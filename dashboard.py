import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "database.db"


def choose_latest_not_after(df, year):
    filtered = df[df["year"] <= year]
    if filtered.empty:
        return None
    return filtered.iloc[-1]


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

    if norway.empty:
        raise ValueError("Table norway_inequality_indicators_clean is empty.")
    if usa.empty:
        raise ValueError("Table usa_clean is empty.")
    if ph.empty:
        raise ValueError("National row not found in philippines_clean.")

    return norway, usa, ph.iloc[0]


def main():
    st.set_page_config(page_title="Inequality & Welfare Dashboard", layout="wide")
    st.title("Inequality & Welfare Dashboard")
    st.caption("Norway, USA, and Philippines comparison using cleaned project data")

    norway_df, usa_df, ph_row = load_data(str(DB_PATH))

    min_year = int(norway_df["year"].min())
    max_year = int(norway_df["year"].max())

    st.sidebar.header("Controls")
    selected_year = st.sidebar.slider("Reference year", min_year, max_year, max_year)
    population = st.sidebar.selectbox(
        "Norway population definition",
        ["All population", "Excl. student households"],
    )
    trend_mode = st.sidebar.selectbox(
        "Norway trend view",
        ["All indicators", "Gini", "P90/P10", "S80/S20"],
    )

    if population == "All population":
        norway_gini_col = "gini_all_population"
        norway_p90_col = "p90_p10_all_population"
        norway_s80_col = "s80_s20_all_population"
    else:
        norway_gini_col = "gini_excl_student_households"
        norway_p90_col = "p90_p10_excl_student_households"
        norway_s80_col = "s80_s20_excl_student_households"

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

    st.subheader("Norway trend panel")
    trend_df = norway_df[norway_df["year"] <= selected_year].copy()
    trend_columns = {
        "Gini": norway_gini_col,
        "P90/P10": norway_p90_col,
        "S80/S20": norway_s80_col,
    }
    if trend_mode == "All indicators":
        plot_df = trend_df[["year", norway_gini_col, norway_p90_col, norway_s80_col]].rename(
            columns={
                norway_gini_col: "Gini",
                norway_p90_col: "P90/P10",
                norway_s80_col: "S80/S20",
            }
        )
    else:
        col = trend_columns[trend_mode]
        plot_df = trend_df[["year", col]].rename(columns={col: trend_mode})
    st.line_chart(plot_df.set_index("year"))

    left, right = st.columns(2)
    with left:
        st.subheader("Gini comparison (USA, Norway, Philippines)")
        gini_df = pd.DataFrame(
            [
                {"Country": "Norway", "Gini": norway_gini, "Year used": norway_year},
                {"Country": "USA", "Gini": usa_gini, "Year used": usa_gini_year},
                {"Country": "Philippines", "Gini": ph_gini, "Year used": ph_gini_year},
            ]
        )
        st.bar_chart(gini_df.set_index("Country")["Gini"])
        st.dataframe(gini_df, hide_index=True, use_container_width=True)

    with right:
        st.subheader("USA vs Norway decile ratio comparison")
        p90_df = pd.DataFrame(
            [
                {"Country": "Norway", "P90/P10": norway_p90, "Year used": norway_year},
                {"Country": "USA", "P90/P10": usa_p90, "Year used": usa_p90_year},
            ]
        )
        st.bar_chart(p90_df.set_index("Country")["P90/P10"])
        st.dataframe(p90_df, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
