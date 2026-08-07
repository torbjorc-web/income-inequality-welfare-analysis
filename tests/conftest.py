import sqlite3

import pandas as pd
import pytest

_NORWAY_YEARS = list(range(2015, 2025))

NORWAY_INDICATOR_ROWS = pd.DataFrame(
    {
        "year": _NORWAY_YEARS,
        "gini_all_population": [0.240, 0.242, 0.244, 0.246, 0.248, 0.250, 0.262, 0.255, 0.253, 0.251],
        "p90_p10_all_population": [2.80, 2.82, 2.84, 2.86, 2.88, 2.90, 3.05, 3.00, 2.98, 2.95],
        "s80_s20_all_population": [3.40, 3.42, 3.44, 3.46, 3.48, 3.50, 3.70, 3.60, 3.58, 3.55],
        "gini_excl_student_households": [
            0.230, 0.232, 0.234, 0.236, 0.238, 0.240, 0.252, 0.245, 0.243, 0.241
        ],
        "p90_p10_excl_student_households": [
            2.60, 2.62, 2.64, 2.66, 2.68, 2.70, 2.85, 2.80, 2.78, 2.75
        ],
        "s80_s20_excl_student_households": [
            3.20, 3.22, 3.24, 3.26, 3.28, 3.30, 3.50, 3.40, 3.38, 3.35
        ],
    }
)

USA_CLEAN_ROWS = pd.DataFrame(
    [
        {
            "income_type": "MONEY INCOME",
            "group_name": "Income Dispersion",
            "measure": "Gini index of income inequality",
            "year_2023_estimate": 0.470,
            "year_2023_moe": 0.004,
            "year_2024_estimate": 0.478,
            "year_2024_moe": 0.004,
            "pct_change_estimate": 1.7,
            "pct_change_moe": 1.1,
        },
        {
            "income_type": "MONEY INCOME",
            "group_name": "Income Dispersion",
            "measure": "90th/10th percentile income ratio",
            "year_2023_estimate": 12.60,
            "year_2023_moe": 0.20,
            "year_2024_estimate": 12.90,
            "year_2024_moe": 0.20,
            "pct_change_estimate": 2.4,
            "pct_change_moe": 1.9,
        },
        {
            "income_type": "MONEY INCOME",
            "group_name": "Share of Aggregate Income by Percentile",
            "measure": "Lowest quintile",
            "year_2023_estimate": 3.0,
            "year_2023_moe": 0.1,
            "year_2024_estimate": 3.1,
            "year_2024_moe": 0.1,
            "pct_change_estimate": 3.3,
            "pct_change_moe": 4.0,
        },
        {
            "income_type": "MONEY INCOME",
            "group_name": "Share of Aggregate Income by Percentile",
            "measure": "Highest quintile",
            "year_2023_estimate": 51.6,
            "year_2023_moe": 0.4,
            "year_2024_estimate": 52.1,
            "year_2024_moe": 0.4,
            "pct_change_estimate": 1.0,
            "pct_change_moe": 1.0,
        },
    ]
)

PHILIPPINES_CLEAN_ROWS = pd.DataFrame(
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
            "region": "NCR",
            "gini_2009": 0.4008,
            "gini_2012": 0.3979,
            "gini_2015": 0.3894,
            "gini_2018": 0.3703,
            "gini_2021": 0.3562,
            "gini_2023": 0.3459,
        },
        {
            "region": "BARMM",
            "gini_2009": None,
            "gini_2012": None,
            "gini_2015": None,
            "gini_2018": None,
            "gini_2021": 0.3114,
            "gini_2023": 0.3031,
        },
    ]
)

NORWAY_PUBLIC_SERVICES_ROWS = pd.DataFrame(
    [
        {
            "Land": "Norge",
            "Barnehage": "1,5",
            "Utdanning": "3,0",
            "Pleie og omsorg": "2,5",
            "Helse": "4,0",
        },
        {
            "Land": "Sverige",
            "Barnehage": "1,2",
            "Utdanning": "2,8",
            "Pleie og omsorg": "2,2",
            "Helse": "3,6",
        },
    ]
)


@pytest.fixture
def db_path(tmp_path):
    """Path to a database file inside a temp dir. The file does not exist yet."""
    return tmp_path / "database" / "database.db"


@pytest.fixture
def populated_db(db_path):
    """A temp SQLite database with the four tables the dashboard requires."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        NORWAY_INDICATOR_ROWS.to_sql(
            "norway_inequality_indicators_clean", conn, index=False, if_exists="replace"
        )
        USA_CLEAN_ROWS.to_sql("usa_clean", conn, index=False, if_exists="replace")
        PHILIPPINES_CLEAN_ROWS.to_sql("philippines_clean", conn, index=False, if_exists="replace")
        NORWAY_PUBLIC_SERVICES_ROWS.to_sql(
            "norway_public_services", conn, index=False, if_exists="replace"
        )
        conn.commit()
    return db_path


@pytest.fixture
def usa_df():
    return USA_CLEAN_ROWS.copy()


@pytest.fixture
def ph_row():
    return PHILIPPINES_CLEAN_ROWS.iloc[0].copy()


@pytest.fixture
def norway_df():
    return NORWAY_INDICATOR_ROWS.copy()
