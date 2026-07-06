import sqlite3
import subprocess
import sys
from pathlib import Path


def get_missing_tables(db_path: Path, required_tables: set[str]) -> list[str]:
    if not db_path.exists():
        return sorted(required_tables)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    existing_tables = {row[0] for row in rows}
    return sorted(required_tables - existing_tables)


def run_python_script(base_dir: Path, script_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        cwd=str(base_dir),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to run {script_path.name}.\n\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )


def ensure_database_ready(base_dir: Path, db_path: Path, required_tables: set[str]) -> None:
    missing_tables = get_missing_tables(db_path, required_tables)
    if not missing_tables:
        return

    run_python_script(base_dir, base_dir / "setup_database.py")
    run_python_script(base_dir, base_dir / "scripts" / "clean_data.py")

    missing_after = get_missing_tables(db_path, required_tables)
    if missing_after:
        raise RuntimeError(
            "Database bootstrap finished but required tables are still missing: "
            + ", ".join(missing_after)
        )


def ensure_user_country_table(db_path: Path, table_name: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                country TEXT NOT NULL,
                year INTEGER NOT NULL,
                gini REAL NOT NULL,
                p90_p10 REAL,
                s80_s20 REAL,
                welfare_proxy_value REAL,
                welfare_proxy_label TEXT,
                source TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (country, year)
            )
            """
        )
        conn.commit()
