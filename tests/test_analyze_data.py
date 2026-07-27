import sqlite3

import pandas as pd
import pytest

from scripts import analyze_data


@pytest.fixture
def analysis_db(populated_db):
    """Temp database extended with the raw tables analyze_data reads."""
    with sqlite3.connect(populated_db) as connection:
        pd.DataFrame(
            {
                "Unnamed: 0": ["Hele befolkningen", "2020", "2021", "2022", "1800"],
                "Hele befolkningen": ["", "0,250", "0,262", "0,255", "0,999"],
            }
        ).to_sql("norway", connection, index=False)
        pd.DataFrame(
            {
                "Alder": ["0-17", "18-66", "67+"],
                "SNA-skala": ["1,0", "2,0", "1,5"],
                "EU-skala": ["0,5", "2,0", "1,0"],
            }
        ).to_sql("norway_public_services_5", connection, index=False)
        connection.commit()
    return populated_db


@pytest.fixture
def conn(analysis_db):
    with sqlite3.connect(analysis_db) as connection:
        yield connection


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("0,470", 0.470),
        ("1 234", 1234.0),
        ("47%", 47.0),
        ("-1,5", -1.5),
        ("..", None),
        ("?", None),
        ("-", None),
        ("", None),
        (None, None),
        ("abc", None),
    ],
)
def test_parse_number(raw, expected):
    assert analyze_data.parse_number(raw) == expected


def test_get_tables_lists_user_tables_alphabetically(conn):
    tables = analyze_data.get_tables(conn)

    assert tables == sorted(tables)
    assert "usa_clean" in tables
    assert not any(name.startswith("sqlite_") for name in tables)


def test_table_helpers_report_shape_and_existence(conn):
    assert analyze_data.row_count(conn, "philippines_clean") == 3
    assert analyze_data.table_columns(conn, "philippines_clean")[0] == "region"
    assert analyze_data.table_exists(conn, "usa_clean")
    assert not analyze_data.table_exists(conn, "no_such_table")


def test_non_empty_count_ignores_nulls_and_blanks(conn):
    conn.execute("UPDATE philippines_clean SET region = '' WHERE region = 'NCR'")

    assert analyze_data.non_empty_count(conn, "philippines_clean", "region") == 2
    assert analyze_data.non_empty_count(conn, "philippines_clean", "gini_2009") == 2


def test_summarize_table_quality_profiles_the_first_five_columns(conn):
    lines = analyze_data.summarize_table_quality(conn, "philippines_clean")

    assert lines[0] == "- philippines_clean: 3 rows, 7 columns"
    assert len(lines) == 7
    assert lines[-1] == "  - ..."
    assert "  - region: 3/3 non-empty (100.0%)" in lines


def test_summarize_table_quality_short_circuits_on_empty_tables(conn):
    conn.execute("DELETE FROM philippines_clean")

    assert analyze_data.summarize_table_quality(conn, "philippines_clean") == [
        "- philippines_clean: 0 rows, 7 columns"
    ]


def test_analyze_norway_public_services_reports_totals_and_means(conn):
    lines = analyze_data.analyze_norway_public_services(conn)

    assert "- Parsed rows: 2" in lines
    assert "- Highest combined spending share: Norge (11.00)" in lines
    assert "- Lowest combined spending share: Sverige (9.80)" in lines
    assert "  - Barnehage: 1.35" in lines


def test_analyze_norway_public_services_handles_unparsable_rows(conn):
    conn.execute("UPDATE norway_public_services SET Helse = '..'")

    assert analyze_data.analyze_norway_public_services(conn)[1] == "- No fully parsable rows found."


def test_analyze_scale_table_reports_ratios_and_largest_gap(conn):
    lines = analyze_data.analyze_scale_table(conn)

    assert "- Parsed rows: 3" in lines
    assert "- Largest absolute gap: 0-17 (SNA=1.00, EU=0.50)" in lines
    assert "  - 18-66: 1.00" in lines


def test_analyze_scale_table_skips_zero_denominators(conn):
    conn.execute("UPDATE norway_public_services_5 SET \"EU-skala\" = '0'")

    assert analyze_data.analyze_scale_table(conn)[1] == "- No parsable rows found."


def test_analyze_norway_gini_trend_uses_first_and_last_plausible_year(conn):
    lines = analyze_data.analyze_norway_gini_trend(conn)

    assert "- Parsed points: 3" in lines
    assert "- First year: 2020 (Gini 0.250)" in lines
    assert "- Last year: 2022 (Gini 0.255)" in lines
    assert "- Change over period: +0.005" in lines


def test_analyze_usa_clean_trend_reports_2023_to_2024_deltas(conn):
    lines = analyze_data.analyze_usa_clean_trend(conn)

    assert lines[0] == "## USA cleaned trend"
    assert any("Gini index of income inequality: 0.470 -> 0.478 (+0.008)" in line for line in lines)
    assert any("Highest quintile: 51.600 -> 52.100" in line for line in lines)


def test_analyze_usa_clean_trend_handles_a_missing_table(conn):
    conn.execute("DROP TABLE usa_clean")

    assert "not found" in analyze_data.analyze_usa_clean_trend(conn)[1]


def test_analyze_philippines_clean_trend_reports_national_and_regional_extremes(conn):
    lines = analyze_data.analyze_philippines_clean_trend(conn)

    assert any("National Gini: 0.4641 (2009) -> 0.3909 (2023) (-0.0732)" in line for line in lines)
    assert "- Lowest regional Gini in 2023: BARMM (0.3031)" in lines
    assert "- Highest regional Gini in 2023: NCR (0.3459)" in lines


def test_analyze_philippines_clean_trend_handles_a_missing_national_row(conn):
    conn.execute("DELETE FROM philippines_clean WHERE region = 'Philippines'")

    assert "- National row ('Philippines') not found." in analyze_data.analyze_philippines_clean_trend(conn)


def test_three_country_comparison_ranks_countries_by_gini(conn):
    lines = analyze_data.analyze_three_country_comparison(conn)

    assert any("USA=0.4780 (2024)" in line for line in lines)
    assert any(
        "USA (0.4780) > Philippines (0.3909) > Norway (0.2550)" in line for line in lines
    )
    assert "- Gap USA - Norway: +0.2230" in lines
    assert "- Gap Philippines - Norway: +0.1359" in lines


def test_three_country_comparison_needs_at_least_two_countries(conn):
    conn.execute("DROP TABLE norway")
    conn.execute("DROP TABLE philippines_clean")

    lines = analyze_data.analyze_three_country_comparison(conn)

    assert lines[1] == "- Could not compute multi-country benchmark (missing values)."


def test_main_writes_a_summary_file(analysis_db, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(analyze_data, "DB_PATH", analysis_db)
    monkeypatch.setattr(analyze_data, "OUTPUT_DIR", tmp_path / "outputs")
    monkeypatch.setattr(analyze_data, "TABLES_DIR", tmp_path / "outputs" / "tables")
    monkeypatch.setattr(analyze_data, "SUMMARY_PATH", tmp_path / "outputs" / "tables" / "summary.txt")

    analyze_data.main()

    summary = (tmp_path / "outputs" / "tables" / "summary.txt").read_text(encoding="utf-8")
    assert "## Table quality profile" in summary
    assert "## Philippines cleaned trend" in summary
    assert "Saved summary to" in capsys.readouterr().out


def test_main_requires_an_existing_database(monkeypatch, tmp_path):
    monkeypatch.setattr(analyze_data, "DB_PATH", tmp_path / "missing.db")

    with pytest.raises(FileNotFoundError, match="Database not found"):
        analyze_data.main()
