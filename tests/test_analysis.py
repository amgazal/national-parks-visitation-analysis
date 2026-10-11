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
