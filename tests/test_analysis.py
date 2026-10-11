from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[1]))
from src.analysis import annual_visits, load_recreation_visits, top_bottom  # noqa: E402


def test_load_recreation_visits_filters_to_trv(tmp_path):
    source = tmp_path / "main.csv"
    pd.DataFrame([
        ["ABLI", 2020, 1, "TRV", 10],
        ["ABLI", 2020, 1, "TV", 12],
    ], columns=["UnitCode", "Year", "Month", "Statistic", "Value"]).to_csv(source, index=False)
    result = load_recreation_visits(source)
    assert result["Statistic"].unique().tolist() == ["TRV"]
    assert result.iloc[0]["Value"] == 10


def test_annual_visits_sums_months():
    visits = pd.DataFrame({"UnitCode": ["A", "A"], "Year": [2020, 2020], "Month": [1, 2], "Statistic": ["TRV", "TRV"], "Value": [2, 3]})
    assert annual_visits(visits).iloc[0]["RecreationVisits"] == 5


def test_top_bottom_requires_year():
    annual = pd.DataFrame({"UnitCode": ["A", "B"], "Year": [2025, 2025], "RecreationVisits": [10, 1]})
    top, bottom = top_bottom(annual, 2025, n=1)
    assert top.iloc[0].UnitCode == "A"
    assert bottom.iloc[0].UnitCode == "B"

import json
import numpy as np
import pytest
from src.analysis import (add_metadata, comparable_seasonality, duckdb_annual_summary,
                          load_park_metadata, recent_cohort, grouped_regression)


def source_file(tmp_path, rows):
    path = tmp_path / 'source.csv'
    pd.DataFrame(rows, columns=['UnitCode', 'Year', 'Month', 'Statistic', 'Value']).to_csv(path, index=False)
    return path


@pytest.mark.parametrize('column,value', [(1, 2020.5), (2, 0), (2, 13), (2, 1.5),
                                         (4, None), (4, np.inf), (4, 1.2), (0, None)])
def test_invalid_records_raise(tmp_path, column, value):
    row = ['ABLI', 2020, 1, 'TRV', 10]
    row[column] = value
    with pytest.raises(ValueError, match='Invalid'):
        load_recreation_visits(source_file(tmp_path, [row]))


def test_normalized_duplicates_raise(tmp_path):
    with pytest.raises(ValueError, match='Duplicate'):
        load_recreation_visits(source_file(tmp_path, [['abli', 2020, 1, 'TRV', 10], ['ABLI', 2020, 1, 'TRV', 10]]))


def test_negative_quarantine_and_partial_year(tmp_path):
    rows = [['A', 2025, m, 'TRV', -5 if m == 2 else 0] for m in range(1, 13)]
    with pytest.warns(UserWarning, match='Quarantining'):
        visits = load_recreation_visits(source_file(tmp_path, rows))
    assert visits.attrs['rejected_records'][0]['Value'] == -5
    annual = annual_visits(visits)
    assert annual.iloc[0].MonthsReported == 11
    assert not annual.iloc[0].CompleteYear
    assert top_bottom(annual, 2025)[0].empty


def synthetic_visits():
    return pd.DataFrame([dict(UnitCode=u, Year=y, Month=m, Value=(10 if m == 7 else 1)*scale)
                         for u, scale in [('A', 1), ('B', 100), ('Z', 0)]
                         for y in range(2023, 2026) for m in range(1, 13)])


def test_comparable_seasonality_and_zero_policy():
    visits = synthetic_visits()
    monthly = comparable_seasonality(visits)
    assert monthly.Units.unique().tolist() == [2]
    assert monthly.MeanUnitShare.sum() == pytest.approx(1)
    assert monthly.VolumeShare.sum() == pytest.approx(1)
    assert monthly.loc[monthly.Month.eq(7), 'MeanUnitShare'].iloc[0] == pytest.approx(10/21)
    assert len(recent_cohort(annual_visits(visits))) == 3
    partial = visits.loc[~(visits.UnitCode.eq('B') & visits.Year.eq(2024) & visits.Month.eq(1))]
    assert set(recent_cohort(annual_visits(partial)).UnitCode) == {'A', 'Z'}


def test_missing_metadata_does_not_drop_visits():
    annual = annual_visits(synthetic_visits())
    metadata = pd.DataFrame({'UnitCode': ['A'], 'ParkName': ['Alpha'], 'Designation': ['Park']})
    joined = add_metadata(annual, metadata)
    assert len(joined) == len(annual)
    assert joined.loc[joined.UnitCode.eq('B'), 'ParkName'].eq('B').all()
    sql = duckdb_annual_summary(joined)
    expected = annual.groupby('Year').RecreationVisits.sum()
    np.testing.assert_allclose(sql.RecreationVisits, expected)


def test_metadata_numeric_and_pagination(tmp_path):
    path = tmp_path / 'metadata.json'
    payload = dict(total='1', start='0', data=[dict(parkCode='a', fullName='Alpha', name='Alpha',
                   designation='', states='NY', latitude='n/a', longitude='-73')])
    path.write_text(json.dumps(payload))
    result = load_park_metadata(path)
    assert pd.isna(result.iloc[0].Latitude)
    assert pd.isna(result.iloc[0].Designation)
    assert result.Longitude.dtype.kind in 'fi'
    payload['total'] = '2'; path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match='pagination'):
        load_park_metadata(path)


def test_model_repeats_units_and_retains_zero_sensitivity():
    annual = pd.DataFrame([dict(UnitCode=str(u), Year=y, CompleteYear=True, RecreationVisits=u*100,
                               Latitude=30+u, Longitude=-100+u, Designation='Park')
                           for u in range(12) for y in range(2023, 2026)])
    metrics = grouped_regression(annual)
    assert len(metrics) == 200
    assert metrics.loc[metrics.sensitivity.eq('include_zero')].eval('train_units + test_units').eq(12).all()
    assert metrics.loc[metrics.sensitivity.eq('positive_only')].eval('train_units + test_units').eq(11).all()
    assert np.isfinite(metrics[['r2_log_visits', 'mae_log_visits']]).all().all()


def test_metadata_duplicate_codes_fail(tmp_path):
    path = tmp_path / 'metadata.json'
    row = dict(parkCode='a', fullName='Alpha', name='Alpha', designation='Park',
               states='NY', latitude='40', longitude='-73')
    path.write_text(json.dumps(dict(total=2, data=[row, row])))
    with pytest.raises(ValueError, match='duplicate'):
        load_park_metadata(path)


def test_downloader_preserves_snapshot_on_failure(tmp_path, monkeypatch):
    from scripts import download_data
    old = tmp_path / 'Main_Data.csv'
    old.write_text('previous snapshot')
    monkeypatch.setattr(download_data, 'RAW', tmp_path)
    monkeypatch.setattr(download_data, 'SOURCES', {'Main_Data.csv': 'https://example.invalid'})
    def unavailable(*args, **kwargs):
        raise OSError('network unavailable')
    monkeypatch.setattr(download_data, 'urlopen', unavailable)
    with pytest.raises(RuntimeError, match='existing snapshot preserved'):
        download_data.main()
    assert old.read_text() == 'previous snapshot'
    assert not list(tmp_path.glob('*.part'))


def test_missing_required_columns_fail(tmp_path):
    path = tmp_path / 'bad.csv'
    path.write_text('UnitCode,Year\nA,2025\n')
    with pytest.raises(ValueError):
        load_recreation_visits(path)
