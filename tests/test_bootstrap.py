import sqlite3

import pytest

from src.data.bootstrap import (
    ensure_database_ready,
    ensure_user_country_table,
    get_missing_tables,
    run_python_script,
)

REQUIRED = {"norway_inequality_indicators_clean", "usa_clean", "philippines_clean", "norway_public_services"}


def table_names(db_path):
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows}


def test_missing_tables_lists_everything_when_the_database_does_not_exist(db_path):
    assert get_missing_tables(db_path, REQUIRED) == sorted(REQUIRED)


def test_missing_tables_is_empty_for_a_fully_populated_database(populated_db):
    assert get_missing_tables(populated_db, REQUIRED) == []


def test_missing_tables_reports_only_what_is_absent(populated_db):
    with sqlite3.connect(populated_db) as conn:
        conn.execute("DROP TABLE usa_clean")
        conn.commit()

    assert get_missing_tables(populated_db, REQUIRED) == ["usa_clean"]


def test_run_python_script_raises_with_captured_output(tmp_path):
    script = tmp_path / "boom.py"
    script.write_text("import sys\nprint('out')\nsys.exit(3)\n")

    with pytest.raises(RuntimeError, match="Failed to run boom.py"):
        run_python_script(tmp_path, script)


def test_run_python_script_succeeds_for_a_healthy_script(tmp_path):
    script = tmp_path / "ok.py"
    script.write_text("print('fine')\n")

    run_python_script(tmp_path, script)


def test_ensure_database_ready_is_a_no_op_when_tables_exist(populated_db, monkeypatch):
    monkeypatch.setattr(
        "src.data.bootstrap.run_python_script",
        lambda *args: pytest.fail("bootstrap scripts must not run when the schema is complete"),
    )

    ensure_database_ready(populated_db.parent.parent, populated_db, REQUIRED)


def test_ensure_database_ready_runs_setup_scripts_when_tables_are_missing(db_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "src.data.bootstrap.run_python_script",
        lambda base_dir, script_path: calls.append(script_path.name),
    )

    with pytest.raises(RuntimeError, match="required tables are still missing"):
        ensure_database_ready(db_path.parent, db_path, REQUIRED)

    assert calls == ["setup_database.py", "clean_data.py"]


def test_ensure_user_country_table_creates_the_expected_schema(populated_db):
    ensure_user_country_table(populated_db, "user_country_indicators")

    with sqlite3.connect(populated_db) as conn:
        columns = {row[1]: row for row in conn.execute("PRAGMA table_info(user_country_indicators)")}

    assert set(columns) == {
        "country",
        "year",
        "gini",
        "p90_p10",
        "s80_s20",
        "welfare_proxy_value",
        "welfare_proxy_label",
        "source",
        "notes",
        "created_at",
    }
    # country + year form the composite primary key.
    assert columns["country"][5] == 1
    assert columns["year"][5] == 2
    assert columns["gini"][3] == 1


def test_ensure_user_country_table_creates_the_database_file_if_needed(db_path):
    db_path.parent.mkdir(parents=True)

    ensure_user_country_table(db_path, "user_country_indicators")

    assert db_path.exists()
    assert "user_country_indicators" in table_names(db_path)


def test_ensure_user_country_table_is_idempotent_and_preserves_rows(populated_db):
    ensure_user_country_table(populated_db, "user_country_indicators")
    with sqlite3.connect(populated_db) as conn:
        conn.execute(
            "INSERT INTO user_country_indicators (country, year, gini) VALUES ('Kenya', 2021, 0.4)"
        )
        conn.commit()

    ensure_user_country_table(populated_db, "user_country_indicators")

    with sqlite3.connect(populated_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM user_country_indicators").fetchone()[0] == 1
