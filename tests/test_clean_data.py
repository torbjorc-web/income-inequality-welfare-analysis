import sqlite3

import pytest

from scripts import clean_data


USA_CSV = """Report title;;;;;;
Measure;2023;;2024;;Change;
;Estimate;MOE;Estimate;MOE;Estimate;MOE
MONEY INCOME;;;;;;
Income Dispersion;;;;;;
Gini index of income inequality;0,470;0,004;0,478;0,004;1,7;1,1
90th/10th percentile income ratio;12,60;0,20;12,90;0,20;2,4;1,9
Share of Aggregate Income by Percentile;;;;;;
Lowest quintile;3,0;0,1;3,1;0,1;3,3;4,0
Note:;This line is skipped;;;;;
*An asterisk footnote stops parsing;;;;;;
Highest quintile;51,6;0,4;52,1;0,4;1,0;1,0
"""

PH_CSV = """Table 1 Gini coefficients,,,,,,
Region,2009,2012,2015,2018,2021,2023
Philippines,0.4641,0.4605,0.4438,0.4267,0.4063,0.3909
NCR,0.4008,0.3979,0.3894,0.3703,0.3562,0.3459
BARMM,,,,,0.3114,0.3031
,,,,,,
Note: PSA,,,,,,
Region X,0.5,0.5,0.5,0.5,0.5,0.5
"""

NORWAY_CSV = """Aar;Gini;Dummy;P90/P10;S80/S20;Gini eks;Dummy;P90/P10 eks;S80/S20 eks
Hele befolkningen;;;;;;;;
2020;0,250;;2,90;3,50;0,240;;2,70;3,30
2021;0,262;;3,05;3,70;0,252;;2,85;3,50
2022;0,255;;3,00;3,60;0,245;;2,80;3,40
1800;0,999;;9,90;9,90;0,999;;9,90;9,90
2023;;;;;;;;
"""


@pytest.fixture
def raw_sources(tmp_path, monkeypatch):
    usa = tmp_path / "usa.csv"
    ph = tmp_path / "ph.csv"
    norway = tmp_path / "norway.csv"
    usa.write_text(USA_CSV, encoding="utf-8")
    ph.write_text(PH_CSV, encoding="utf-8")
    norway.write_text(NORWAY_CSV, encoding="utf-8")

    monkeypatch.setattr(clean_data, "USA_RAW_PATH", usa)
    monkeypatch.setattr(clean_data, "PH_RAW_PATH", ph)
    monkeypatch.setattr(clean_data, "NORWAY_RAW_PATH", norway)
    monkeypatch.setattr(clean_data, "PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr(clean_data, "DB_PATH", tmp_path / "database.db")
    return tmp_path


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("0,470", 0.470),
        ("1 234", 1234.0),
        ("12*", 12.0),
        ("47%", 47.0),
        ("-1,5", -1.5),
        ("Z", None),
        ("z", None),
        ("...", None),
        ("-", None),
        ("?", None),
        ("nan", None),
        ("", None),
        (None, None),
        ("abc", None),
    ],
)
def test_parse_number(raw, expected):
    assert clean_data.parse_number(raw) == expected


def test_read_csv_flexible_raises_for_a_missing_file(tmp_path):
    with pytest.raises(RuntimeError, match="Unable to read CSV file"):
        clean_data.read_csv_flexible(tmp_path / "nope.csv", sep=",")


def test_clean_usa_dataset_carries_section_context_onto_each_row(raw_sources):
    df = clean_data.clean_usa_dataset()

    assert df["income_type"].unique().tolist() == ["MONEY INCOME"]
    assert df["measure"].tolist() == [
        "Gini index of income inequality",
        "90th/10th percentile income ratio",
        "Lowest quintile",
    ]
    assert df.loc[0, "group_name"] == "Income Dispersion"
    assert df.loc[2, "group_name"] == "Share of Aggregate Income by Percentile"


def test_clean_usa_dataset_parses_comma_decimals_into_floats(raw_sources):
    row = clean_data.clean_usa_dataset().iloc[0]

    assert row["year_2023_estimate"] == pytest.approx(0.470)
    assert row["year_2024_estimate"] == pytest.approx(0.478)
    assert row["pct_change_estimate"] == pytest.approx(1.7)


def test_clean_usa_dataset_stops_at_the_footnote_block(raw_sources):
    # "Highest quintile" sits after the asterisk footnote and must not be parsed.
    assert "Highest quintile" not in clean_data.clean_usa_dataset()["measure"].tolist()


def test_clean_usa_dataset_requires_a_measure_header(tmp_path, monkeypatch):
    broken = tmp_path / "broken.csv"
    broken.write_text("a;b;c;d;e;f;g\n1;2;3;4;5;6;7\n", encoding="utf-8")
    monkeypatch.setattr(clean_data, "USA_RAW_PATH", broken)

    with pytest.raises(ValueError, match="Could not find 'Measure' header row"):
        clean_data.clean_usa_dataset()


def test_clean_philippines_dataset_shape_and_missing_values(raw_sources):
    df = clean_data.clean_philippines_dataset()

    assert df["region"].tolist() == ["Philippines", "NCR", "BARMM"]
    assert list(df.columns) == [
        "region",
        "gini_2009",
        "gini_2012",
        "gini_2015",
        "gini_2018",
        "gini_2021",
        "gini_2023",
    ]
    assert df.loc[0, "gini_2023"] == pytest.approx(0.3909)
    assert df.loc[2, ["gini_2009", "gini_2012", "gini_2015", "gini_2018"]].isna().all()
    assert df.loc[2, "gini_2021"] == pytest.approx(0.3114)


def test_clean_philippines_dataset_stops_at_the_note_line(raw_sources):
    assert "Region X" not in clean_data.clean_philippines_dataset()["region"].tolist()


def test_clean_philippines_dataset_requires_a_region_header(tmp_path, monkeypatch):
    broken = tmp_path / "broken.csv"
    broken.write_text("a,b\n1,2\n", encoding="utf-8")
    monkeypatch.setattr(clean_data, "PH_RAW_PATH", broken)

    with pytest.raises(ValueError, match="Could not find 'Region' header row"):
        clean_data.clean_philippines_dataset()


def test_clean_norway_p90_p10_keeps_only_plausible_years(raw_sources):
    df = clean_data.clean_norway_p90_p10_dataset()

    assert df["year"].tolist() == [2020, 2021, 2022]
    assert df.loc[0, "p90_p10_all_population"] == pytest.approx(2.90)
    assert df.loc[0, "p90_p10_excl_student_households"] == pytest.approx(2.70)


def test_clean_norway_indicators_extracts_all_six_measures(raw_sources):
    df = clean_data.clean_norway_inequality_indicators_dataset()

    assert df["year"].tolist() == [2020, 2021, 2022]
    assert df.loc[1, "gini_all_population"] == pytest.approx(0.262)
    assert df.loc[1, "s80_s20_all_population"] == pytest.approx(3.70)
    assert df.loc[1, "gini_excl_student_households"] == pytest.approx(0.252)
    assert df.loc[1, "s80_s20_excl_student_households"] == pytest.approx(3.50)


def test_clean_norway_indicators_returns_typed_empty_frame_when_nothing_parses(tmp_path, monkeypatch):
    empty = tmp_path / "empty.csv"
    empty.write_text("header;only\n;\n", encoding="utf-8")
    monkeypatch.setattr(clean_data, "NORWAY_RAW_PATH", empty)

    df = clean_data.clean_norway_inequality_indicators_dataset()

    assert df.empty
    assert list(df.columns) == [
        "year",
        "gini_all_population",
        "p90_p10_all_population",
        "s80_s20_all_population",
        "gini_excl_student_households",
        "p90_p10_excl_student_households",
        "s80_s20_excl_student_households",
    ]


def test_main_writes_processed_csvs_and_database_tables(raw_sources, capsys):
    (raw_sources / "database.db").touch()

    clean_data.main()

    processed = raw_sources / "processed"
    assert {p.name for p in processed.glob("*.csv")} == {
        "usa_income_distribution_clean.csv",
        "philippines_gini_clean.csv",
        "norway_p90_p10_clean.csv",
        "norway_inequality_indicators_clean.csv",
    }

    with sqlite3.connect(raw_sources / "database.db") as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {
        "usa_clean",
        "philippines_clean",
        "norway_p90_p10_clean",
        "norway_inequality_indicators_clean",
    }
    assert "Clean USA rows: 3" in capsys.readouterr().out


def test_main_requires_an_existing_database(raw_sources):
    with pytest.raises(FileNotFoundError, match="Database not found"):
        clean_data.main()


def test_main_requires_every_raw_source(raw_sources, monkeypatch):
    monkeypatch.setattr(clean_data, "PH_RAW_PATH", raw_sources / "missing.csv")

    with pytest.raises(FileNotFoundError, match="Philippines source file not found"):
        clean_data.main()
