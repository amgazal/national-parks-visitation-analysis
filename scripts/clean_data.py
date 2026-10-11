"""Create clean annual and monthly analysis tables and figures."""

from pathlib import Path
import sys
import json
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.analysis import (  # noqa: E402
    add_metadata,
    annual_visits,
    duckdb_annual_summary,
    load_park_metadata,
    load_recreation_visits,
    comparable_seasonality,
    recent_cohort,
    grouped_regression,
    top_bottom,
)


def main() -> None:
    raw = ROOT / "data" / "raw"
    processed = ROOT / "data" / "processed"
    figures = ROOT / "figures"
    processed.mkdir(exist_ok=True)
    figures.mkdir(exist_ok=True)
    sns.set_theme(style="whitegrid", context="talk")

    visits = load_recreation_visits(raw / "Main_Data.csv")
    metadata = load_park_metadata(raw / "nps_parks_api.json")
    annual = add_metadata(annual_visits(visits), metadata)
    monthly = comparable_seasonality(visits)
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    pd.DataFrame(visits.attrs["rejected_records"]).to_csv(reports / "rejected_records.csv", index=False)
    annual.loc[~annual.CompleteYear].to_csv(reports / "incomplete_years.csv", index=False)
    annual.loc[annual.FullName.isna()].groupby("UnitCode").agg(
        FirstYear=("Year", "min"), LastYear=("Year", "max"),
        ReportedVisits=("RecreationVisits", "sum")).to_csv(reports / "unmatched_metadata.csv")
    duckdb_annual_summary(annual).to_csv(reports / "annual_summary.csv", index=False)
    cohort = recent_cohort(annual)
    excluded = cohort.loc[cohort[["Latitude", "Longitude", "Designation"]].isna().any(axis=1)].copy()
    excluded.to_csv(reports / "model_exclusions.csv", index=False)
    source_trv = pd.read_csv(raw / "Main_Data.csv")
    source_trv = source_trv.loc[source_trv.Statistic.eq("TRV")]
    source_totals = source_trv.groupby("Year").Value.sum().rename("SourceSignedTotal")
    comparison_totals = annual.groupby("Year").RecreationVisits.sum().to_frame().join(source_totals)
    comparison_totals["Difference"] = comparison_totals.RecreationVisits - comparison_totals.SourceSignedTotal
    comparison_totals.to_csv(reports / "negative_value_sensitivity.csv")
    cohort.to_csv(processed / "recent_cohort.csv", index=False)
    designation = cohort.groupby("Designation").RecreationVisits.agg(
        Units="size", Median="median", Q1=lambda x: x.quantile(.25), Q3=lambda x: x.quantile(.75))
    designation.to_csv(reports / "designation_comparison.csv")
    metrics = grouped_regression(annual)
    metrics.to_csv(reports / "model_splits.csv", index=False)
    metrics.groupby(["sensitivity", "model"])[["r2_log_visits", "mae_log_visits"]].agg(
        ["mean", "std", "min", "max"]).to_csv(reports / "model_summary.csv")
    monthly.to_csv(reports / "seasonality.csv", index=False)
    audit = dict(valid_monthly_records=len(visits), historical_codes=visits.UnitCode.nunique(),
        incomplete_unit_years=int((~annual.CompleteYear).sum()), recent_cohort_units=len(cohort),
        unmatched_recent_codes=cohort.loc[cohort.FullName.isna(), "UnitCode"].tolist(),
        model_units=len(cohort.dropna(subset=["Latitude", "Longitude", "Designation"])),
        recent_zero_units=int(cohort.RecreationVisits.eq(0).sum()),
        latest_complete=bool(annual.loc[annual.Year.eq(annual.Year.max()), "CompleteYear"].all()))
    (reports / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    fig, ax = plt.subplots(figsize=(11, 7))
    comparison = designation.loc[designation.Units.ge(5)].sort_values("Median")
    ax.errorbar(comparison.Median, range(len(comparison)),
                xerr=[comparison.Median-comparison.Q1, comparison.Q3-comparison.Median],
                fmt="o", color="#176b87", capsize=4)
    ax.set_yticks(range(len(comparison)), [f"{name} (n={int(row.Units)})" for name, row in comparison.iterrows()])
    ax.set(xscale="log", xlabel="Mean annual recreation visits per unit (log scale)",
           title="Designation comparison, 2023–2025\nMedian and middle 50% of unit means; groups with ≥5 units")
    fig.tight_layout()
    fig.savefig(figures / "designation_comparison.png", dpi=180)
    plt.close(fig)
    annual.to_csv(processed / "annual_recreation_visits.csv", index=False)
    monthly.to_csv(processed / "monthly_recreation_visits.csv", index=False)
    duckdb_annual_summary(annual).to_csv(processed / "annual_summary.csv", index=False)

    yearly = annual.groupby("Year", as_index=False)["RecreationVisits"].sum()
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(yearly["Year"], yearly["RecreationVisits"] / 1e6, marker="o", color="#176b87")
    ax.axvline(2020, color="#c44e52", linestyle="--", label="2020 pandemic year")
    ax.set(title="Reported NPS recreation visits, 1979–2025 (changing coverage)", xlabel="Reporting year", ylabel="Recreation visits (millions)")
    ax.ticklabel_format(axis="y", style="plain")
    ax.legend(loc="upper left", fontsize=11)
    fig.tight_layout()
    fig.savefig(figures / "annual_visitation_trend.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(monthly.Month, monthly.MeanUnitShare * 100, marker="o", label="Equal weight per unit and year")
    ax.plot(monthly.Month, monthly.VolumeShare * 100, marker="s", label="Weighted by visit volume")
    ax.set(title=f"Seasonality, 2023–2025: {int(monthly.Units.iloc[0])} comparable units",
           xlabel="Month", ylabel="Share of annual recreation visits (%)", xticks=range(1, 13))
    ax.legend(fontsize=11)
    fig.tight_layout()
    fig.savefig(figures / "seasonal_visitation.png", dpi=180)
    plt.close(fig)

    latest_top, latest_bottom = top_bottom(annual, int(annual["Year"].max()))
    latest_top.to_csv(reports / "latest_top_10.csv", index=False)
    latest_bottom.to_csv(reports / "latest_bottom_10.csv", index=False)
    latest_top.to_csv(processed / "latest_top_10.csv", index=False)
    latest_bottom.to_csv(processed / "latest_bottom_10.csv", index=False)

    fig, ax = plt.subplots(figsize=(12, 7))
    plot_data = latest_top.sort_values("RecreationVisits")
    ax.barh(plot_data["ParkName"], plot_data["RecreationVisits"] / 1e6, color="#176b87")
    ax.set(title=f"Top 10 reporting units by recreation visits, {annual['Year'].max()}", xlabel="Recreation visits (millions)", ylabel="")
    ax.ticklabel_format(axis="x", style="plain")
    fig.tight_layout()
    fig.savefig(figures / "top_10_latest_year.png", dpi=180)
    plt.close(fig)

    print(f"Cleaned {len(visits):,} monthly recreation records for {visits.UnitCode.nunique()} units")
    print(f"Annual totals: {yearly.iloc[0].RecreationVisits:,.0f} in {yearly.iloc[0].Year} to {yearly.iloc[-1].RecreationVisits:,.0f} in {yearly.iloc[-1].Year}")
    print("Acreage and population proximity are not fields in the official package or API snapshot; they remain unresolved.")


if __name__ == "__main__":
    main()
