import pandas as pd
import streamlit as st

from src.config import BASE_DIR, CSV_TEMPLATE, DB_PATH, REQUIRED_TABLES, USER_COUNTRY_TABLE
from src.data.bootstrap import ensure_database_ready, ensure_user_country_table
from src.data.repository import load_core_data, load_user_country_data, save_user_country_data
from src.services.metrics import (
    build_ph_gini_series,
    build_usa_gini_series,
    choose_latest_not_after,
    get_ph_gini_improvement,
    pick_ph_gini,
    pick_usa_value,
)
from src.services.upload import normalize_mapped_upload, validate_country_upload


@st.cache_data
def load_data(_db_path: str):
    return load_core_data(DB_PATH)


@st.cache_data
def load_uploaded_data(_db_path: str):
    return load_user_country_data(DB_PATH, USER_COUNTRY_TABLE)


def main():
    st.set_page_config(page_title="Inequality & Welfare Dashboard", layout="wide")
    st.title("Inequality & Welfare Dashboard")
    st.caption("Norway, USA, and Philippines comparison using cleaned project data")

    try:
        with st.spinner("Preparing database (first run on cloud may take up to a minute)..."):
            ensure_database_ready(BASE_DIR, DB_PATH, REQUIRED_TABLES)
            ensure_user_country_table(DB_PATH, USER_COUNTRY_TABLE)
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

    with st.sidebar.expander("Add your own country data (CSV)"):
        st.download_button(
            "Download CSV template",
            data=CSV_TEMPLATE,
            file_name="country_upload_template.csv",
            mime="text/csv",
        )

        uploaded_file = st.file_uploader("Upload country CSV", type=["csv"], key="country_csv_upload")
        if uploaded_file is not None:
            try:
                uploaded_df = pd.read_csv(uploaded_file)
                st.write("Preview")
                st.dataframe(uploaded_df.head(5), width="stretch")

                columns = list(uploaded_df.columns)
                optional_choices = ["(none)"] + columns

                country_mode = st.radio("Country mapping", ["Use fixed country name", "Use column"])
                country_column = None
                fixed_country = ""
                if country_mode == "Use column":
                    country_column = st.selectbox("Country column", columns)
                else:
                    fixed_country = st.text_input("Country name", value="South Africa")

                year_col = st.selectbox("Year column", columns, key="map_year")
                gini_col = st.selectbox("Gini column", columns, key="map_gini")
                p90_col = st.selectbox("P90/P10 column (optional)", optional_choices, key="map_p90")
                s80_col = st.selectbox("S80/S20 column (optional)", optional_choices, key="map_s80")
                welfare_value_col = st.selectbox("Welfare proxy value column (optional)", optional_choices, key="map_wv")
                welfare_label_col = st.selectbox("Welfare proxy label column (optional)", optional_choices, key="map_wl")
                source_col = st.selectbox("Source column (optional)", optional_choices, key="map_src")
                notes_col = st.selectbox("Notes column (optional)", optional_choices, key="map_notes")

                mapping = {
                    "year": year_col,
                    "gini": gini_col,
                    "p90_p10": None if p90_col == "(none)" else p90_col,
                    "s80_s20": None if s80_col == "(none)" else s80_col,
                    "welfare_proxy_value": None if welfare_value_col == "(none)" else welfare_value_col,
                    "welfare_proxy_label": None if welfare_label_col == "(none)" else welfare_label_col,
                    "source": None if source_col == "(none)" else source_col,
                    "notes": None if notes_col == "(none)" else notes_col,
                }

                if st.button("Validate and import CSV"):
                    normalized_df = normalize_mapped_upload(
                        uploaded_df,
                        country_mode=country_mode,
                        country_column=country_column,
                        fixed_country=fixed_country,
                        mapping=mapping,
                    )
                    validation_errors = validate_country_upload(normalized_df)
                    if validation_errors:
                        for err in validation_errors:
                            st.error(err)
                    else:
                        save_user_country_data(DB_PATH, USER_COUNTRY_TABLE, normalized_df)
                        st.success(f"Imported {len(normalized_df)} rows.")
                        load_uploaded_data.clear()
            except Exception as exc:
                st.error("Could not parse CSV upload.")
                st.exception(exc)

    user_country_df = load_uploaded_data(str(DB_PATH))

    norway_series = norway_df[["year", "gini_all_population", "gini_excl_student_households"]].copy()
    usa_series = build_usa_gini_series(usa_df)
    ph_series = build_ph_gini_series(ph_row)

    min_year = int(min(norway_df["year"].min(), 2009))
    max_year = int(max(norway_df["year"].max(), 2024))

    st.sidebar.header("Controls")
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
            user_country_df[["country", "year", "gini"]]
            if not user_country_df.empty
            else pd.DataFrame(columns=["country", "year", "gini"]),
        ],
        ignore_index=True,
    )

    available_countries = sorted(trends["country"].dropna().unique().tolist())

    selected_countries = st.sidebar.multiselect(
        "Countries",
        available_countries,
        default=[c for c in ["Norway", "USA", "Philippines"] if c in available_countries],
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

    selected_for_rank = trends[trends["country"].isin(selected_countries) & (trends["year"] <= selected_year)].copy()
    if not selected_for_rank.empty:
        rank_df = selected_for_rank.sort_values(["country", "year"]).groupby("country", as_index=False).tail(1)
        rank_df = rank_df.sort_values("gini", ascending=False)
        st.info(
            "Latest Gini ranking (higher = more inequality): "
            + " > ".join([f"{row.country} ({row.gini:.3f})" for row in rank_df.itertuples(index=False)])
        )

    st.subheader("Gini trends over time")
    if filtered_trends.empty:
        st.warning("No data points match the selected country/year/Gini filters.")
    else:
        st.line_chart(filtered_trends.pivot_table(index="year", columns="country", values="gini", aggfunc="mean"))

    left, right = st.columns(2)
    with left:
        st.subheader("Country comparison (selected reference year)")
        gini_rows = []
        for country in selected_countries:
            country_series = trends[(trends["country"] == country) & (trends["year"] <= selected_year)].sort_values("year")
            if country_series.empty:
                continue
            last_row = country_series.iloc[-1]
            gini_rows.append({"Country": country, "Gini": float(last_row["gini"]), "Year used": int(last_row["year"])})

        gini_df = pd.DataFrame(gini_rows)
        if gini_df.empty:
            st.warning("No country comparison data for current filters.")
        else:
            st.bar_chart(gini_df.set_index("Country")["Gini"])
            st.dataframe(gini_df, hide_index=True, width="stretch")

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

        if not user_country_df.empty:
            user_welfare = user_country_df[
                (user_country_df["country"].isin(selected_countries))
                & (user_country_df["year"] <= selected_year)
            ].sort_values(["country", "year"]).groupby("country", as_index=False).tail(1)
            if not user_welfare.empty:
                extra_rows = user_welfare.apply(
                    lambda row: {
                        "Country": row["country"],
                        "Inequality (Gini)": row["gini"],
                        "Welfare proxy": row["welfare_proxy_value"],
                        "Proxy": row["welfare_proxy_label"]
                        if pd.notna(row["welfare_proxy_label"]) and str(row["welfare_proxy_label"]).strip()
                        else "User provided welfare proxy",
                    },
                    axis=1,
                )
                welfare_df = pd.concat([welfare_df, pd.DataFrame(list(extra_rows))], ignore_index=True)

        welfare_df = welfare_df[
            welfare_df["Country"].isin(selected_countries)
        ].dropna(subset=["Inequality (Gini)", "Welfare proxy"])

        if welfare_df.empty:
            st.warning("No welfare context data available for selected countries.")
        else:
            st.scatter_chart(welfare_df.set_index("Country")[["Welfare proxy", "Inequality (Gini)"]])
            st.dataframe(welfare_df, hide_index=True, width="stretch")

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
