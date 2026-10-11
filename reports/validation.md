# Final validation

Review date: October 11, 2026 (America/New_York).

- Downloaded all four official inputs successfully; SHA-256 digests and retrieval times are in `source_manifest.json`.
- Created an isolated Python 3.14 environment and installed `requirements.txt` successfully using binary distributions. Updated scientific package pins for the available Python runtime; `pip check` reported no broken requirements.
- Executed `scripts/clean_data.py`: 193,692 accepted monthly TRV records, 406 historical codes. The expected warning identifies four quarantined negative records.
- Executed both notebooks sequentially in fresh kernels using `scripts/execute_notebooks.py`; all code cells completed without errors.
- Executed `python -m pytest -q`: **20 passed**. Coverage includes malformed dates/counts, duplicate normalized records, negative-record quarantine, incomplete years, zero denominators, metadata omissions/pagination/duplicates, SQL aggregation, repeated unit evaluation, and failed-download preservation.
- Independently checked reported totals, percentage changes, top-three counts, top-ten share, seasonal ordering/proportions, designation medians, and rounded model results against the generated tables.
- Visually inspected all four generated figures; fixed clipped annual-axis labels and overlapping ranking ticks by expressing large totals in millions.
- Cloned the committed repository into a separate temporary directory, copied only the freshly downloaded raw snapshot, and used the isolated pinned environment. Cleaning, all 20 tests, and both fresh-kernel notebooks passed again. Every generated result CSV matched byte-for-byte. Downloads had already been exercised separately; this checks clean-source reproduction against the same input bytes, not a second live API snapshot.
- Checked local documentation links and `git diff --check`. Official catalog, source downloads, NPS definitions, reporting limitations, and designation-change pages were accessible.

The sandbox prevented download DNS access and local Jupyter port binding. The same operations succeeded with authorized network/kernel access. Initial plotting selected a macOS GUI backend and aborted; the cleaning script now explicitly selects the noninteractive Agg backend. Initial old-package runs produced pandas compatibility warnings; the final isolated pinned environment passed without those warnings.

Raw inputs are excluded from Git. The live API can change, and fully identical future results require the same metadata bytes; the committed manifest identifies this review's snapshot. Source completeness does not establish measurement accuracy or resolve unit-specific historical counting errors.
