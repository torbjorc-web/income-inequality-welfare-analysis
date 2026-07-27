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

## Trend forecasting model (scikit-learn)

The dashboard section **Trend forecast (machine learning)** fits a supervised regression model
(`src/services/forecasting.py`) that projects a single inequality indicator forward in time.

**Task choice.** Regression, not classification. Only Norway (`gini`, `p90_p10`, `s80_s20`, annual
2001-2024) and the Philippines (regional Gini for the survey years 2009, 2012, 2015, 2018, 2021,
2023) have enough repeated observations to learn from. The USA extract only covers 2023 and 2024,
so it is excluded from forecasting. A country classifier was rejected: with three countries whose
Gini ranges barely overlap, the task would be trivially separable and would not show anything the
descriptive charts do not already show.

**Features and target.** The single feature is the year, expressed as an offset from the first
observed year of the series. The target is the indicator value. Two models are offered:

| Model | Pipeline |
| --- | --- |
| Linear trend | `LinearRegression` on the year offset |
| Ridge quadratic trend | `PolynomialFeatures(degree=2)` -> `StandardScaler` -> `Ridge(alpha=1.0)` |

**Validation.** A rolling-origin (walk-forward) backtest is used rather than a random train/test
split, because shuffling would leak future observations into training. The model is fitted on the
first four observations, asked to predict the fifth, then refitted with five, and so on. Reported
scores are MAE, RMSE, and R-squared over the held-out years, alongside the MAE of a **naive
last-value baseline** that repeats the previous observation. R-squared is suppressed when fewer
than three held-out points are available, since it is not meaningful there.

**Limitations.** These are shown in the dashboard next to every forecast:

- Sample sizes are tiny (24 annual points for Norway, 6 survey points per Philippine region), so
  the error estimates are themselves noisy.
- The model sees calendar time only. It has no policy, macroeconomic, or survey-methodology
  inputs, so it cannot anticipate reforms or shocks.
- For **Norway's Gini and S80/S20 the naive baseline beats both models** on backtest MAE, and the
  backtest R-squared is negative. Norway's Gini is close to flat with irregular spikes (2005,
  2021), so there is no smooth trend to learn. This is reported in the UI rather than hidden: a
  model that does not beat its baseline is a result, not a failure. Norway's P90/P10 is the one
  series where the trend fit adds value (positive R-squared).
- Quadratic fits extrapolate aggressively; forecasts more than a few periods out are illustrative.
- Philippine survey years are irregularly spaced, so forecasts step forward in two-year intervals
  and should be read as approximate.

## Equivalence scales: SNA vs EU-skala

When comparing inequality or poverty across households, incomes are adjusted with an **equivalence scale** so households of different sizes can be compared more fairly.

- **EU-skala (modified OECD scale)** gives standard weights to adults and children and is widely used in European inequality/poverty statistics.
- **SNA-skala** applies a different weighting logic and can give higher weights for some age groups than the EU-skala.

In this project, both scales are included (see `norway_public_services_5`) to show that measured inequality/poverty can change depending on the chosen scale.  
This means that scale choice is a methodological decision, not just a technical detail, and should be stated clearly when interpreting results.
