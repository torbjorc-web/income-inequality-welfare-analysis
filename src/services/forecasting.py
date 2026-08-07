"""Trend forecasting for country inequality indicators.

The project only has genuine annual time series for Norway (2001-2024) and
irregular survey years for the Philippines (2009-2023), so the modelling task is
a small-sample univariate trend regression on the year index, backtested with a
rolling origin and compared against a naive last-value baseline.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

MODEL_CHOICES = ("Linear trend", "Ridge quadratic trend")

NORWAY_METRICS = {
    "Gini": ("gini_all_population", "gini_excl_student_households"),
    "P90/P10": ("p90_p10_all_population", "p90_p10_excl_student_households"),
    "S80/S20": ("s80_s20_all_population", "s80_s20_excl_student_households"),
}

PH_GINI_YEARS = (2009, 2012, 2015, 2018, 2021, 2023)

MIN_OBSERVATIONS = 5


@dataclass
class ForecastResult:
    history: pd.DataFrame
    forecast: pd.DataFrame
    backtest: pd.DataFrame
    metrics: dict
    model_name: str
    caveats: list[str] = field(default_factory=list)


def build_norway_series(norway_df: pd.DataFrame, metric: str, exclude_students: bool) -> pd.DataFrame:
    all_col, excl_col = NORWAY_METRICS[metric]
    column = excl_col if exclude_students else all_col
    series = norway_df[["year", column]].rename(columns={column: "value"})
    return _tidy_series(series)


def build_ph_region_series(ph_df: pd.DataFrame, region: str) -> pd.DataFrame:
    rows = ph_df[ph_df["region"] == region]
    if rows.empty:
        return pd.DataFrame(columns=["year", "value"])
    row = rows.iloc[0]
    series = pd.DataFrame(
        [{"year": year, "value": row[f"gini_{year}"]} for year in PH_GINI_YEARS]
    )
    return _tidy_series(series)


def build_user_country_series(user_df: pd.DataFrame, country: str, metric_column: str) -> pd.DataFrame:
    rows = user_df[user_df["country"] == country][["year", metric_column]]
    return _tidy_series(rows.rename(columns={metric_column: "value"}))


def _tidy_series(series: pd.DataFrame) -> pd.DataFrame:
    tidy = series.copy()
    tidy["year"] = pd.to_numeric(tidy["year"], errors="coerce")
    tidy["value"] = pd.to_numeric(tidy["value"], errors="coerce")
    return tidy.dropna().astype({"year": int}).sort_values("year").reset_index(drop=True)


def build_model(model_name: str) -> Pipeline:
    if model_name == "Ridge quadratic trend":
        return Pipeline(
            [
                ("poly", PolynomialFeatures(degree=2, include_bias=False)),
                ("scale", StandardScaler()),
                ("model", Ridge(alpha=1.0)),
            ]
        )
    if model_name == "Linear trend":
        return Pipeline([("model", LinearRegression())])
    raise ValueError(f"Unknown model: {model_name}")


def _design_matrix(years: np.ndarray, base_year: int) -> np.ndarray:
    return (years - base_year).reshape(-1, 1).astype(float)


def rolling_origin_backtest(series: pd.DataFrame, model_name: str, min_train: int = 4) -> pd.DataFrame:
    """Walk-forward validation: fit on all observations before a year, predict it."""
    records = []
    base_year = int(series["year"].iloc[0])
    for split in range(min_train, len(series)):
        train, test = series.iloc[:split], series.iloc[split]
        model = build_model(model_name)
        model.fit(_design_matrix(train["year"].to_numpy(), base_year), train["value"].to_numpy())
        predicted = float(
            model.predict(_design_matrix(np.array([test["year"]]), base_year))[0]
        )
        records.append(
            {
                "year": int(test["year"]),
                "actual": float(test["value"]),
                "predicted": predicted,
                "baseline": float(train["value"].iloc[-1]),
            }
        )
    return pd.DataFrame(records)


def _score(backtest: pd.DataFrame) -> dict:
    actual, predicted = backtest["actual"], backtest["predicted"]
    metrics = {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(np.mean((actual - predicted) ** 2))),
        "baseline_mae": float(mean_absolute_error(actual, backtest["baseline"])),
        "n_backtest": len(backtest),
    }
    # R^2 is undefined for a single point and unstable when actuals barely vary.
    if len(backtest) >= 3 and actual.std(ddof=0) > 0:
        metrics["r2"] = float(r2_score(actual, predicted))
    return metrics


def forecast_series(
    series: pd.DataFrame,
    model_name: str = "Linear trend",
    horizon: int = 5,
    step: int = 1,
) -> ForecastResult:
    if len(series) < MIN_OBSERVATIONS:
        raise ValueError(
            f"Need at least {MIN_OBSERVATIONS} observations to fit a trend model, got {len(series)}."
        )

    base_year = int(series["year"].iloc[0])
    model = build_model(model_name)
    model.fit(
        _design_matrix(series["year"].to_numpy(), base_year),
        series["value"].to_numpy(),
    )

    last_year = int(series["year"].iloc[-1])
    future_years = np.array([last_year + step * i for i in range(1, horizon + 1)])
    predictions = model.predict(_design_matrix(future_years, base_year))
    forecast = pd.DataFrame({"year": future_years.astype(int), "predicted": predictions})

    backtest = rolling_origin_backtest(series, model_name)
    metrics = _score(backtest)

    return ForecastResult(
        history=series,
        forecast=forecast,
        backtest=backtest,
        metrics=metrics,
        model_name=model_name,
        caveats=_build_caveats(series, metrics, model_name),
    )


def _build_caveats(series: pd.DataFrame, metrics: dict, model_name: str) -> list[str]:
    caveats = [
        f"Fitted on {len(series)} observations ({series['year'].iloc[0]}-{series['year'].iloc[-1]}); "
        "this is a very small sample by machine-learning standards.",
        "The model extrapolates a smooth trend in calendar time only. It has no policy, "
        "macroeconomic, or survey-methodology inputs, so it cannot anticipate shocks or reforms.",
    ]
    if metrics["n_backtest"] < 5:
        caveats.append(
            "Backtest uses fewer than 5 held-out years, so the error estimates are themselves noisy."
        )
    if "r2" not in metrics:
        caveats.append("R^2 is omitted because too few held-out points are available to be meaningful.")
    if metrics["mae"] > metrics["baseline_mae"]:
        caveats.append(
            "The naive last-value baseline beats the model on backtest MAE, so the trend fit adds no "
            "predictive value for this series."
        )
    if model_name == "Ridge quadratic trend":
        caveats.append(
            "Quadratic trends extrapolate aggressively; treat forecasts more than a few years out as illustrative."
        )
    return caveats


def combined_chart_frame(result: ForecastResult) -> pd.DataFrame:
    """Long history/forecast frame indexed by year, ready for st.line_chart."""
    history = result.history.rename(columns={"value": "Actual"}).set_index("year")[["Actual"]]
    forecast = result.forecast.rename(columns={"predicted": "Forecast"}).set_index("year")[["Forecast"]]
    return history.join(forecast, how="outer")
