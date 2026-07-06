# Project Reflection

## What Worked Well

- Building a reproducible pipeline from raw CSV files to SQLite and cleaned tables.
- Keeping the dashboard and scripts aligned with shared table structures.
- Adding country upload support made the app extensible without code changes.
- Iterating quickly on deployment and documentation improved project usability.

## Main Challenges

- Source files use mixed delimiters, encodings, and table layouts.
- Some indicators are not perfectly comparable across countries.
- SQLite snapshots are useful for deployment consistency, but are binary and harder to diff.
- Notebook and markdown lint issues required cleanup to keep the repository polished.

## What I Learned

- Data normalization choices strongly influence how reliable cross-country comparisons are.
- Clear repository documentation is as important as code for portfolio presentation.
- Streamlit deployment is straightforward when dependencies, entrypoint, and paths are stable.
- Small quality checks (linting, diagnostics, smoke tests) prevent broken public demos.

## Next Improvements

- Add a short video walkthrough and replace placeholder link in README.
- Add chart-level caveats for comparability next to each visualization type.
- Introduce simple tests for core metric helper functions.
- Consider persisting user-upload data in managed storage for multi-user robustness.
