# Portfolio and resume copy

**Title:** Beyond the Crowds: Exploring What Drives National Park Visitation

**Description (45 words):** Inspired by noticing differences in park activity during visits around the Bronx, I analyzed official National Park Service data to explore visitation patterns nationwide. I built a reproducible Python workflow, compared seasonality and park designations, and tested associations while distinguishing visit counts from actual crowding.

**Stack:** Python, Pandas, NumPy, DuckDB SQL, Matplotlib, Seaborn, scikit-learn, Jupyter, pytest.

**Resume bullet options:**

- Analyzed 193,692 monthly NPS recreation-visit records across 47 years using Python and DuckDB, documenting invalid counts, incomplete years, and metadata gaps.
- Compared seasonal visitation across 392 consistently reporting NPS units and park-designation differences using reproducible notebooks and visualizations.
- Evaluated visitation associations across 367 units using 25 held-out cross-validation folds, comparing geography and designation with a baseline on log-transformed visits.

**Interview notes:**

- The question came from personal observations, but Bronx municipal parks are a different population from the nationwide NPS data.
- Visits fell 27.6% in 2020; 2025 reached 323.0 million. The top ten reporting codes accounted for 29.1% of 2025 volume.
- July averaged 14.1% of annual visits in the comparable seasonal cohort. Equal-unit weighting prevents the busiest parks from dominating this result.
- Current designation was more informative than coordinates alone. Combined mean R² was 0.303 on log1p three-year mean visits, not original visit counts or causal explanatory power.
- I preserved questionable records in an audit, flagged incomplete years, kept zeros, and documented missing joins. Population, accessibility, acreage, historical designation changes, and counting procedures remain unresolved.

This is a data analysis and evidence-based problem-solving project. It does not predict crowding or establish why designation causes visitation. Portfolio and resume repositories were not edited.
