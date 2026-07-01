import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "database" / "database.db"
OUTPUT_DIR = BASE_DIR / "outputs"
FIGURES_DIR = OUTPUT_DIR / "figures"
TABLES_DIR = OUTPUT_DIR / "tables"

COMPARISON_CSV = TABLES_DIR / "country_headline_comparison.csv"
COMPARISON_MD = TABLES_DIR / "country_headline_comparison.md"
NORWAY_TREND_PNG = FIGURES_DIR / "norway_inequality_trend.png"
WELFARE_CONTEXT_PNG = FIGURES_DIR / "welfare_context_comparison.png"
USA_NORWAY_90_10_PNG = FIGURES_DIR / "usa_norway_90_10_comparison.png"
NORWAY_3_INDICATORS_PNG = FIGURES_DIR / "norway_gini_p90p10_s80s20.png"
USA_NORWAY_COMPARISON_PNG = FIGURES_DIR / "usa_norway_comparison.png"
GINI_3COUNTRY_PNG = FIGURES_DIR / "gini_usa_norway_philippines.png"
GINI_3COUNTRY_YMAX1_PNG = FIGURES_DIR / "gini_usa_norway_philippines_ymax1.png"


def parse_number(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"..", "?", "-", "...", "…", "Z", "z"}:
        return None
    text = text.replace("*", "").replace(" ", "").replace("%", "").replace(",", ".")

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


def table_exists(conn, table_name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def get_norway_gini_series(conn):
    rows = conn.execute(
        """
        SELECT "Unnamed: 0", "Hele befolkningen"
        FROM "norway"
        """
    ).fetchall()

    series = []
    for year_raw, gini_raw in rows:
        year = parse_number(year_raw)
        gini = parse_number(gini_raw)
        if year is not None and gini is not None and 1900 <= year <= 2100:
            series.append((int(year), gini))

    if not series:
        raise ValueError("No parsable Norway year/Gini values found.")

    series.sort(key=lambda x: x[0])
    return series


def get_usa_gini(conn):
    if not table_exists(conn, "usa_clean"):
        raise ValueError("Table usa_clean not found. Run scripts\\clean_data.py first.")

    row = conn.execute(
        """
        SELECT year_2023_estimate, year_2024_estimate
        FROM "usa_clean"
        WHERE income_type = 'MONEY INCOME'
          AND measure = 'Gini index of income inequality'
        LIMIT 1
        """
    ).fetchone()
    if not row or row[1] is None:
        raise ValueError("USA Gini values not found in usa_clean.")
    return row


def get_philippines_gini(conn):
    if not table_exists(conn, "philippines_clean"):
        raise ValueError("Table philippines_clean not found. Run scripts\\clean_data.py first.")

    row = conn.execute(
        """
        SELECT gini_2009, gini_2023
        FROM "philippines_clean"
        WHERE region = 'Philippines'
        LIMIT 1
        """
    ).fetchone()
    if not row or row[1] is None:
        raise ValueError("Philippines national Gini values not found in philippines_clean.")
    return row


def get_norway_public_services_average(conn):
    rows = conn.execute(
        """
        SELECT "Barnehage", "Utdanning", "Pleie og omsorg", "Helse"
        FROM "norway_public_services"
        """
    ).fetchall()
    totals = []
    for row in rows:
        values = [parse_number(cell) for cell in row]
        if all(v is not None for v in values):
            totals.append(sum(values))
    if not totals:
        return None
    return sum(totals) / len(totals)


def get_norway_equivalence_ratio_average(conn):
    rows = conn.execute(
        """
        SELECT "SNA-skala", "EU-skala"
        FROM "norway_public_services_5"
        """
    ).fetchall()
    ratios = []
    for sna_raw, eu_raw in rows:
        sna = parse_number(sna_raw)
        eu = parse_number(eu_raw)
        if sna is not None and eu is not None and eu != 0:
            ratios.append(sna / eu)
    if not ratios:
        return None
    return sum(ratios) / len(ratios)


def get_usa_lowest_quintile_share(conn):
    row = conn.execute(
        """
        SELECT year_2024_estimate
        FROM "usa_clean"
        WHERE income_type = 'MONEY INCOME'
          AND group_name = 'Share of Aggregate Income by Percentile'
          AND measure = 'Lowest quintile'
        LIMIT 1
        """
    ).fetchone()
    return row[0] if row and row[0] is not None else None


def get_norway_p90_p10_series(conn):
    if not table_exists(conn, "norway_p90_p10_clean"):
        raise ValueError("Table norway_p90_p10_clean not found. Run scripts\\clean_data.py first.")

    rows = conn.execute(
        """
        SELECT year, p90_p10_all_population
        FROM "norway_p90_p10_clean"
        WHERE p90_p10_all_population IS NOT NULL
        ORDER BY year
        """
    ).fetchall()
    if not rows:
        raise ValueError("No Norway P90/P10 values found in norway_p90_p10_clean.")
    return rows


def get_norway_indicator_series(conn):
    if not table_exists(conn, "norway_inequality_indicators_clean"):
        raise ValueError("Table norway_inequality_indicators_clean not found. Run scripts\\clean_data.py first.")

    rows = conn.execute(
        """
        SELECT year, gini_all_population, p90_p10_all_population, s80_s20_all_population
        FROM "norway_inequality_indicators_clean"
        ORDER BY year
        """
    ).fetchall()
    if not rows:
        raise ValueError("No Norway indicator values found in norway_inequality_indicators_clean.")
    return rows


def get_usa_p90_p10_points(conn):
    if not table_exists(conn, "usa_clean"):
        raise ValueError("Table usa_clean not found. Run scripts\\clean_data.py first.")

    row = conn.execute(
        """
        SELECT year_2023_estimate, year_2024_estimate
        FROM "usa_clean"
        WHERE income_type = 'MONEY INCOME'
          AND measure = '90th/10th percentile income ratio'
        LIMIT 1
        """
    ).fetchone()
    if not row or (row[0] is None and row[1] is None):
        raise ValueError("USA 90/10 values not found in usa_clean.")

    points = []
    if row[0] is not None:
        points.append((2023, row[0]))
    if row[1] is not None:
        points.append((2024, row[1]))
    return points


def get_usa_latest_gini_and_90_10(conn):
    if not table_exists(conn, "usa_clean"):
        raise ValueError("Table usa_clean not found. Run scripts\\clean_data.py first.")

    gini_row = conn.execute(
        """
        SELECT year_2024_estimate
        FROM "usa_clean"
        WHERE income_type = 'MONEY INCOME'
          AND measure = 'Gini index of income inequality'
        LIMIT 1
        """
    ).fetchone()
    p90_row = conn.execute(
        """
        SELECT year_2024_estimate
        FROM "usa_clean"
        WHERE income_type = 'MONEY INCOME'
          AND measure = '90th/10th percentile income ratio'
        LIMIT 1
        """
    ).fetchone()

    gini = gini_row[0] if gini_row else None
    p90_p10 = p90_row[0] if p90_row else None
    if gini is None and p90_p10 is None:
        raise ValueError("USA comparison indicators not found in usa_clean.")
    return gini, p90_p10


def build_country_table(conn):
    norway_series = get_norway_gini_series(conn)
    usa_2023, usa_2024 = get_usa_gini(conn)
    ph_2009, ph_2023 = get_philippines_gini(conn)

    data = [
        {
            "country": "Norway",
            "latest_gini": norway_series[-1][1],
            "latest_year": norway_series[-1][0],
            "change_from_first_observation": norway_series[-1][1] - norway_series[0][1],
            "headline_context_indicator": "Avg public-services total (Barnehage+Utdanning+Pleie/Helse)",
            "context_value": get_norway_public_services_average(conn),
            "context_unit": "share points",
        },
        {
            "country": "USA",
            "latest_gini": usa_2024,
            "latest_year": 2024,
            "change_from_first_observation": usa_2024 - usa_2023 if usa_2023 is not None else None,
            "headline_context_indicator": "Lowest quintile income share (money income, 2024)",
            "context_value": get_usa_lowest_quintile_share(conn),
            "context_unit": "%",
        },
        {
            "country": "Philippines",
            "latest_gini": ph_2023,
            "latest_year": 2023,
            "change_from_first_observation": ph_2023 - ph_2009 if ph_2009 is not None else None,
            "headline_context_indicator": "National Gini change since 2009",
            "context_value": ph_2023 - ph_2009 if ph_2009 is not None else None,
            "context_unit": "Gini points",
        },
    ]
    return pd.DataFrame(data)


def save_comparison_table(df):
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(COMPARISON_CSV, index=False, encoding="utf-8")
    headers = list(df.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        cells = []
        for value in row.tolist():
            if isinstance(value, float):
                cells.append(f"{value:.4f}")
            elif value is None:
                cells.append("")
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    COMPARISON_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_norway_inequality_trend(conn):
    series = get_norway_gini_series(conn)
    years = [x[0] for x in series]
    values = [x[1] for x in series]

    plt.figure(figsize=(9, 5))
    plt.plot(years, values, marker="o", linewidth=2)
    plt.title("Norway inequality trend (Gini, whole population)")
    plt.xlabel("Year")
    plt.ylabel("Gini coefficient")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(NORWAY_TREND_PNG, dpi=150)
    plt.close()


def plot_welfare_context_comparison(conn):
    public_services = get_norway_public_services_average(conn)
    equivalence_ratio = get_norway_equivalence_ratio_average(conn)
    usa_lowest_quintile = get_usa_lowest_quintile_share(conn)

    labels = [
        "Norway public services\n(avg total share)",
        "Norway SNA/EU\n(avg ratio)",
        "USA lowest quintile\nincome share (2024)",
    ]
    values = [public_services, equivalence_ratio, usa_lowest_quintile]

    plt.figure(figsize=(9, 5))
    bars = plt.bar(labels, values)
    plt.title("Public services / equivalence scale / poverty proxy")
    plt.ylabel("Value (mixed units)")
    plt.grid(axis="y", alpha=0.3)
    for bar, value in zip(bars, values):
        if value is not None:
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{value:.2f}",
                ha="center",
                va="bottom",
            )
    plt.tight_layout()
    plt.savefig(WELFARE_CONTEXT_PNG, dpi=150)
    plt.close()


def plot_usa_norway_90_10_comparison(conn):
    norway_rows = get_norway_p90_p10_series(conn)
    usa_rows = get_usa_p90_p10_points(conn)

    norway_years = [row[0] for row in norway_rows]
    norway_values = [row[1] for row in norway_rows]
    usa_years = [row[0] for row in usa_rows]
    usa_values = [row[1] for row in usa_rows]

    plt.figure(figsize=(10, 5))
    plt.plot(norway_years, norway_values, marker="o", linewidth=2, label="Norway P90/P10")
    plt.plot(usa_years, usa_values, marker="o", linewidth=2, label="USA 90th/10th ratio")
    plt.title("P90/P10 comparison: Norway vs USA")
    plt.xlabel("Year")
    plt.ylabel("P90/P10 income ratio")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(USA_NORWAY_90_10_PNG, dpi=150)
    plt.close()


def plot_norway_three_indicators(conn):
    rows = get_norway_indicator_series(conn)
    years = [r[0] for r in rows]
    gini_vals = [r[1] for r in rows]
    p90_vals = [r[2] for r in rows]
    s80_vals = [r[3] for r in rows]

    fig, ax_left = plt.subplots(figsize=(10, 5))
    ax_right = ax_left.twinx()

    line_gini = ax_left.plot(years, gini_vals, marker="o", linewidth=2, label="Gini")[0]
    line_p90 = ax_right.plot(years, p90_vals, marker="o", linewidth=2, label="P90/P10", color="tab:orange")[0]
    line_s80 = ax_right.plot(years, s80_vals, marker="o", linewidth=2, label="S80/S20", color="tab:green")[0]

    ax_left.set_title("Norway inequality indicators: Gini, P90/P10, S80/S20")
    ax_left.set_xlabel("Year")
    ax_left.set_ylabel("Gini")
    ax_right.set_ylabel("Ratios")
    ax_left.grid(True, alpha=0.3)

    handles = [line_gini, line_p90, line_s80]
    labels = [h.get_label() for h in handles]
    ax_left.legend(handles, labels, loc="upper left")

    fig.tight_layout()
    fig.savefig(NORWAY_3_INDICATORS_PNG, dpi=150)
    plt.close(fig)


def plot_usa_norway_comparison(conn):
    norway_rows = get_norway_indicator_series(conn)
    norway_latest = norway_rows[-1]
    norway_gini = norway_latest[1]
    norway_p90 = norway_latest[2]

    usa_gini, usa_p90 = get_usa_latest_gini_and_90_10(conn)

    categories = ["Gini", "P90/P10"]
    norway_values = [norway_gini, norway_p90]
    usa_values = [usa_gini, usa_p90]

    x = [0, 1]
    width = 0.35

    plt.figure(figsize=(8, 5))
    plt.bar([i - width / 2 for i in x], norway_values, width=width, label="Norway")
    plt.bar([i + width / 2 for i in x], usa_values, width=width, label="USA")
    plt.xticks(x, categories)
    plt.title("USA vs Norway comparison (latest available)")
    plt.ylabel("Value")
    plt.grid(axis="y", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(USA_NORWAY_COMPARISON_PNG, dpi=150)
    plt.close()


def plot_gini_three_country_comparison(conn):
    norway_series = get_norway_gini_series(conn)
    _, usa_2024 = get_usa_gini(conn)
    _, ph_2023 = get_philippines_gini(conn)

    countries = ["Norway", "USA", "Philippines"]
    values = [norway_series[-1][1], usa_2024, ph_2023]

    plt.figure(figsize=(8, 5))
    bars = plt.bar(countries, values, color=["tab:blue", "tab:orange", "tab:green"])
    plt.title("Gini comparison: USA, Norway, Philippines")
    plt.ylabel("Gini coefficient")
    plt.grid(axis="y", alpha=0.3)

    for bar, value in zip(bars, values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.3f}",
            ha="center",
            va="bottom",
        )

    plt.tight_layout()
    plt.savefig(GINI_3COUNTRY_PNG, dpi=150)
    plt.close()


def plot_gini_three_country_comparison_ymax1(conn):
    norway_series = get_norway_gini_series(conn)
    _, usa_2024 = get_usa_gini(conn)
    _, ph_2023 = get_philippines_gini(conn)

    countries = ["Norway", "USA", "Philippines"]
    values = [norway_series[-1][1], usa_2024, ph_2023]

    plt.figure(figsize=(8, 5))
    bars = plt.bar(countries, values, color=["tab:blue", "tab:orange", "tab:green"])
    plt.title("Gini comparison: USA, Norway, Philippines (y-max = 1.0)")
    plt.ylabel("Gini coefficient")
    plt.ylim(0, 1.0)
    plt.grid(axis="y", alpha=0.3)

    for bar, value in zip(bars, values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.3f}",
            ha="center",
            va="bottom",
        )

    plt.tight_layout()
    plt.savefig(GINI_3COUNTRY_YMAX1_PNG, dpi=150)
    plt.close()


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        table_df = build_country_table(conn)
        save_comparison_table(table_df)
        plot_norway_inequality_trend(conn)
        plot_welfare_context_comparison(conn)
        plot_usa_norway_90_10_comparison(conn)
        plot_norway_three_indicators(conn)
        plot_usa_norway_comparison(conn)
        plot_gini_three_country_comparison(conn)
        plot_gini_three_country_comparison_ymax1(conn)

    print(f"Created comparison table: {COMPARISON_CSV}")
    print(f"Created markdown table:  {COMPARISON_MD}")
    print(f"Created chart:           {NORWAY_TREND_PNG}")
    print(f"Created chart:           {WELFARE_CONTEXT_PNG}")
    print(f"Created chart:           {USA_NORWAY_90_10_PNG}")
    print(f"Created chart:           {NORWAY_3_INDICATORS_PNG}")
    print(f"Created chart:           {USA_NORWAY_COMPARISON_PNG}")
    print(f"Created chart:           {GINI_3COUNTRY_PNG}")
    print(f"Created chart:           {GINI_3COUNTRY_YMAX1_PNG}")


if __name__ == "__main__":
    main()