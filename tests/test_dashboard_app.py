import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import dashboard
from src import config
from src.data.bootstrap import ensure_user_country_table
from src.data.repository import save_user_country_data


DASHBOARD_PATH = str(config.BASE_DIR / "dashboard.py")


@pytest.fixture
def app(populated_db, monkeypatch):
    """Run dashboard.py against a temp database instead of the committed one."""
    ensure_user_country_table(populated_db, config.USER_COUNTRY_TABLE)
    monkeypatch.setattr(config, "DB_PATH", populated_db)
    monkeypatch.setattr(config, "BASE_DIR", populated_db.parent.parent)
    # The loaders take an underscore-prefixed path, which Streamlit excludes from the
    # cache key, so every test would otherwise reuse the first test's database.
    st.cache_data.clear()
    yield AppTest.from_file(DASHBOARD_PATH, default_timeout=60)
    st.cache_data.clear()


@pytest.fixture
def ph_regions_df(populated_db):
    from src.data.repository import load_ph_regions

    return load_ph_regions(populated_db)


def test_forecast_source_options_lists_norway_and_long_enough_regions(ph_regions_df):
    options = dashboard.forecast_source_options(ph_regions_df, pd.DataFrame({"country": []}))

    assert "Norway" in options
    assert options["Norway"] == ("norway", None)
    assert options["Philippines - Philippines"] == ("philippines", "Philippines")
    # BARMM only has two survey observations, which is below MIN_OBSERVATIONS.
    assert "Philippines - BARMM" not in options


def test_forecast_source_options_includes_uploaded_countries_with_enough_history(ph_regions_df):
    user_df = pd.DataFrame(
        {
            "country": ["Kenya"] * 6,
            "year": [2015, 2016, 2017, 2018, 2019, 2020],
            "gini": [0.45, 0.44, 0.43, 0.42, 0.41, 0.40],
        }
    )

    options = dashboard.forecast_source_options(ph_regions_df, user_df)

    assert options["Kenya (uploaded)"] == ("user", "Kenya")


def test_forecast_source_options_skips_uploaded_countries_with_short_history(ph_regions_df):
    user_df = pd.DataFrame({"country": ["Kenya", "Kenya"], "year": [2019, 2020], "gini": [0.41, 0.40]})

    assert "Kenya (uploaded)" not in dashboard.forecast_source_options(ph_regions_df, user_df)


def test_app_runs_without_raising(app):
    app.run()

    assert not app.exception


def test_app_renders_title_and_headline_metrics(app):
    app.run()

    assert app.title[0].value == "Inequality & Welfare Dashboard"
    labels = [metric.label for metric in app.metric]
    assert "Norway Gini" in labels
    assert "USA Gini" in labels
    assert "Philippines Gini" in labels


def test_app_metric_values_match_the_fixture_database(app):
    app.run()

    values = {metric.label: metric.value for metric in app.metric}
    assert values["Norway Gini"] == "0.251"
    assert values["USA Gini"] == "0.478"
    assert values["Philippines Gini"] == "0.391"


def test_app_renders_the_sidebar_controls(app):
    app.run()

    assert app.sidebar.selectbox[0].label == "Norway population definition"
    assert set(app.sidebar.multiselect[0].value) == {"Norway", "USA", "Philippines"}


def test_app_renders_the_forecast_section(app):
    app.run()

    headers = [header.value for header in app.header]
    assert "Trend forecast (machine learning)" in headers
    assert any(metric.label == "Backtest MAE" for metric in app.metric)


def test_switching_population_definition_updates_the_norway_metric(app):
    app.run()
    app.sidebar.selectbox[0].set_value("Excl. student households").run()

    values = {metric.label: metric.value for metric in app.metric}
    assert values["Norway Gini"] == "0.241"
    assert not app.exception


def test_app_surfaces_uploaded_countries(app, populated_db):
    save_user_country_data(
        populated_db,
        config.USER_COUNTRY_TABLE,
        pd.DataFrame(
            [
                {
                    "country": "Kenya",
                    "year": 2021,
                    "gini": 0.40,
                    "p90_p10": 9.1,
                    "s80_s20": 6.8,
                    "welfare_proxy_value": 13.0,
                    "welfare_proxy_label": "Coverage",
                    "source": "KNBS",
                    "notes": "",
                }
            ]
        ),
    )

    app.run()

    assert "Kenya" in app.sidebar.multiselect[0].options
    assert not app.exception
