import numpy as np
import pandas as pd
import pytest

from src.services.metrics import (
    build_ph_gini_series,
    build_usa_gini_series,
    choose_latest_not_after,
    get_ph_gini_improvement,
    pick_ph_gini,
    pick_usa_value,
)


def test_choose_latest_not_after_picks_the_most_recent_eligible_row(norway_df):
    assert choose_latest_not_after(norway_df, 2022)["year"] == 2022
    # 2023 has no gap, but an in-between year must fall back to the previous observation.
    assert choose_latest_not_after(norway_df, 2030)["year"] == 2024


def test_choose_latest_not_after_returns_none_before_the_series_starts(norway_df):
    assert choose_latest_not_after(norway_df, 1999) is None


def test_pick_usa_value_prefers_2024_from_2024_onwards(usa_df):
    assert pick_usa_value(usa_df, "Gini index of income inequality", 2024) == (0.478, 2024)
    assert pick_usa_value(usa_df, "Gini index of income inequality", 2030) == (0.478, 2024)


def test_pick_usa_value_falls_back_to_2023_for_earlier_reference_years(usa_df):
    assert pick_usa_value(usa_df, "Gini index of income inequality", 2023) == (0.470, 2023)
    assert pick_usa_value(usa_df, "90th/10th percentile income ratio", 2020) == (12.60, 2023)


def test_pick_usa_value_falls_back_to_2023_when_2024_is_missing(usa_df):
    usa_df.loc[usa_df["measure"] == "Gini index of income inequality", "year_2024_estimate"] = None

    assert pick_usa_value(usa_df, "Gini index of income inequality", 2024) == (0.470, 2023)


def test_pick_usa_value_returns_none_pair_for_unknown_or_empty_measures(usa_df):
    assert pick_usa_value(usa_df, "Not a measure", 2024) == (None, None)

    usa_df.loc[:, ["year_2023_estimate", "year_2024_estimate"]] = np.nan
    assert pick_usa_value(usa_df, "Gini index of income inequality", 2024) == (None, None)


def test_pick_usa_value_ignores_other_income_types(usa_df):
    usa_df["income_type"] = "EQUIVALENCE-ADJUSTED INCOME"

    assert pick_usa_value(usa_df, "Gini index of income inequality", 2024) == (None, None)


@pytest.mark.parametrize(
    "reference_year,expected",
    [
        (2009, (0.4641, 2009)),
        (2011, (0.4641, 2009)),
        (2018, (0.4267, 2018)),
        (2023, (0.3909, 2023)),
        (2050, (0.3909, 2023)),
    ],
)
def test_pick_ph_gini_uses_the_latest_survey_not_after_the_reference_year(
    ph_row, reference_year, expected
):
    assert pick_ph_gini(ph_row, reference_year) == expected


def test_pick_ph_gini_returns_none_pair_before_the_first_survey(ph_row):
    assert pick_ph_gini(ph_row, 2008) == (None, None)


def test_pick_ph_gini_skips_missing_survey_years():
    sparse = pd.Series(
        {
            "gini_2009": None,
            "gini_2012": None,
            "gini_2015": None,
            "gini_2018": None,
            "gini_2021": 0.3114,
            "gini_2023": None,
        }
    )

    assert pick_ph_gini(sparse, 2023) == (0.3114, 2021)


def test_build_usa_gini_series_emits_one_row_per_available_estimate(usa_df):
    series = build_usa_gini_series(usa_df)

    assert series["year"].tolist() == [2023, 2024]
    assert series["country"].unique().tolist() == ["USA"]
    assert series["gini"].tolist() == pytest.approx([0.470, 0.478])


def test_build_usa_gini_series_is_empty_when_the_measure_is_absent(usa_df):
    series = build_usa_gini_series(usa_df[usa_df["measure"] != "Gini index of income inequality"])

    assert series.empty
    assert list(series.columns) == ["country", "year", "gini"]


def test_build_ph_gini_series_covers_all_survey_years(ph_row):
    series = build_ph_gini_series(ph_row)

    assert series["year"].tolist() == [2009, 2012, 2015, 2018, 2021, 2023]
    assert series["gini"].is_monotonic_decreasing


def test_build_ph_gini_series_drops_missing_years():
    sparse = pd.Series(
        {
            "gini_2009": None,
            "gini_2012": None,
            "gini_2015": None,
            "gini_2018": None,
            "gini_2021": 0.3114,
            "gini_2023": 0.3031,
        }
    )

    assert build_ph_gini_series(sparse)["year"].tolist() == [2021, 2023]


def test_ph_gini_improvement_is_the_drop_between_2009_and_2023(ph_row):
    assert get_ph_gini_improvement(ph_row) == pytest.approx(0.4641 - 0.3909)


def test_ph_gini_improvement_is_none_when_an_endpoint_is_missing(ph_row):
    ph_row["gini_2009"] = None

    assert get_ph_gini_improvement(ph_row) is None
