# Findings and review decisions

The question is why some NPS reporting units attract more recreation visits. The strongest result here is a descriptive difference between park designations, with seasonality providing context. Neither comparison identifies a causal mechanism. The Bronx park visits motivated the question; the national data are not evidence about those municipal parks.

## Measure and scope

The [2025 NPS package](https://catalog.data.gov/dataset/nps-visitor-use-statistics-data-package-2025), released March 26, 2026, covers 1979–2025. Its XML defines TRV as Recreation Visits. Under the [NPS definition](https://www.nps.gov/subjects/socialscience/nps-visitor-use-statistics-definitions.htm), repeat visits on different days can count again; totals are not unique people. Commuting is classified separately as non-recreation use. Annual volume does not measure simultaneous crowding.

The source contains 193,696 TRV rows across 406 historical reporting codes; 193,692 remain after quarantine. Coverage grows from 271 codes in 1979 to 400 in 2025. All 400 have twelve records in 2025, and the calculated 323,014,305 agrees with the [official 2025 release](https://www.nps.gov/orgs/1207/03-13-26-2025-visitation-statsitics.htm). That release counts 406 administrative parks; this repository counts distinct CSV reporting codes. No complete administrative-to-reporting crosswalk was established, so these counts must not be equated.

## Quality decisions

Missing identifiers, nonnumeric/nonfinite values, fractional counts or dates, invalid months, out-of-package years, and duplicate normalized keys fail validation rather than disappearing. Four negative records are preserved in [rejected_records.csv](rejected_records.csv): SAJH November 2002 −20,331; LIBO January 2003 −425; RUCA November 2004 −39; MORR December 2011 −320. Their meaning is unresolved, so they are not treated as valid counts or replaced with zero.

Eleven source unit-years lack twelve months; quarantine adds four more partial years. [incomplete_years.csv](incomplete_years.csv) lists all 15. Annual trend totals sum available valid observations and are labeled reported totals; rankings and recent comparisons require complete years. [negative_value_sensitivity.csv](negative_value_sensitivity.csv) preserves source signed totals and the exact upward differences caused by quarantine: 20,331 in 2002, 425 in 2003, 39 in 2004, and 320 in 2011. Recent findings are unaffected. Completeness means twelve reported months, not proof that estimates are accurate.

Zeros are retained. CAWO in 2023 and EDAL in 2025 have zero annual totals; neither has a zero three-year mean. These two units are excluded only from the seasonality cohort because a within-year proportion would be undefined. Low reported use can also reflect closures or counting practices; no closure explanation was independently established here.

## Annual results and concentration

| Year | Reported recreation visits | Reporting codes |
|---|---:|---:|
| 2019 | 327,516,619 | 379 |
| 2020 | 237,064,332 | 383 |
| 2024 | 331,863,358 | 398 |
| 2025 | 323,014,305 | 400 |

The 2020 decrease is 27.6%; 2025 is 2.7% below 2024. These are changing-coverage totals. The pandemic-era break is descriptive, not an estimated causal effect. Exact annual results are in [annual_summary.csv](annual_summary.csv).

Blue Ridge Parkway (16,533,753), Golden Gate National Recreation Area (15,748,676), and Great Smoky Mountains National Park (11,527,939) lead 2025. The top ten account for 29.1% of visits. [Top ten](latest_top_10.csv) and [bottom ten](latest_bottom_10.csv) include codes and metadata. EDAL reports zero and CAWO reports 20. These are volume rankings, not a ranking of visitor experience or demand under equal access.

## Comparable seasonality

Use the 394 codes with complete records in every year from 2023 through 2025, removing the two with any zero-total year for this calculation. Divide each monthly count by its unit-year total, then average across 392 units and three years. July is 14.1%, June 12.4%, and August 11.9%. On the same cohort, volume-weighted July is 12.9%. Equal weighting describes the average unit's seasonal profile; volume weighting describes when the cohort's visits occur. Neither describes daily crowding. This recent period avoids the acute 2020 disruption but does not guarantee identical operations across units. See [seasonality.csv](seasonality.csv).

## Designation and geography

Average each complete unit's 2023–2025 annual totals before comparing categories. The API snapshot supplies present-day categories, kept exactly as reported. Median unit means are 1,163,888 for National Recreation Areas (n=16), 792,493 for National Parks (n=51), and 27,335 for National Historic Sites (n=70). These categories differ in purpose and setting, and their distributions overlap. The chart shows medians and interquartile ranges, not confidence intervals; groups below five units remain in the table but are omitted from the chart. Large outliers are retained, while medians and a logarithmic axis make the skew visible. See [designation_comparison.csv](designation_comparison.csv).

The API has 474 entries, a broader and differently organized set than reporting codes. Fifteen historical codes do not match; twelve occur in the recent cohort. For example, the visitation file separates SEQU and KICA, while the API uses SEKI. They are not assigned duplicate combined metadata. All unmatched codes remain in national totals and appear in [unmatched_metadata.csv](unmatched_metadata.csv). The model excludes 27 of 394 units: twelve unmatched and fifteen additional units without a usable designation. See [model_exclusions.csv](model_exclusions.csv). Selection can bias category and model results.

Names and designations change: [NPS documents](https://www.nps.gov/aboutus/recent-changes.htm) New River Gorge's December 2020 redesignation and Weir Farm's January 2021 change. A current API snapshot cannot reconstruct historical classifications. The recent cross-section reduces, but does not eliminate, temporal mismatch. Category counts here are not an official census of all National Parks, and coordinates represent points rather than boundaries, gateway access, or nearby population.

## Secondary prediction benchmark

One row per unit (three-year mean) prevents repeated annual observations from giving long-reporting units more weight. Use five-fold cross-validation repeated five times, seed 42; each fold holds out whole units. Identical splits compare a training-mean dummy, standardized coordinates, one-hot designation, and both. Preprocessing is fitted only on training data. Fixed Ridge alpha=1 stabilizes rare categories without tuning against held-out results; unseen categories use all-zero indicators.

| Predictor | Mean R², log1p visits | SD across folds | Mean MAE, log1p visits |
|---|---:|---:|---:|
| Training-mean baseline | −0.016 | 0.023 | 1.628 |
| Coordinates | −0.005 | 0.054 | 1.611 |
| Designation | 0.273 | 0.106 | 1.295 |
| Both | 0.303 | 0.103 | 1.282 |

The combined R² ranges from 0.091 to 0.436. These scores apply to **log1p mean annual visits**, not original count-scale variance or forecasts. Negative R² means worse than predicting the test-set mean; the dummy predicts the training mean and therefore need not score zero. Fold SD is split variation, not a confidence interval because folds overlap. A positive-only sensitivity produces identical scores since none of the 367 modeled three-year means is zero. Annual zeros still matter for the seasonality exclusions above. Full results: [model_splits.csv](model_splits.csv), [model_summary.csv](model_summary.csv).

The old single-split R² of approximately 0.066 is superseded. The target period, weighting, estimator, and evaluation changed, so the new score is not a like-for-like model improvement claim. Designation provides predictive information here; linear coordinates alone add little. This does not rule out more complex geographic relationships. The model remains a secondary check, with designation medians the more direct answer to the research question.

## Limits and next steps

No verified compatible acreage, population, or transport join was established. These fields are absent from the selected visitation/API inputs, not necessarily unavailable elsewhere. Adding them would require resolving reporting-code boundaries, reference dates, and appropriate access measures. Visits per acre would not directly measure crowding. No invented proxy or significance claim is used.

NPS notes that counting-method changes, estimation, and permanent source errors can affect trends in its [data limitations](https://www.nps.gov/subjects/socialscience/visitor-use-statistics-dashboard.htm). A full unit-by-unit endnote audit remains outside this analysis. Seasonal patterns could guide questions about when to investigate staffing or transit, but decisions need local entrance counts, trail counters, access constraints, and visitor-experience evidence.

Follow the root README to regenerate every table, chart, and notebook. Raw bytes and retrieval timestamps are recorded in the source manifest; API changes can alter future metadata comparisons.
