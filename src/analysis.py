from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
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
    frame.loc[:, "Year"] = pd.to_numeric(frame["Year"], errors="coerce")
    frame.loc[:, "Month"] = pd.to_numeric(frame["Month"], errors="coerce")
    frame.loc[:, "Value"] = pd.to_numeric(frame["Value"], errors="coerce")
    frame = frame.dropna(subset=["UnitCode", "Year", "Month", "Value"])
    frame.loc[:, "Year"] = frame["Year"].astype(int)
    frame.loc[:, "Month"] = frame["Month"].astype(int)
    # Negative values cannot represent visit counts; retain only valid observations.
    frame = frame.loc[frame["Value"].ge(0)].copy()
    if frame.duplicated(["UnitCode", "Year", "Month", "Statistic"]).any():
        raise ValueError("Duplicate unit-year-month-statistic records found")
    return frame


def load_park_metadata(path: str | Path) -> pd.DataFrame:
    """Load the NPS API snapshot and retain documented descriptive fields."""
    payload = pd.read_json(path)
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
        frame.loc[:, column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.drop_duplicates("UnitCode")


def annual_visits(visits: pd.DataFrame) -> pd.DataFrame:
    return visits.groupby(["UnitCode", "Year"], as_index=False)["Value"].sum().rename(columns={"Value": "RecreationVisits"})


def monthly_visits(visits: pd.DataFrame) -> pd.DataFrame:
    return visits.groupby("Month", as_index=False)["Value"].sum().rename(columns={"Value": "RecreationVisits"})


def add_metadata(annual: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    return annual.merge(metadata, on="UnitCode", how="left", validate="many_to_one")


def top_bottom(annual: pd.DataFrame, year: int, n: int = 10) -> tuple[pd.DataFrame, pd.DataFrame]:
    subset = annual.loc[annual["Year"].eq(year)].sort_values("RecreationVisits", ascending=False)
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


def grouped_regression(annual_with_metadata: pd.DataFrame) -> dict[str, float | int]:
    """Evaluate a descriptive model with park-grouped train/test separation."""
    model_data = annual_with_metadata.dropna(subset=["RecreationVisits", "Latitude", "Longitude", "Designation"]).copy()
    model_data = model_data.loc[model_data["RecreationVisits"] > 0]
    if model_data["UnitCode"].nunique() < 10:
        raise ValueError("Too few reporting units for grouped evaluation")
    features = ["Latitude", "Longitude", "Designation", "Year"]
    target = np.log1p(model_data["RecreationVisits"])
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train, test = next(splitter.split(model_data, target, groups=model_data["UnitCode"]))
    transformer = ColumnTransformer([
        ("numeric", StandardScaler(), ["Latitude", "Longitude", "Year"]),
        ("designation", OneHotEncoder(handle_unknown="ignore"), ["Designation"]),
    ])
    estimator = make_pipeline(transformer, LinearRegression())
    estimator.fit(model_data.iloc[train][features], target.iloc[train])
    predicted = estimator.predict(model_data.iloc[test][features])
    return {
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "test_units": int(model_data.iloc[test]["UnitCode"].nunique()),
        "r2_log_visits": float(r2_score(target.iloc[test], predicted)),
        "mae_log_visits": float(mean_absolute_error(target.iloc[test], predicted)),
    }
