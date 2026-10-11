"""Create clean annual and monthly analysis tables and figures."""

from pathlib import Path
import sys

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
    monthly_visits,
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
    monthly = monthly_visits(visits)
    annual.to_csv(processed / "annual_recreation_visits.csv", index=False)
    monthly.to_csv(processed / "monthly_recreation_visits.csv", index=False)
    duckdb_annual_summary(annual).to_csv(processed / "annual_summary.csv", index=False)

    yearly = annual.groupby("Year", as_index=False)["RecreationVisits"].sum()
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(yearly["Year"], yearly["RecreationVisits"], marker="o", color="#176b87")
    ax.axvline(2020, color="#c44e52", linestyle="--", label="2020 pandemic year")
    ax.set(title="NPS recreation visits over time", xlabel="Reporting year", ylabel="Recreation visits")
    ax.ticklabel_format(axis="y", style="plain")
    ax.text(2020.4, yearly["RecreationVisits"].max() * 0.95, "2020 pandemic year", color="#c44e52")
    fig.subplots_adjust(left=0.1, right=0.98, bottom=0.12, top=0.9)
    fig.savefig(figures / "annual_visitation_trend.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(monthly["Month"], monthly["RecreationVisits"], color="#2a9d8f")
    ax.set(title="Seasonal distribution of recreation visits, 1979–2025", xlabel="Month", ylabel="Recreation visits")
    ax.ticklabel_format(axis="y", style="plain")
    fig.subplots_adjust(left=0.1, right=0.98, bottom=0.12, top=0.9)
    fig.savefig(figures / "seasonal_visitation.png", dpi=180)
    plt.close(fig)

    latest_top, latest_bottom = top_bottom(annual, int(annual["Year"].max()))
    latest_top.to_csv(processed / "latest_top_10.csv", index=False)
    latest_bottom.to_csv(processed / "latest_bottom_10.csv", index=False)

    fig, ax = plt.subplots(figsize=(12, 7))
    plot_data = latest_top.sort_values("RecreationVisits")
    ax.barh(plot_data["ParkName"], plot_data["RecreationVisits"], color="#176b87")
    ax.set(title=f"Top 10 reporting units by recreation visits, {annual['Year'].max()}", xlabel="Recreation visits", ylabel="")
    ax.ticklabel_format(axis="x", style="plain")
    fig.subplots_adjust(left=0.35, right=0.98, bottom=0.12, top=0.9)
    fig.savefig(figures / "top_10_latest_year.png", dpi=180)
    plt.close(fig)

    print(f"Cleaned {len(visits):,} monthly recreation records for {visits.UnitCode.nunique()} units")
    print(f"Annual totals: {yearly.iloc[0].RecreationVisits:,.0f} in {yearly.iloc[0].Year} to {yearly.iloc[-1].RecreationVisits:,.0f} in {yearly.iloc[-1].Year}")
    print("Acreage and population proximity are not fields in the official package or API snapshot; they remain unresolved.")


if __name__ == "__main__":
    main()
