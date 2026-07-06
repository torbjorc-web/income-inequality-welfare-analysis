import sqlite3
from pathlib import Path

import pandas as pd


def parse_number(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(" ", "").replace("%", "").replace(",", ".")
    cleaned = []
    for ch in text:
        if ch.isdigit() or ch in {".", "-"}:
            cleaned.append(ch)
        else:
            break
    if not cleaned:
        return None
    try:
        return float("".join(cleaned))
    except ValueError:
        return None


def get_norway_welfare_total(conn: sqlite3.Connection):
    row = conn.execute(
        """
        SELECT "Barnehage", "Utdanning", "Pleie og omsorg", "Helse"
        FROM "norway_public_services"
        WHERE TRIM("Land") IN ('Norge', 'Norway')
        LIMIT 1
        """
    ).fetchone()
    if not row:
        return None
    values = [parse_number(v) for v in row]
    if any(v is None for v in values):
        return None
    return sum(values)


def get_usa_lowest_quintile_share(conn: sqlite3.Connection):
    row = conn.execute(
        """
        SELECT year_2024_estimate
        FROM usa_clean
        WHERE income_type = 'MONEY INCOME'
          AND group_name = 'Share of Aggregate Income by Percentile'
          AND measure = 'Lowest quintile'
        LIMIT 1
        """
    ).fetchone()
    if not row:
        return None
    return float(row[0]) if row[0] is not None else None


def load_core_data(db_path: Path):
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    with sqlite3.connect(db_path) as conn:
        norway = pd.read_sql_query(
            "SELECT * FROM norway_inequality_indicators_clean ORDER BY year",
            conn,
        )
        usa = pd.read_sql_query("SELECT * FROM usa_clean", conn)
        ph = pd.read_sql_query(
            "SELECT * FROM philippines_clean WHERE region = 'Philippines' LIMIT 1",
            conn,
        )
        norway_welfare_total = get_norway_welfare_total(conn)
        usa_lowest_quintile_share = get_usa_lowest_quintile_share(conn)

    if norway.empty:
        raise ValueError("Table norway_inequality_indicators_clean is empty.")
    if usa.empty:
        raise ValueError("Table usa_clean is empty.")
    if ph.empty:
        raise ValueError("National row not found in philippines_clean.")

    return norway, usa, ph.iloc[0], norway_welfare_total, usa_lowest_quintile_share
