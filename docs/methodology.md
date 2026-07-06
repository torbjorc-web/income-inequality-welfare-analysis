# Methodology

1. Collect relevant public datasets.
2. Ingest raw files to SQLite (`setup_database.py`).
3. Clean and standardize indicators into analysis tables (`scripts/clean_data.py`).
4. Generate comparative summaries and output artifacts (`scripts/analyze_data.py`, `scripts/make_charts.py`).
5. Serve interactive analysis in Streamlit (`dashboard.py`).
6. Optionally extend the country set with validated CSV uploads (stored in `user_country_indicators`).

## Dashboard upload methodology

User-provided country CSV data is integrated through a controlled mapping and validation flow:

1. User uploads CSV in the Streamlit sidebar.
2. User maps source columns to normalized fields.
3. Required quality checks run before import:
	- `year` numeric and in [1900, 2100]
	- `gini` numeric and in [0, 1]
	- no duplicate `country` + `year` rows in the same upload
4. Valid rows are normalized and appended to SQLite.
5. Uploaded countries are included in trends, rankings, comparisons, and welfare scatter views.

## Equivalence scales: SNA vs EU-skala

When comparing inequality or poverty across households, incomes are adjusted with an **equivalence scale** so households of different sizes can be compared more fairly.

- **EU-skala (modified OECD scale)** gives standard weights to adults and children and is widely used in European inequality/poverty statistics.
- **SNA-skala** applies a different weighting logic and can give higher weights for some age groups than the EU-skala.

In this project, both scales are included (see `norway_public_services_5`) to show that measured inequality/poverty can change depending on the chosen scale.  
This means that scale choice is a methodological decision, not just a technical detail, and should be stated clearly when interpreting results.
