import sqlite3

import pandas as pd
import pytest

import setup_database


@pytest.fixture
def raw_dir(tmp_path, monkeypatch):
    """Redirect setup_database at a temp raw folder and temp SQLite file."""
    raw = tmp_path / "raw"
    raw.mkdir()
    db = tmp_path / "database.db"
    monkeypatch.setattr(setup_database, "RAW_DIR", raw)
    monkeypatch.setattr(setup_database, "DB_PATH", db)
    return raw


def test_clean_columns_trims_and_flattens_header_text():
    df = pd.DataFrame(columns=["  Land ", "Pleie\nog omsorg", "A  B"])

    cleaned = setup_database.clean_columns(df)

    assert list(cleaned.columns) == ["Land", "Pleie og omsorg", "A B"]


def test_clean_columns_does_not_mutate_the_input():
    df = pd.DataFrame(columns=[" Land "])

    setup_database.clean_columns(df)

    assert list(df.columns) == [" Land "]


@pytest.mark.parametrize(
    "content,expected",
    [
        ("a;b;c\n1;2;3\n", ";"),
        ("a,b,c\n1,2,3\n", ","),
        ("a\n1\n", ";"),
    ],
)
def test_detect_delimiter(tmp_path, content, expected):
    path = tmp_path / "sample.csv"
    path.write_text(content, encoding="utf-8")

    assert setup_database.detect_delimiter(path, "utf-8") == expected


def test_detect_delimiter_ignores_blank_lines(tmp_path):
    path = tmp_path / "sample.csv"
    path.write_text("\n\na,b\n\n1,2\n", encoding="utf-8")

    assert setup_database.detect_delimiter(path, "utf-8") == ","


def test_load_csv_reads_semicolon_files(tmp_path):
    path = tmp_path / "semi.csv"
    path.write_text("year;gini\n2020;0,25\n", encoding="utf-8")

    df = setup_database.load_csv(path)

    assert list(df.columns) == ["year", "gini"]
    assert df.iloc[0]["year"] == 2020


def test_load_csv_reads_comma_files_with_latin1_bytes(tmp_path):
    path = tmp_path / "latin.csv"
    path.write_bytes("region,gini\nSør,0.42\n".encode("latin1"))

    df = setup_database.load_csv(path)

    assert list(df.columns) == ["region", "gini"]
    assert len(df) == 1


def test_main_loads_configured_csvs_into_tables(raw_dir, monkeypatch, capsys):
    target = raw_dir / "norway.csv"
    target.write_text("Land;Barnehage\nNorge;1,5\n", encoding="utf-8")
    monkeypatch.setattr(setup_database, "CSV_TABLES", [("norway_public_services", target)])

    setup_database.main()

    with sqlite3.connect(setup_database.DB_PATH) as conn:
        rows = conn.execute("SELECT Land, Barnehage FROM norway_public_services").fetchall()
    assert rows == [("Norge", "1,5")]
    assert "OK: norway_public_services" in capsys.readouterr().out


def test_main_is_idempotent_and_replaces_existing_tables(raw_dir, monkeypatch):
    target = raw_dir / "norway.csv"
    target.write_text("Land;Barnehage\nNorge;1,5\n", encoding="utf-8")
    monkeypatch.setattr(setup_database, "CSV_TABLES", [("norway_public_services", target)])

    setup_database.main()
    setup_database.main()

    with sqlite3.connect(setup_database.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM norway_public_services").fetchone()[0] == 1


def test_main_skips_and_warns_about_missing_configured_files(raw_dir, monkeypatch, capsys):
    monkeypatch.setattr(setup_database, "CSV_TABLES", [("ghost", raw_dir / "ghost.csv")])

    setup_database.main()

    out = capsys.readouterr().out
    assert "not found in data/raw" in out
    assert "SKIP:" in out


def test_main_warns_about_unconfigured_files_present_on_disk(raw_dir, monkeypatch, capsys):
    (raw_dir / "extra.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    monkeypatch.setattr(setup_database, "CSV_TABLES", [])

    setup_database.main()

    assert "not listed in CSV_TABLES: ['extra.csv']" in capsys.readouterr().out
