import pandas as pd


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
        records.append({"country": "USA", "year": 2024, "gini": float(row["year_2024_estimate"])})
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


def get_ph_gini_improvement(ph_row):
    if pd.isna(ph_row["gini_2009"]) or pd.isna(ph_row["gini_2023"]):
        return None
    return float(ph_row["gini_2009"] - ph_row["gini_2023"])
