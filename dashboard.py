import sqlite3
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "database.db"
REQUIRED_TABLES = {
    "norway_inequality_indicators_clean",
    "usa_clean",
    "philippines_clean",
    "norway_public_services",
}


def choose_latest_not_after(df, year):
    filtered = df[df["year"] <= year]
    if filtered.empty:
        return None
    return filtered.iloc[-1]


def get_missing_tables(db_path):
    if not db_path.exists():
        return sorted(REQUIRED_TABLES)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    existing_tables = {row[0] for row in rows}
    return sorted(REQUIRED_TABLES - existing_tables)


def run_python_script(script_path):
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to run {script_path.name}.\n\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )


def ensure_database_ready():
    missing_tables = get_missing_tables(DB_PATH)
    if not missing_tables:
        return

    run_python_script(BASE_DIR / "setup_database.py")
    run_python_script(BASE_DIR / "scripts" / "clean_data.py")

    missing_after = get_missing_tables(DB_PATH)
    if missing_after:
        raise RuntimeError(
            "Database bootstrap finished but required tables are still missing: "
            + ", ".join(missing_after)
        )


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


def pick_usa_value(usa_df, measure, year):
    row = usa_df[
        (usa_df["income_type"] == "MONEY INCOME")
        & (usa_df["measure"] == measure)
    ]
    if row.empty:
        return None, None

    row = row.iloc[0]
    if year >= 2024 and pd.notna(row["year_2024_estimate"]):
        return float(row["year_2024_estimate"]), 2024
    if pd.notna(row["year_2023_estimate"]):
        return float(row["year_2023_estimate"]), 2023
    return None, None


def pick_ph_gini(ph_row, year):
    series = [
        (2009, ph_row["gini_2009"]),
        (2012, ph_row["gini_2012"]),
        (2015, ph_row["gini_2015"]),
        (2018, ph_row["gini_2018"]),
        (2021, ph_row["gini_2021"]),
        (2023, ph_row["gini_2023"]),
    ]
    available = [(y, float(v)) for y, v in series if pd.notna(v) and y <= year]
    if not available:
        return None, None
    return available[-1][1], available[-1][0]


def build_usa_gini_series(usa_df):
    row = usa_df[
        (usa_df["income_type"] == "MONEY INCOME")
        & (usa_df["measure"] == "Gini index of income inequality")
    ]
    if row.empty:
        return pd.DataFrame(columns=["country", "year", "gini"])

    row = row.iloc[0]
    records = []
    if pd.notna(row["year_2023_estimate"]):
        records.append({"country": "USA", "year": 2023, "gini": float(row["year_2023_estimate"])})
    if pd.notna(row["year_2024_estimate"]):
        records.append({"country": "USA", "year": 2024, "gini": float(row["year_2024_estimate"] )})
    return pd.DataFrame(records)


def build_ph_gini_series(ph_row):
    return pd.DataFrame(
        [
            {"country": "Philippines", "year": 2009, "gini": ph_row["gini_2009"]},
            {"country": "Philippines", "year": 2012, "gini": ph_row["gini_2012"]},
            {"country": "Philippines", "year": 2015, "gini": ph_row["gini_2015"]},
            {"country": "Philippines", "year": 2018, "gini": ph_row["gini_2018"]},
            {"country": "Philippines", "year": 2021, "gini": ph_row["gini_2021"]},
            {"country": "Philippines", "year": 2023, "gini": ph_row["gini_2023"]},
        ]
    ).dropna(subset=["gini"])


def get_norway_welfare_total(conn):
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


def get_usa_lowest_quintile_share(conn):
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


def get_ph_gini_improvement(ph_row):
    if pd.isna(ph_row["gini_2009"]) or pd.isna(ph_row["gini_2023"]):
        return None
    return float(ph_row["gini_2009"] - ph_row["gini_2023"])


@st.cache_data
def load_data(db_path_str):
    db_path = Path(db_path_str)
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


def main():
    st.set_page_config(page_title="Inequality & Welfare Dashboard", layout="wide")
    st.title("Inequality & Welfare Dashboard")
    st.caption("Norway, USA, and Philippines comparison using cleaned project data")

    try:
        with st.spinner("Preparing database (first run on cloud may take up to a minute)..."):
            ensure_database_ready()
        (
            norway_df,
            usa_df,
            ph_row,
            norway_welfare_total,
            usa_lowest_quintile_share,
        ) = load_data(str(DB_PATH))
    except Exception as exc:
        st.error("Unable to initialize dashboard data.")
        st.exception(exc)
        st.stop()

    norway_series = norway_df[["year", "gini_all_population", "gini_excl_student_households"]].copy()
    usa_series = build_usa_gini_series(usa_df)
    ph_series = build_ph_gini_series(ph_row)

    min_year = int(min(norway_df["year"].min(), 2009))
    max_year = int(max(norway_df["year"].max(), 2024))

    st.sidebar.header("Controls")
    selected_countries = st.sidebar.multiselect(
        "Countries",
        ["Norway", "USA", "Philippines"],
        default=["Norway", "USA", "Philippines"],
    )
    year_start, year_end = st.sidebar.slider(
        "Year range",
        min_year,
        max_year,
        (min_year, max_year),
    )
    gini_min, gini_max = st.sidebar.slider(
        "Gini range",
        0.15,
        0.60,
        (0.20, 0.50),
        step=0.01,
    )
    selected_year = st.sidebar.slider("Reference year", min_year, max_year, max_year)
    population = st.sidebar.selectbox(
        "Norway population definition",
        ["All population", "Excl. student households"],
    )

    if population == "All population":
        norway_gini_col = "gini_all_population"
        norway_p90_col = "p90_p10_all_population"
        norway_s80_col = "s80_s20_all_population"
    else:
        norway_gini_col = "gini_excl_student_households"
        norway_p90_col = "p90_p10_excl_student_households"
        norway_s80_col = "s80_s20_excl_student_households"

    norway_country_series = norway_series[["year", norway_gini_col]].rename(columns={norway_gini_col: "gini"})
    norway_country_series["country"] = "Norway"

    trends = pd.concat(
        [
            norway_country_series[["country", "year", "gini"]],
            usa_series[["country", "year", "gini"]],
            ph_series[["country", "year", "gini"]],
        ],
        ignore_index=True,
    )

    filtered_trends = trends[
        (trends["country"].isin(selected_countries))
        & (trends["year"].between(year_start, year_end))
        & (trends["gini"].between(gini_min, gini_max))
    ].copy()

    norway_latest = choose_latest_not_after(norway_df, selected_year)
    if norway_latest is None:
        raise ValueError("No Norway rows available for selected year.")

    norway_gini = float(norway_latest[norway_gini_col])
    norway_p90 = float(norway_latest[norway_p90_col])
    norway_s80 = float(norway_latest[norway_s80_col])
    norway_year = int(norway_latest["year"])

    usa_gini, usa_gini_year = pick_usa_value(usa_df, "Gini index of income inequality", selected_year)
    usa_p90, usa_p90_year = pick_usa_value(usa_df, "90th/10th percentile income ratio", selected_year)
    ph_gini, ph_gini_year = pick_ph_gini(ph_row, selected_year)

    k1, k2, k3 = st.columns(3)
    k1.metric("Norway Gini", f"{norway_gini:.3f}", help=f"Year {norway_year}")
    k2.metric("USA Gini", f"{usa_gini:.3f}" if usa_gini is not None else "n/a", help=f"Year {usa_gini_year}")
    k3.metric("Philippines Gini", f"{ph_gini:.3f}" if ph_gini is not None else "n/a", help=f"Year {ph_gini_year}")

    k4, k5, k6 = st.columns(3)
    k4.metric("Norway P90/P10", f"{norway_p90:.2f}", help=f"Year {norway_year}")
    k5.metric("USA 90th/10th", f"{usa_p90:.2f}" if usa_p90 is not None else "n/a", help=f"Year {usa_p90_year}")
    k6.metric("Norway S80/S20", f"{norway_s80:.2f}", help=f"Year {norway_year}")

    gini_for_rank = [
        ("Norway", norway_gini),
        ("USA", usa_gini if usa_gini is not None else float("nan")),
        ("Philippines", ph_gini if ph_gini is not None else float("nan")),
    ]
    valid_rank = [(c, v) for c, v in gini_for_rank if pd.notna(v)]
    valid_rank.sort(key=lambda x: x[1], reverse=True)
    st.info(
        "Latest Gini ranking (higher = more inequality): "
        + " > ".join([f"{country} ({value:.3f})" for country, value in valid_rank])
    )

    st.subheader("Gini trends over time")
    if filtered_trends.empty:
        st.warning("No data points match the selected country/year/Gini filters.")
    else:
        st.line_chart(filtered_trends.pivot_table(index="year", columns="country", values="gini", aggfunc="mean"))

    left, right = st.columns(2)
    with left:
        st.subheader("Country comparison (selected reference year)")
        gini_df = pd.DataFrame([
            {"Country": "Norway", "Gini": norway_gini, "Year used": norway_year},
            {"Country": "USA", "Gini": usa_gini, "Year used": usa_gini_year},
            {"Country": "Philippines", "Gini": ph_gini, "Year used": ph_gini_year},
        ])
        gini_df = gini_df[gini_df["Country"].isin(selected_countries)].dropna(subset=["Gini"])
        if gini_df.empty:
            st.warning("No country comparison data for current filters.")
        else:
            st.bar_chart(gini_df.set_index("Country")["Gini"])
            st.dataframe(gini_df, hide_index=True, use_container_width=True)

    with right:
        st.subheader("Welfare context vs inequality scatter")
        ph_gini_improvement = get_ph_gini_improvement(ph_row)
        welfare_df = pd.DataFrame(
            [
                {
                    "Country": "Norway",
                    "Inequality (Gini)": norway_gini,
                    "Welfare proxy": norway_welfare_total,
                    "Proxy": "Public services total (Barnehage+Utdanning+Pleie/Helse)",
                },
                {
                    "Country": "USA",
                    "Inequality (Gini)": usa_gini,
                    "Welfare proxy": usa_lowest_quintile_share,
                    "Proxy": "Lowest quintile income share",
                },
                {
                    "Country": "Philippines",
                    "Inequality (Gini)": ph_gini,
                    "Welfare proxy": ph_gini_improvement,
                    "Proxy": "National Gini improvement since 2009",
                },
            ]
        )
        welfare_df = welfare_df[
            welfare_df["Country"].isin(selected_countries)
        ].dropna(subset=["Inequality (Gini)", "Welfare proxy"])

        if welfare_df.empty:
            st.warning("No welfare context data available for selected countries.")
        else:
            st.scatter_chart(welfare_df.set_index("Country")[["Welfare proxy", "Inequality (Gini)"]])
            st.dataframe(welfare_df, hide_index=True, use_container_width=True)

    st.subheader("Norway inequality indicators")
    norway_indicator_df = norway_df[norway_df["year"] <= selected_year][
        ["year", norway_gini_col, norway_p90_col, norway_s80_col]
    ].rename(
        columns={
            norway_gini_col: "Gini",
            norway_p90_col: "P90/P10",
            norway_s80_col: "S80/S20",
        }
    )
    st.line_chart(norway_indicator_df.set_index("year"))

    st.caption(
        "Note: Welfare scatter uses available country-specific welfare proxies from SQLite tables; "
        "units differ by country and are intended for exploratory context rather than strict like-for-like spending comparison."
    )


if __name__ == "__main__":
    main()
