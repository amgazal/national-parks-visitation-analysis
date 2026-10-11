# Findings

## Study population and measure

This study covers NPS units that reported monthly visitor-use statistics in the 2025 package, 1979–2025. It is a National Park System study, not a study of only units whose official designation is **National Park**. The primary measure is NPS `TRV`, Recreation Visits. A visit count is not a count of unique people, and these data do not directly measure on-site crowding, queues, density, or capacity pressure.

The personal motivation was noticing different levels of foot traffic while visiting parks near my aunt's home in the Bronx. Many Bronx parks are New York City municipal parks, not NPS units. The national NPS results below therefore provide context about a different population and should not be presented as evidence about those specific Bronx parks.

## Results

- Total reported recreation visits were **327,516,619 in 2019**, fell to **237,064,332 in 2020**, and reached **323,014,305 in 2025**. The 2020 change is consistent with a major disruption, but this descriptive series cannot identify its causes.
- In 2025, the highest-volume reporting units were **Blue Ridge Parkway (16,533,753)**, **Golden Gate National Recreation Area (15,748,676)**, and **Great Smoky Mountains National Park (11,527,939)**. The lowest values include units with zero or very small reported counts; a low count may reflect limited use, reporting practices, or a unit-specific counting method.
- July, August, and June have the largest aggregate recreation-visit totals across 1979–2025. This is a volume pattern, not a crowding or per-park seasonal density estimate.
- The NPS API metadata allows comparisons by designation and geographic coordinates. A simple interpretable model using latitude, longitude, designation, and year, evaluated with parks held out by group, achieved a held-out `R²` of about **0.066** on log visits. These variables alone explain little out-of-sample variation. This is evidence against a strong claim that geography and designation, as represented here, are sufficient explanations.

## What can be learned

Park managers could use the descriptive rankings and seasonal totals as screening information for asking more specific questions about staffing, visitor communication, transportation, and monitoring. Those decisions should be checked against park-level operations data, entrance counts, trail counters, reservation data, and visitor experience measures.

The results support hypotheses, not causal recommendations. High visitation may reflect attraction, access, nearby population, route traffic, reporting practices, or several factors together. The model does not establish that latitude, designation, or year causes visits.

## Unresolved questions and limitations

- Acreage is not included in `Main_Data.csv`, the XML metadata, or the saved NPS API response used here. A visits-per-acre number would also be a weak crowding proxy because parks differ in geography, boundaries, usable area, and counting methods. The acreage question is therefore unresolved rather than filled with an unverified lookup.
- Population proximity and accessibility require a separately designed, time-matched source such as Census population surfaces, road-network travel times, or gateway-community data. They are not inferred from state or coordinates.
- Reporting coverage changes over time, and NPS documents differences in procedures, data quality, and counting methods. Comparisons across years and units should be interpreted cautiously.
- Very low and zero values are retained as reported; the analysis does not assume they mean zero unique visitors.
- Four negative `TRV` records in the downloaded source were excluded because negative visits cannot be valid visit counts. They are an audit item, not imputed observations.
- The regression uses repeated annual observations but holds out entire units so the same park does not appear in both train and test sets. It is a modest descriptive benchmark, not a forecasting system.

## Reproduce

From the repository root:

```bash
python -m pip install -r requirements.txt
python scripts/download_data.py
python scripts/clean_data.py
pytest -q
```

Then run notebooks 1 and 2 from the repository root. They read the generated relative paths and call the same functions used by the scripts.
