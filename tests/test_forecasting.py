import numpy as np
import pandas as pd
import pytest

from src.services.forecasting import (
    MIN_OBSERVATIONS,
    MODEL_CHOICES,
    build_norway_series,
    build_ph_region_series,
    combined_chart_frame,
    forecast_series,
    rolling_origin_backtest,
)


@pytest.fixture
def norway_df():
    years = list(range(2001, 2025))
    return pd.DataFrame(
        {
            "year": years,
            "gini_all_population": [0.23 + 0.001 * i for i in range(len(years))],
            "gini_excl_student_households": [0.22 + 0.001 * i for i in range(len(years))],
        }
    )


@pytest.fixture
def ph_df():
    return pd.DataFrame(
        [
            {
                "region": "Philippines",
                "gini_2009": 0.4641,
                "gini_2012": 0.4605,
                "gini_2015": 0.4438,
                "gini_2018": 0.4267,
                "gini_2021": 0.4063,
                "gini_2023": 0.3909,
            },
            {
                "region": "NIR",
                "gini_2009": None,
                "gini_2012": None,
                "gini_2015": None,
                "gini_2018": None,
                "gini_2021": 0.4114,
                "gini_2023": 0.4031,
            },
        ]
    )


def test_norway_series_respects_population_definition(norway_df):
    all_pop = build_norway_series(norway_df, "Gini", exclude_students=False)
    excl = build_norway_series(norway_df, "Gini", exclude_students=True)
    assert list(all_pop.columns) == ["year", "value"]
    assert len(all_pop) == 24
    assert all_pop["value"].iloc[0] == pytest.approx(0.23)
    assert excl["value"].iloc[0] == pytest.approx(0.22)


def test_ph_series_drops_missing_survey_years(ph_df):
    national = build_ph_region_series(ph_df, "Philippines")
    sparse = build_ph_region_series(ph_df, "NIR")
    assert national["year"].tolist() == [2009, 2012, 2015, 2018, 2021, 2023]
    assert sparse["year"].tolist() == [2021, 2023]
    assert build_ph_region_series(ph_df, "Nowhere").empty


def test_forecast_rejects_too_few_observations(ph_df):
    with pytest.raises(ValueError, match=str(MIN_OBSERVATIONS)):
        forecast_series(build_ph_region_series(ph_df, "NIR"))


@pytest.mark.parametrize("model_name", MODEL_CHOICES)
def test_forecast_recovers_a_clean_linear_trend(model_name):
    series = pd.DataFrame({"year": range(2000, 2020), "value": [0.3 + 0.01 * i for i in range(20)]})
    result = forecast_series(series, model_name=model_name, horizon=3)

    assert result.forecast["year"].tolist() == [2020, 2021, 2022]
    assert result.forecast["predicted"].tolist() == pytest.approx([0.50, 0.51, 0.52], abs=0.02)
    assert result.metrics["mae"] < 0.01
    assert result.caveats


def test_forecast_honours_step_for_irregular_survey_years(ph_df):
    result = forecast_series(build_ph_region_series(ph_df, "Philippines"), horizon=2, step=2)
    assert result.forecast["year"].tolist() == [2025, 2027]
    # National Gini has fallen steadily since 2009, so the trend must keep declining.
    assert result.forecast["predicted"].is_monotonic_decreasing
    assert result.forecast["predicted"].iloc[0] < 0.3909


def test_backtest_is_walk_forward_and_reports_a_baseline():
    series = pd.DataFrame({"year": range(2000, 2012), "value": np.linspace(0.3, 0.4, 12)})
    backtest = rolling_origin_backtest(series, "Linear trend", min_train=4)

    assert backtest["year"].tolist() == list(range(2004, 2012))
    # The baseline for each held-out year is the previous year's actual value.
    assert backtest["baseline"].tolist() == pytest.approx(series["value"].iloc[3:-1].tolist())


def test_chart_frame_aligns_history_and_forecast(norway_df):
    result = forecast_series(build_norway_series(norway_df, "Gini", False), horizon=2)
    frame = combined_chart_frame(result)

    assert list(frame.columns) == ["Actual", "Forecast"]
    assert frame.index.tolist() == list(range(2001, 2027))
    assert frame.loc[2024, "Actual"] == pytest.approx(0.253)
    assert pd.isna(frame.loc[2024, "Forecast"])
    assert pd.isna(frame.loc[2026, "Actual"])
