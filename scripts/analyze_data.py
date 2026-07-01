import sqlite3
from pathlib import Path
from statistics import mean


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "database" / "database.db"
OUTPUT_DIR = BASE_DIR / "outputs"
SUMMARY_PATH = OUTPUT_DIR / "analysis_summary.txt"


def parse_number(value):
    if value is None:
        return None

    text = str(value).strip()
    if not text or text in {"..", "?", "-"}:
        return None

    text = text.replace(" ", "").replace("%", "")
    text = text.replace(",", ".")

    cleaned = []
    for ch in text:
        if ch.isdigit() or ch in {".", "-"}:
            cleaned.append(ch)
        else:
            break

    try:
        return float("".join(cleaned))
    except ValueError:
        return None


def get_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]


def table_columns(conn, table_name):
    rows = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return [row[1] for row in rows]


def row_count(conn, table_name):
    return conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]


def table_exists(conn, table_name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def non_empty_count(conn, table_name, column_name):
    query = f'SELECT COUNT(*) FROM "{table_name}" WHERE "{column_name}" IS NOT NULL AND TRIM("{column_name}") != ""'
    return conn.execute(query).fetchone()[0]


def summarize_table_quality(conn, table_name):
    rows = row_count(conn, table_name)
    columns = table_columns(conn, table_name)
    info = [f"- {table_name}: {rows} rows, {len(columns)} columns"]

    if rows == 0:
        return info

    for col in columns[:5]:
        filled = non_empty_count(conn, table_name, col)
        pct = (filled / rows) * 100
        info.append(f"  - {col}: {filled}/{rows} non-empty ({pct:.1f}%)")

    if len(columns) > 5:
        info.append("  - ...")

    return info


def analyze_norway_public_services(conn):
    table_name = "norway_public_services"
    columns = ["Barnehage", "Utdanning", "Pleie og omsorg", "Helse"]
    rows = conn.execute(
        f'SELECT "Land", "Barnehage", "Utdanning", "Pleie og omsorg", "Helse" FROM "{table_name}"'
    ).fetchall()

    valid_rows = []
    for row in rows:
        country = row[0]
        values = [parse_number(v) for v in row[1:]]
        if country and all(v is not None for v in values):
            valid_rows.append((country, values))

    if not valid_rows:
        return ["## Norway public services", "- No fully parsable rows found."]

    category_means = []
    for idx, col in enumerate(columns):
        category_means.append((col, mean([vals[idx] for _, vals in valid_rows])))

    totals = [(country, sum(vals)) for country, vals in valid_rows]
    highest_total = max(totals, key=lambda x: x[1])
    lowest_total = min(totals, key=lambda x: x[1])

    lines = [
        "## Norway public services",
        f"- Parsed rows: {len(valid_rows)}",
        f"- Highest combined spending share: {highest_total[0]} ({highest_total[1]:.2f})",
        f"- Lowest combined spending share: {lowest_total[0]} ({lowest_total[1]:.2f})",
        "- Average by category:",
    ]
    for col, avg_value in category_means:
        lines.append(f"  - {col}: {avg_value:.2f}")
    return lines


def analyze_scale_table(conn):
    table_name = "norway_public_services_5"
    rows = conn.execute(f'SELECT "Alder", "SNA-skala", "EU-skala" FROM "{table_name}"').fetchall()

    parsed = []
    for age, sna, eu in rows:
        sna_val = parse_number(sna)
        eu_val = parse_number(eu)
        if age and sna_val is not None and eu_val is not None and eu_val != 0:
            parsed.append((age, sna_val, eu_val, sna_val / eu_val))

    if not parsed:
        return ["## SNA vs EU scale", "- No parsable rows found."]

    biggest_gap = max(parsed, key=lambda x: abs(x[1] - x[2]))
    lines = [
        "## SNA vs EU scale",
        f"- Parsed rows: {len(parsed)}",
        f"- Largest absolute gap: {biggest_gap[0]} (SNA={biggest_gap[1]:.2f}, EU={biggest_gap[2]:.2f})",
        "- SNA/EU ratio by age group:",
    ]
    for age, _, _, ratio in parsed:
        lines.append(f"  - {age}: {ratio:.2f}")
    return lines


def analyze_norway_gini_trend(conn):
    table_name = "norway"
    rows = conn.execute(
        f'SELECT "Unnamed: 0", "Hele befolkningen" FROM "{table_name}"'
    ).fetchall()

    pairs = []
    for year_raw, gini_raw in rows:
        year = parse_number(year_raw)
        gini = parse_number(gini_raw)
        if year is not None and gini is not None and 1900 <= year <= 2100:
            pairs.append((int(year), gini))

    if not pairs:
        return ["## Norway inequality trend", "- No parsable year/Gini rows found."]

    pairs.sort(key=lambda x: x[0])
    first_year, first_gini = pairs[0]
    last_year, last_gini = pairs[-1]
    delta = last_gini - first_gini

    return [
        "## Norway inequality trend",
        f"- Parsed points: {len(pairs)}",
        f"- First year: {first_year} (Gini {first_gini:.3f})",
        f"- Last year: {last_year} (Gini {last_gini:.3f})",
        f"- Change over period: {delta:+.3f}",
    ]


def analyze_usa_clean_trend(conn):
    table_name = "usa_clean"
    if not table_exists(conn, table_name):
        return ["## USA cleaned trend", "- Table usa_clean not found. Run scripts\\clean_data.py first."]

    rows = conn.execute(
        f"""
        SELECT income_type, measure, year_2023_estimate, year_2024_estimate
        FROM "{table_name}"
        WHERE measure IN ('Gini index of income inequality', 'Highest quintile')
        ORDER BY income_type, measure
        """
    ).fetchall()

    if not rows:
        return ["## USA cleaned trend", "- No trend rows found in usa_clean."]

    lines = ["## USA cleaned trend"]
    for income_type, measure, y2023, y2024 in rows:
        if y2023 is None or y2024 is None:
            continue
        delta = y2024 - y2023
        lines.append(
            f"- {income_type} | {measure}: {y2023:.3f} -> {y2024:.3f} ({delta:+.3f})"
        )

    if len(lines) == 1:
        lines.append("- No rows with complete 2023/2024 estimates.")
    return lines


def analyze_philippines_clean_trend(conn):
    table_name = "philippines_clean"
    if not table_exists(conn, table_name):
        return [
            "## Philippines cleaned trend",
            "- Table philippines_clean not found. Run scripts\\clean_data.py first.",
        ]

    national = conn.execute(
        f"""
        SELECT gini_2009, gini_2012, gini_2015, gini_2018, gini_2021, gini_2023
        FROM "{table_name}"
        WHERE region = 'Philippines'
        LIMIT 1
        """
    ).fetchone()

    best_2023 = conn.execute(
        f"""
        SELECT region, gini_2023
        FROM "{table_name}"
        WHERE region <> 'Philippines' AND gini_2023 IS NOT NULL
        ORDER BY gini_2023 ASC
        LIMIT 1
        """
    ).fetchone()

    worst_2023 = conn.execute(
        f"""
        SELECT region, gini_2023
        FROM "{table_name}"
        WHERE region <> 'Philippines' AND gini_2023 IS NOT NULL
        ORDER BY gini_2023 DESC
        LIMIT 1
        """
    ).fetchone()

    lines = ["## Philippines cleaned trend"]
    if national:
        y2009 = national[0]
        y2023 = national[5]
        if y2009 is not None and y2023 is not None:
            lines.append(f"- National Gini: {y2009:.4f} (2009) -> {y2023:.4f} (2023) ({(y2023 - y2009):+.4f})")
        lines.append(
            "- National series: "
            f"2009={national[0]:.4f}, 2012={national[1]:.4f}, 2015={national[2]:.4f}, "
            f"2018={national[3]:.4f}, 2021={national[4]:.4f}, 2023={national[5]:.4f}"
        )
    else:
        lines.append("- National row ('Philippines') not found.")

    if best_2023:
        lines.append(f"- Lowest regional Gini in 2023: {best_2023[0]} ({best_2023[1]:.4f})")
    if worst_2023:
        lines.append(f"- Highest regional Gini in 2023: {worst_2023[0]} ({worst_2023[1]:.4f})")
    return lines


def analyze_three_country_comparison(conn):
    lines = ["## Norway vs USA vs Philippines comparison"]

    norway_rows = conn.execute(
        """
        SELECT "Unnamed: 0", "Hele befolkningen"
        FROM "norway"
        """
    ).fetchall() if table_exists(conn, "norway") else []
    norway_pairs = []
    for year_raw, gini_raw in norway_rows:
        year = parse_number(year_raw)
        gini = parse_number(gini_raw)
        if year is not None and gini is not None and 1900 <= year <= 2100:
            norway_pairs.append((int(year), gini))
    norway_latest = max(norway_pairs, key=lambda x: x[0]) if norway_pairs else None

    usa_gini = conn.execute(
        """
        SELECT year_2024_estimate
        FROM "usa_clean"
        WHERE income_type = 'MONEY INCOME' AND measure = 'Gini index of income inequality'
        LIMIT 1
        """
    ).fetchone() if table_exists(conn, "usa_clean") else None

    ph_gini = conn.execute(
        """
        SELECT gini_2023
        FROM "philippines_clean"
        WHERE region = 'Philippines'
        LIMIT 1
        """
    ).fetchone() if table_exists(conn, "philippines_clean") else None

    metrics = []
    if norway_latest:
        metrics.append(("Norway", norway_latest[1], norway_latest[0]))
    if usa_gini and usa_gini[0] is not None:
        metrics.append(("USA", usa_gini[0], 2024))
    if ph_gini and ph_gini[0] is not None:
        metrics.append(("Philippines", ph_gini[0], 2023))

    if len(metrics) < 2:
        lines.append("- Could not compute multi-country benchmark (missing values).")
        return lines

    lines.append(
        "- Latest national Gini values used: "
        + ", ".join([f"{name}={value:.4f} ({year})" for name, value, year in metrics])
    )

    sorted_metrics = sorted(metrics, key=lambda x: x[1], reverse=True)
    lines.append(
        "- Highest to lowest inequality (by Gini): "
        + " > ".join([f"{name} ({value:.4f})" for name, value, _ in sorted_metrics])
    )

    value_map = {name: value for name, value, _ in metrics}
    if "USA" in value_map and "Philippines" in value_map:
        lines.append(
            f"- Gap USA - Philippines: {value_map['USA'] - value_map['Philippines']:+.4f}"
        )
    if "USA" in value_map and "Norway" in value_map:
        lines.append(f"- Gap USA - Norway: {value_map['USA'] - value_map['Norway']:+.4f}")
    if "Philippines" in value_map and "Norway" in value_map:
        lines.append(
            f"- Gap Philippines - Norway: {value_map['Philippines'] - value_map['Norway']:+.4f}"
        )

    return lines


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        tables = get_tables(conn)
        lines = [
            "Income inequality analysis summary",
            f"Database: {DB_PATH}",
            f"Tables found: {len(tables)}",
            "",
            "## Table quality profile",
        ]

        for table_name in tables:
            lines.extend(summarize_table_quality(conn, table_name))

        lines.append("")
        lines.extend(analyze_norway_gini_trend(conn))
        lines.append("")
        lines.extend(analyze_norway_public_services(conn))
        lines.append("")
        lines.extend(analyze_scale_table(conn))
        lines.append("")
        lines.extend(analyze_usa_clean_trend(conn))
        lines.append("")
        lines.extend(analyze_philippines_clean_trend(conn))
        lines.append("")
        lines.extend(analyze_three_country_comparison(conn))

    summary = "\n".join(lines) + "\n"
    SUMMARY_PATH.write_text(summary, encoding="utf-8")
    print(summary)
    print(f"Saved summary to: {SUMMARY_PATH}")


if __name__ == "__main__":
    main()