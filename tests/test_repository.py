import sqlite3

import pandas as pd
import pytest

from src.data.bootstrap import ensure_user_country_table
from src.data.repository import (
    get_norway_welfare_total,
    get_usa_lowest_quintile_share,
    load_core_data,
    load_ph_regions,
    load_user_country_data,
    parse_number,
    save_user_country_data,
)

USER_COLUMNS = [
    "country",
    "year",
    "gini",
    "p90_p10",
    "s80_s20",
    "welfare_proxy_value",
    "welfare_proxy_label",
    "source",
    "notes",
]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1,5", 1.5),
        ("1.5", 1.5),
        ("12 345", 12345.0),
        ("47%", 47.0),
        ("-0.25", -0.25),
        ("3,2 pst", 3.2),
        (2.5, 2.5),
        (None, None),
        ("", None),
        ("   ", None),
        ("n/a", None),
        ("..", None),
    ],
)
def test_parse_number_handles_norwegian_and_dirty_values(raw, expected):
    assert parse_number(raw) == expected


@pytest.fixture
def user_db(populated_db):
    ensure_user_country_table(populated_db, "user_country_indicators")
    return populated_db


def test_load_core_data_returns_all_five_components(populated_db):
    norway, usa, ph, welfare_total, quintile_share = load_core_data(populated_db)

    assert list(norway["year"]) == list(range(2015, 2025))
    assert len(usa) == 4
    assert ph["region"] == "Philippines"
    assert welfare_total == pytest.approx(1.5 + 3.0 + 2.5 + 4.0)
    assert quintile_share == pytest.approx(3.1)


def test_load_core_data_orders_norway_by_year(populated_db):
    with sqlite3.connect(populated_db) as conn:
        conn.execute("UPDATE norway_inequality_indicators_clean SET year = 2010 WHERE year = 2024")
        conn.commit()

    norway, _, _, _, _ = load_core_data(populated_db)
    assert list(norway["year"]) == [2010] + list(range(2015, 2024))


def test_load_core_data_raises_when_database_is_missing(db_path):
    with pytest.raises(FileNotFoundError, match="Database not found"):
        load_core_data(db_path)


@pytest.mark.parametrize(
    "empty_table,message",
    [
        ("norway_inequality_indicators_clean", "norway_inequality_indicators_clean is empty"),
        ("usa_clean", "usa_clean is empty"),
        ("philippines_clean", "National row not found"),
    ],
)
def test_load_core_data_rejects_empty_tables(populated_db, empty_table, message):
    with sqlite3.connect(populated_db) as conn:
        conn.execute(f"DELETE FROM {empty_table}")
        conn.commit()

    with pytest.raises(ValueError, match=message):
        load_core_data(populated_db)


def test_norway_welfare_total_is_none_when_a_component_is_unparsable(populated_db):
    with sqlite3.connect(populated_db) as conn:
        conn.execute("UPDATE norway_public_services SET Helse = '..' WHERE Land = 'Norge'")
        conn.commit()
        assert get_norway_welfare_total(conn) is None


def test_norway_welfare_total_is_none_when_no_norway_row_exists(populated_db):
    with sqlite3.connect(populated_db) as conn:
        conn.execute("DELETE FROM norway_public_services WHERE TRIM(Land) IN ('Norge', 'Norway')")
        conn.commit()
        assert get_norway_welfare_total(conn) is None


def test_usa_lowest_quintile_share_is_none_when_the_measure_is_absent(populated_db):
    with sqlite3.connect(populated_db) as conn:
        conn.execute("DELETE FROM usa_clean WHERE measure = 'Lowest quintile'")
        conn.commit()
        assert get_usa_lowest_quintile_share(conn) is None


def test_load_ph_regions_returns_every_region(populated_db):
    regions = load_ph_regions(populated_db)

    assert list(regions["region"]) == ["Philippines", "NCR", "BARMM"]
    assert set(regions.columns) == {
        "region",
        "gini_2009",
        "gini_2012",
        "gini_2015",
        "gini_2018",
        "gini_2021",
        "gini_2023",
    }
    assert regions.loc[regions["region"] == "BARMM", "gini_2009"].isna().all()


def test_load_ph_regions_raises_when_database_is_missing(db_path):
    with pytest.raises(FileNotFoundError, match="Database not found"):
        load_ph_regions(db_path)


def test_load_user_country_data_returns_empty_frame_when_database_is_missing(db_path):
    df = load_user_country_data(db_path, "user_country_indicators")

    assert df.empty
    assert list(df.columns) == USER_COLUMNS


def test_load_user_country_data_returns_empty_frame_when_table_is_missing(populated_db):
    df = load_user_country_data(populated_db, "user_country_indicators")

    assert df.empty
    assert list(df.columns) == USER_COLUMNS


def test_save_then_load_round_trips_and_sorts(user_db):
    df = pd.DataFrame(
        [
            {
                "country": "  Kenya  ",
                "year": 2021,
                "gini": 0.40,
                "p90_p10": 9.5,
                "s80_s20": 7.1,
                "welfare_proxy_value": 12.0,
                "welfare_proxy_label": "Coverage",
                "source": "KNBS",
                "notes": "note",
            },
            {
                "country": "Kenya",
                "year": 2019,
                "gini": 0.42,
                "p90_p10": None,
                "s80_s20": None,
                "welfare_proxy_value": None,
                "welfare_proxy_label": "  ",
                "source": "",
                "notes": "",
            },
        ]
    )

    save_user_country_data(user_db, "user_country_indicators", df)
    loaded = load_user_country_data(user_db, "user_country_indicators")

    assert list(loaded["year"]) == [2019, 2021]
    assert set(loaded["country"]) == {"Kenya"}
    assert loaded.loc[0, ["p90_p10", "s80_s20", "welfare_proxy_value"]].isna().all()
    # Blank optional text is stored as SQL NULL rather than an empty string.
    assert loaded.loc[0, ["welfare_proxy_label", "source", "notes"]].isna().all()
    assert loaded.loc[1, "welfare_proxy_label"] == "Coverage"


def test_upload_pipeline_stores_unmapped_optional_text_as_null(user_db):
    from src.services.upload import normalize_mapped_upload, validate_country_upload

    raw = pd.DataFrame({"Year": [2019, 2021], "Gini": [0.42, 0.40]})
    normalized = normalize_mapped_upload(
        raw,
        country_mode="Use fixed country name",
        country_column=None,
        fixed_country="Kenya",
        mapping={"year": "Year", "gini": "Gini"},
    )

    assert validate_country_upload(normalized) == []

    save_user_country_data(user_db, "user_country_indicators", normalized)
    loaded = load_user_country_data(user_db, "user_country_indicators")

    assert loaded["country"].tolist() == ["Kenya", "Kenya"]
    assert loaded[["welfare_proxy_label", "source", "notes"]].isna().all().all()


def test_save_user_country_data_replaces_duplicate_country_year(user_db):
    first = pd.DataFrame(
        [
            {
                "country": "Kenya",
                "year": 2021,
                "gini": 0.40,
                "p90_p10": None,
                "s80_s20": None,
                "welfare_proxy_value": None,
                "welfare_proxy_label": "",
                "source": "",
                "notes": "",
            }
        ]
    )
    second = first.assign(gini=0.33)

    save_user_country_data(user_db, "user_country_indicators", first)
    save_user_country_data(user_db, "user_country_indicators", second)
    loaded = load_user_country_data(user_db, "user_country_indicators")

    assert len(loaded) == 1
    assert loaded.loc[0, "gini"] == pytest.approx(0.33)
