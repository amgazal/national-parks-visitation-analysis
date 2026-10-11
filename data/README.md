# Data

Raw files are intentionally not committed because the NPS CSV package is large. Download them with:

```bash
python scripts/download_data.py
```

## Source registry

| Source | URL | Retrieved in this build | Used for | Limitations |
|---|---|---:|---|---|
| NPS Visitor Use Statistics 2025 package | https://catalog.data.gov/dataset/nps-visitor-use-statistics-data-package-2025 | 2026-10-10 | `Main_Data.csv`, state file, XML metadata | NPS estimates of reported visitor use; not unique people or direct crowding measurements. |
| NPS Visitor Use Statistics documentation | https://www.nps.gov/subjects/socialscience/visitor-use-statistics-dashboard.htm | 2026-10-10 | Definitions, reporting history, limitations | Reporting and counting procedures vary by unit and over time. |
| NPS API park endpoint | https://developer.nps.gov/api/v1/parks?limit=500&api_key=DEMO_KEY | 2026-10-10 | Park names, designations, states, coordinates | Current API metadata snapshot; no acreage or population-proximity field. |

The NPS XML metadata identifies `TRV` as **Recreation Visits**. This analysis uses that measure, not unique visitors. The NPS API metadata join is case-normalized on `UnitCode`/`parkCode`.

## Files

- `raw/Main_Data.csv`: official monthly statistics, 1979–2025.
- `raw/Main_State_Data.csv`: official state-associated version retained for reference.
- `raw/NPS_VUStats_Data_2025_metadata.xml`: official definitions and metadata.
- `raw/nps_parks_api.json`: saved NPS API response used for the metadata join.
- `processed/`: generated annual and monthly tables; do not treat them as independent source data.

Acreage and population proximity are unresolved in this repository because neither is present in the official visitation package or the saved NPS API response. No proxy is substituted.
