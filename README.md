# Income Inequality, Poverty and Welfare Analysis

![Project Cover](assets/cover.png)

![Status](https://img.shields.io/badge/status-in%20progress-orange?style=for-the-badge)
![Data](https://img.shields.io/badge/data-official%20statistics-blue?style=for-the-badge)
![Focus](https://img.shields.io/badge/focus-data%20analysis%20%26%20visualization-green?style=for-the-badge)
![Countries](https://img.shields.io/badge/countries-Norway%20%7C%20USA%20%7C%20Philippines-purple?style=for-the-badge)

## Live App

- Streamlit dashboard: [Inequality & Welfare Dashboard](https://income-inequality-welfare-analysis-a9ngzr4evattkxng7oaxup.streamlit.app/)
- Embed-friendly URL: [Embedded dashboard view](https://income-inequality-welfare-analysis-a9ngzr4evattkxng7oaxup.streamlit.app/?embed=true)

## Overview

This project compares income inequality, poverty, and welfare systems across Norway, the United States, and the Philippines.

It uses official statistics and supporting research to show how public services, redistribution, and welfare policy shape the gap between rich and poor.

It examines how public services and equivalence scales change the interpretation of inequality and poverty, and uses SQL, pandas, and visualization tools to turn raw CSV data into portfolio-ready analysis.

For a short explanation of **SNA vs EU-skala** and why equivalence-scale choice matters, see `docs/methodology.md`.

## Presentation

- PowerPoint walkthrough: [income_inequality_welfare_analysis_presentation_polished.pptx](https://1drv.ms/p/c/4246acc26547a1fc/IQD3jhAcVuRPSYF4dYweL2VpAVFl818193NJHlZWpirrwmc?e=aM2McJ)

The presentation explains the project story from problem framing to data pipeline, dashboard design, core findings for Norway/USA/Philippines, and practical limitations in cross-country comparison.

## Video Walkthrough

- Project walkthrough video (main showcase): [Income Inequality, Poverty and Welfare Analysis (YouTube)](https://youtu.be/0tfy-TU_l4o)
- YouTube channel: [Project channel](https://www.youtube.com/channel/UCY4HNGfLRSIcls_4h6oq_PA)
- Weekly video ideas + channel about draft: [docs/video_plan.md](docs/video_plan.md)

Recommended video flow: problem context, data and method, live dashboard demo (including CSV upload), key findings, and next improvements.

## Why this project

I wanted to build a portfolio project that shows real data analysis skills, not just charts.

The project combines data collection, cleaning, comparison, visualization, and interpretation in a social and economic context.

## Problem Statement

Official inequality and poverty indicators are often presented separately and are hard to compare across countries with different welfare systems.
This project builds a repeatable pipeline to compare Norway, the USA, and the Philippines using transparent data cleaning, database storage, and clear visual outputs.

## Data Sources

- Statistics Norway (SSB)
- U.S. Census Bureau
- Philippine Statistics Authority (PSA)
- Supporting research on public services, inequality, and welfare effects

## Main Questions

- How does income distribution differ between the three countries?
- What do the data say about the gap between rich and poor?
- How do welfare systems and public services affect poverty and inequality?

## Method

1. Load raw source files into SQLite with `setup_database.py`.
2. Clean and normalize country-specific datasets with `scripts/clean_data.py`.
3. Generate analysis summaries and comparison metrics with `scripts/analyze_data.py`.
4. Generate publication-ready charts/tables with `scripts/make_charts.py`.
5. Fit and backtest a scikit-learn trend model for a selected indicator with `src/services/forecasting.py`.

## Run the project (end-to-end)

```bash
python setup_database.py
python scripts/clean_data.py
python scripts/analyze_data.py
python scripts/make_charts.py
```

Outputs are written to:

- `outputs/figures/` (charts)
- `outputs/tables/` (summary tables and text outputs)

## Run the Streamlit dashboard

```bash
pip install -r requirements.txt
```

```bash
streamlit run dashboard.py
```

The dashboard includes:

- interactive country/year/filter controls
- Norway/USA/Philippines comparison charts
- welfare-proxy scatter context
- CSV upload pipeline for adding custom country data into SQLite
- a **Trend forecast (machine learning)** section with scikit-learn predictions and backtest scores

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```

`pytest.ini` sets `testpaths = tests` and puts the repository root on `PYTHONPATH`, so `pytest`
works from the project root without any extra flags. Useful variations:

```bash
pytest tests/test_upload.py          # one module
pytest -k "gini and not dashboard"   # by name
pytest -q                            # quiet summary
```

What the suite covers:

| Test module | Under test |
| --- | --- |
| `tests/test_config.py` | project paths, required-table set, CSV upload template |
| `tests/test_repository.py` | SQLite loaders/writers and number parsing in `src/data/repository.py` |
| `tests/test_metrics.py` | Gini / P90-P10 / S80-S20 selection and series building |
| `tests/test_upload.py` | CSV column mapping and upload validation rules |
| `tests/test_bootstrap.py` | schema detection, bootstrap orchestration, idempotent table creation |
| `tests/test_setup_database.py` | delimiter/encoding detection and raw CSV ingestion |
| `tests/test_clean_data.py` | USA / Philippines / Norway cleaning transformations |
| `tests/test_analyze_data.py` | summary statistics and the analysis report writer |
| `tests/test_dashboard_app.py` | Streamlit `AppTest` smoke tests for `dashboard.py` |
| `tests/test_forecasting.py` | scikit-learn trend forecast and rolling-origin backtest |

Every test builds its own SQLite database and CSV fixtures under pytest's `tmp_path`, so the suite
never reads or writes `database/database.db`, `data/`, or `outputs/`.

## Dashboard Screenshots

![Dashboard overview](outputs/dashboard_screenshots/dashboard_overview.png)
![Gini mode view](outputs/dashboard_screenshots/dashboard_gini_mode.png)
![Lower panels](outputs/dashboard_screenshots/dashboard_lower_panels.png)

## Data, Method, and Key Findings

Data sources:

- Statistics Norway (SSB)
- U.S. Census Bureau
- Philippine Statistics Authority (PSA)

Method summary:

1. Load raw data to SQLite (`setup_database.py`).
2. Clean/normalize country tables (`scripts/clean_data.py`).
3. Build comparisons and summaries (`scripts/analyze_data.py`).
4. Serve interactive analysis via Streamlit (`dashboard.py`).

Key findings (current snapshot):

- Norway has the lowest headline inequality (latest Gini in project data).
- USA has the highest headline inequality in the comparison.
- Philippines improved national Gini over time but remains above Norway.

## Publish DB changes to GitHub (one command)

Use the release helper to rebuild data artifacts, run checks, and create a consistent commit.

```bash
python scripts/release_db_snapshot.py
```

What it does:

1. Runs `setup_database.py`
2. Runs `scripts/clean_data.py`
3. Runs `scripts/analyze_data.py`
4. Runs `scripts/make_charts.py` (unless `--skip-charts`)
5. Stages `database/database.db`, `data/processed/`, and `outputs/tables/`
6. Commits and pushes to `origin/main`

Useful flags:

- `--message "your commit message"`
- `--skip-push` (create local commit only)
- `--skip-charts` (faster run)

## Add your own country data in the dashboard

The Streamlit dashboard supports importing country-level inequality data from CSV.

1. Open the dashboard and expand `Add your own country data (CSV)` in the sidebar.
2. Download the template from the app or use `data/country_upload_template.csv`.
3. Upload your CSV and map columns in the UI.
4. Run `Validate and import CSV`.

Minimum required fields:

- `country` (or fixed country name in the UI)
- `year`
- `gini`

Optional fields:

- `p90_p10`
- `s80_s20`
- `welfare_proxy_value`
- `welfare_proxy_label`
- `source`
- `notes`

Validation rules:

- `year` must be numeric and between 1900 and 2100
- `gini` must be numeric and between 0 and 1
- no duplicate `country` + `year` rows in one upload

Imported rows are stored in SQLite and included in country selector, trend chart, ranking, and comparison views.

## Repository Structure

- `data/raw/` — original source files.
- `data/processed/` — cleaned and combined datasets.
- `notebooks/` — exploration and analysis notebooks.
- `scripts/` — reusable Python scripts for cleaning and analysis.
- `src/` — dashboard application code (config, SQLite repository, services incl. the ML forecast).
- `tests/` — pytest suite covering the service layer, data access, scripts, and the dashboard.
- `outputs/` — charts, tables, and screenshots.
- `docs/` — project description, methodology, and references.
- `assets/` — cover image and badge notes.

Additional docs:

- `docs/data_dictionary.md` — table and column definitions for core datasets.
- `docs/reflection.md` — lessons learned, challenges, and next improvements.

## Machine learning: inequality trend forecast

The dashboard includes a scikit-learn regression model that projects an inequality indicator
forward in time (`src/services/forecasting.py`).

- **Task:** univariate time-trend regression. Predict a country's Gini, P90/P10, or S80/S20 for
  future years from its own history. Regression was chosen over classification because the annual
  Norwegian series and the Philippine survey series are the only parts of the data with enough
  repeated observations to learn from.
- **Data:** Norway 2001-2024 (24 annual points, all three indicators) and Philippine regional Gini
  for 2009-2023 (6 survey points per region). The USA extract only covers 2023-2024 and is
  therefore excluded from forecasting.
- **Models:** `LinearRegression` on the year offset, or `PolynomialFeatures(2)` +
  `StandardScaler` + `Ridge` for a curved trend.
- **Evaluation:** rolling-origin (walk-forward) backtest rather than a shuffled split, scored with
  MAE, RMSE, and R-squared, and always compared against a naive last-value baseline.
- **Honest result:** for Norway's Gini and S80/S20 the naive baseline *beats* the model — those
  series are essentially flat with irregular spikes, so there is no smooth trend to learn. The
  dashboard says so explicitly. Norway's P90/P10 and the declining Philippine Gini series are
  where the trend model actually helps.
- **Caveats:** sample sizes are very small by ML standards, the model uses calendar time as its
  only feature, and it cannot anticipate policy changes or shocks.

See `docs/methodology.md` for the full write-up. Run the tests with `pytest` (see [Running tests](#running-tests)).

## What I Am Building

- Cleaned datasets.
- Comparison tables.
- Charts and dashboards.
- A short portfolio-ready explanation of the findings.

## Current Status

Active and deployable.

- Core ETL pipeline is in place (raw CSV -> SQLite -> cleaned tables).
- Streamlit dashboard is live and updated from the `main` branch.
- Country CSV upload pipeline is implemented with mapping, validation, and persistence.
- A scikit-learn trend forecast with walk-forward backtesting is surfaced in the dashboard.

## Findings (current snapshot)

- **Norway:** lower inequality level overall, but a gradual increase over time.
- **USA:** higher inequality, with a more market-driven distribution pattern.
- **Philippines:** a stronger poverty challenge and a different welfare context than Norway/USA.

## Chart and table interpretation (short)

- `gini_usa_norway_philippines*.png`: compares headline national inequality levels (Gini) across the three countries.
- `norway_gini_p90p10_s80s20.png`: shows that different inequality indicators in Norway move together over time.
- `usa_norway_comparison.png`: highlights the gap between Norway and USA on latest available Gini and P90/P10 ratios.
- `country_headline_comparison.md`: compact, portfolio-ready comparison table with key context indicators.

## Troubleshooting

- App does not load on Streamlit Cloud:
  - Check `requirements.txt` includes `streamlit`, `pandas`, and `matplotlib`.
  - Confirm app entrypoint is `dashboard.py` on the `main` branch.
- Database tables missing or stale locally:
  - Run `python setup_database.py` then `python scripts/clean_data.py`.
  - Or run `python scripts/release_db_snapshot.py --skip-push` for a full local rebuild.
- Notebook diagnostics show undefined names:
  - Run notebook cells in order from top to bottom.
  - Ensure `database/database.db` exists before running analysis notebooks.
