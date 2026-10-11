from __future__ import annotations

from pathlib import Path
import json
import warnings

import duckdb
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.dummy import DummyRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import RepeatedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


STATISTIC_DEFINITIONS = {
    "TRV": "Recreation Visits",
    "TV": "Total Visits (Recreation plus Non-Recreation)",
    "TRVH": "Recreation Visitor Hours",
    "TH": "Total Hours",
    "TNRV": "Non-Recreation Visits",
}


def load_recreation_visits(path: str | Path) -> pd.DataFrame:
    """Load and validate the NPS main file for recreation visits only."""
    frame = pd.read_csv(path, usecols=["UnitCode", "Year", "Month", "Statistic", "Value"])
    required = {"UnitCode", "Year", "Month", "Statistic", "Value"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing required columns: {required - set(frame.columns)}")
    frame = frame.loc[frame["Statistic"].eq("TRV")].copy()
    frame["UnitCode"] = frame.UnitCode.astype("string").str.strip().str.upper()
    for column in ["Year", "Month", "Value"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    invalid = frame[["Year", "Month", "Value"]].isna().any(axis=1)
    invalid |= ~np.isfinite(frame[["Year", "Month", "Value"]]).all(axis=1)
    invalid |= frame.UnitCode.isna() | frame.UnitCode.eq("")
    invalid |= frame.Year.mod(1).ne(0) | frame.Month.mod(1).ne(0)
    invalid |= ~frame.Month.between(1, 12) | ~frame.Year.between(1979, 2025)
    invalid |= frame.Value.mod(1).ne(0)
    if invalid.any():
        raise ValueError(f"Invalid recreation records: {frame.loc[invalid].to_dict('records')[:10]}")
    if frame.duplicated(["UnitCode", "Year", "Month", "Statistic"]).any():
        raise ValueError("Duplicate unit-year-month-statistic records found")
    rejected = frame.loc[frame.Value.lt(0)].copy()
    if not rejected.empty:
        warnings.warn(f"Quarantining {len(rejected)} negative TRV records; affected annual totals are partial", stacklevel=2)
    frame = frame.loc[frame.Value.ge(0)].copy()
    frame[["Year", "Month", "Value"]] = frame[["Year", "Month", "Value"]].astype("int64")
    frame.attrs["rejected_records"] = rejected.to_dict("records")
    if frame.empty:
        raise ValueError("No valid TRV records")
    return frame


def load_park_metadata(path: str | Path) -> pd.DataFrame:
    """Load the NPS API snapshot and retain documented descriptive fields."""
    payload = json.loads(Path(path).read_text())
    if int(payload["total"]) != len(payload["data"]) or int(payload.get("start", 0)) != 0:
        raise ValueError("Incomplete NPS API snapshot; pagination required")
    frame = pd.json_normalize(payload["data"])
    columns = {
        "parkCode": "UnitCode",
        "fullName": "FullName",
        "name": "ParkName",
        "designation": "Designation",
        "states": "States",
        "latitude": "Latitude",
        "longitude": "Longitude",
    }
    frame = frame[list(columns)].rename(columns=columns)
    frame.loc[:, "UnitCode"] = frame["UnitCode"].str.upper()
    for column in ["Latitude", "Longitude"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame.UnitCode.isna().any() or frame.UnitCode.duplicated().any():
        raise ValueError("Missing or duplicate metadata unit codes")
    frame["Designation"] = frame.Designation.where(frame.Designation.ne(""), np.nan)
    for column, bound in [("Latitude", 90), ("Longitude", 180)]:
        frame.loc[~frame[column].between(-bound, bound), column] = np.nan
    return frame


def annual_visits(visits: pd.DataFrame) -> pd.DataFrame:
    result = visits.groupby(["UnitCode", "Year"], as_index=False).agg(
        RecreationVisits=("Value", "sum"), MonthsReported=("Month", "nunique"))
    result["CompleteYear"] = result.MonthsReported.eq(12)
    return result


def monthly_visits(visits: pd.DataFrame) -> pd.DataFrame:
    return visits.groupby("Month", as_index=False)["Value"].sum().rename(columns={"Value": "RecreationVisits"})


def add_metadata(annual: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    result = annual.merge(metadata, on="UnitCode", how="left", validate="many_to_one")
    result["ParkName"] = result.ParkName.fillna(result.UnitCode)
    return result


def top_bottom(annual: pd.DataFrame, year: int, n: int = 10) -> tuple[pd.DataFrame, pd.DataFrame]:
    if n < 1 or year not in annual.Year.values:
        raise ValueError("Require a represented year and positive n")
    subset = annual.loc[annual["Year"].eq(year)].copy()
    if "CompleteYear" in subset:
        subset = subset.loc[subset.CompleteYear]
    subset = subset.sort_values(["RecreationVisits", "UnitCode"], ascending=[False, True])
    return subset.head(n), subset.tail(n).sort_values("RecreationVisits")


def duckdb_annual_summary(annual: pd.DataFrame) -> pd.DataFrame:
    """Demonstrate a SQL aggregation over the cleaned annual table."""
    query = """
        SELECT Year, SUM(RecreationVisits) AS RecreationVisits,
               COUNT(DISTINCT UnitCode) AS ReportingUnits
        FROM annual
        GROUP BY Year
        ORDER BY Year
    """
    return duckdb.sql(query).df()


def recent_cohort(annual: pd.DataFrame, start: int = 2023, end: int = 2025) -> pd.DataFrame:
    """One row per unit with complete reporting in every requested year; retain zeros."""
    if start > end:
        raise ValueError("Start must precede end")
    subset = annual.loc[annual.Year.between(start, end) & annual.CompleteYear]
    units = subset.groupby("UnitCode").Year.nunique()
    subset = subset.loc[subset.UnitCode.isin(units[units.eq(end - start + 1)].index)]
    result = subset.groupby("UnitCode", as_index=False).agg(RecreationVisits=("RecreationVisits", "mean"))
    fields = [c for c in ["UnitCode", "ParkName", "FullName", "Designation", "States", "Latitude", "Longitude"] if c in annual]
    return result.merge(annual[fields].drop_duplicates("UnitCode"), on="UnitCode", validate="one_to_one")


def comparable_seasonality(visits: pd.DataFrame, start: int = 2023, end: int = 2025) -> pd.DataFrame:
    annual = annual_visits(visits)
    cohort = recent_cohort(annual, start, end)
    # Every year must have positive volume to define a within-year share.
    positive = annual.loc[annual.Year.between(start, end)].groupby("UnitCode").RecreationVisits.min()
    codes = cohort.loc[cohort.UnitCode.isin(positive[positive.gt(0)].index), "UnitCode"]
    subset = visits.loc[visits.UnitCode.isin(codes) & visits.Year.between(start, end)].copy()
    if subset.empty:
        raise ValueError("No complete positive-volume units for seasonality")
    subset["Share"] = subset.Value / subset.groupby(["UnitCode", "Year"]).Value.transform("sum")
    result = subset.groupby("Month", as_index=False).agg(MeanUnitShare=("Share", "mean"), Volume=("Value", "sum"))
    result["VolumeShare"] = result.Volume / result.Volume.sum()
    result["Units"] = len(codes)
    return result


def grouped_regression(annual_with_metadata: pd.DataFrame) -> pd.DataFrame:
    """Repeated five-fold unit-held-out evaluation on 2023–2025 unit means.

    One row per unit makes KFold a unit-grouped split. Identical folds compare
    predictors with a training-mean baseline. Ridge stabilizes sparse categories.
    Scores concern log1p annual visits, never original-scale explained variance.
    """
    cohort = recent_cohort(annual_with_metadata)
    data = cohort.dropna(subset=["Latitude", "Longitude", "Designation"]).reset_index(drop=True)
    if len(data) < 10:
        raise ValueError("Too few reporting units for grouped evaluation")
    scores = []
    for sensitivity in ["include_zero", "positive_only"]:
        sample = data if sensitivity == "include_zero" else data.loc[data.RecreationVisits.gt(0)].reset_index(drop=True)
        target = np.log1p(sample.RecreationVisits)
        splitter = RepeatedKFold(n_splits=5, n_repeats=5, random_state=42)
        for split, (train, test) in enumerate(splitter.split(sample)):
            for name, numeric, categorical in [
                ("baseline", [], []), ("geography", ["Latitude", "Longitude"], []),
                ("designation", [], ["Designation"]),
                ("combined", ["Latitude", "Longitude"], ["Designation"])]:
                transformers = []
                if numeric:
                    transformers.append(("numeric", StandardScaler(), numeric))
                if categorical:
                    transformers.append(("designation", OneHotEncoder(handle_unknown="ignore"), categorical))
                model = (make_pipeline(ColumnTransformer(transformers), Ridge(alpha=1.0, solver="lsqr"))
                         if transformers else DummyRegressor())
                model.fit(sample.iloc[train], target.iloc[train])
                predicted = model.predict(sample.iloc[test])
                scores.append(dict(sensitivity=sensitivity, model=name, split=split,
                    train_units=len(train), test_units=len(test),
                    r2_log_visits=r2_score(target.iloc[test], predicted),
                    mae_log_visits=mean_absolute_error(target.iloc[test], predicted)))
    return pd.DataFrame(scores)
