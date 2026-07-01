import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DB_PATH = BASE_DIR / "database" / "database.db"

USA_RAW_PATH = RAW_DIR / "USA Income Distribution Measures.csv"
PH_RAW_PATH = RAW_DIR / "Gini Philippines version 2.csv"
NORWAY_RAW_PATH = RAW_DIR / "Norge Inntektsfordelingen belyst ved ulike ulikhetsmål. Inntekt etter skatt per forbruksenhet (EU-skala).csv"


def parse_number(value):
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    text = text.replace("*", "").replace(" ", "").replace("%", "")
    text = text.replace(",", ".")
    if text in {"Z", "z", "...", "…", "-", "?", "nan"}:
        return None

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


def read_csv_flexible(path, sep):
    last_error = None
    for enc in ("utf-8-sig", "utf-8", "latin1", "cp1252"):
        try:
            return pd.read_csv(
                path,
                sep=sep,
                header=None,
                dtype=str,
                engine="python",
                encoding=enc,
                on_bad_lines="skip",
            )
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Unable to read CSV file: {path}") from last_error


def clean_usa_dataset():
    raw_df = read_csv_flexible(USA_RAW_PATH, sep=";")
    raw_df = raw_df.fillna("")

    header_idx_candidates = raw_df.index[raw_df[0].str.strip() == "Measure"].tolist()
    if not header_idx_candidates:
        raise ValueError("Could not find 'Measure' header row in USA dataset.")
    header_idx = header_idx_candidates[0]

    rows = raw_df.iloc[header_idx + 2 :].reset_index(drop=True)

    current_income_type = None
    current_group = None
    cleaned_rows = []

    for _, row in rows.iterrows():
        measure = str(row[0]).strip()
        cells = [str(row[i]).strip() for i in range(1, 7)]

        if not measure:
            continue
        if measure.startswith("*An asterisk") or measure.startswith("Z Rounds") or measure.startswith("1 A margin"):
            break
        if measure.startswith("2 Calculated") or measure.startswith("Note:") or measure.startswith("Source:"):
            continue

        if all(not c for c in cells):
            if measure == measure.upper():
                current_income_type = measure
                current_group = None
            else:
                current_group = measure
            continue

        cleaned_rows.append(
            {
                "income_type": current_income_type,
                "group_name": current_group,
                "measure": measure.replace("...", "").strip(),
                "year_2023_estimate": parse_number(cells[0]),
                "year_2023_moe": parse_number(cells[1]),
                "year_2024_estimate": parse_number(cells[2]),
                "year_2024_moe": parse_number(cells[3]),
                "pct_change_estimate": parse_number(cells[4]),
                "pct_change_moe": parse_number(cells[5]),
            }
        )

    cleaned_df = pd.DataFrame(cleaned_rows)
    cleaned_df = cleaned_df.dropna(subset=["measure"]).reset_index(drop=True)
    return cleaned_df


def clean_philippines_dataset():
    raw_df = read_csv_flexible(PH_RAW_PATH, sep=",")
    raw_df = raw_df.fillna("")

    header_idx_candidates = raw_df.index[raw_df[0].str.strip() == "Region"].tolist()
    if not header_idx_candidates:
        raise ValueError("Could not find 'Region' header row in Philippines dataset.")
    header_idx = header_idx_candidates[0]

    rows = raw_df.iloc[header_idx + 1 :].reset_index(drop=True)
    cleaned_rows = []

    for _, row in rows.iterrows():
        region = str(row[0]).strip()
        if not region:
            continue
        if region.startswith("Note:") or region.startswith("Source:"):
            break

        values = [str(row[i]).strip() for i in range(1, 7)]
        if all(not value for value in values):
            continue

        cleaned_rows.append(
            {
                "region": region,
                "gini_2009": parse_number(values[0]),
                "gini_2012": parse_number(values[1]),
                "gini_2015": parse_number(values[2]),
                "gini_2018": parse_number(values[3]),
                "gini_2021": parse_number(values[4]),
                "gini_2023": parse_number(values[5]),
            }
        )

    cleaned_df = pd.DataFrame(cleaned_rows)
    cleaned_df = cleaned_df.dropna(subset=["region"]).reset_index(drop=True)
    return cleaned_df


def clean_norway_p90_p10_dataset():
    raw_df = read_csv_flexible(NORWAY_RAW_PATH, sep=";")
    raw_df = raw_df.fillna("")

    cleaned_rows = []
    for _, row in raw_df.iterrows():
        year = parse_number(row[0])
        if year is None or year < 1900 or year > 2100:
            continue

        p90_p10_all = parse_number(row[3]) if len(row) > 3 else None
        p90_p10_ex_students = parse_number(row[7]) if len(row) > 7 else None

        if p90_p10_all is None and p90_p10_ex_students is None:
            continue

        cleaned_rows.append(
            {
                "year": int(year),
                "p90_p10_all_population": p90_p10_all,
                "p90_p10_excl_student_households": p90_p10_ex_students,
            }
        )

    cleaned_df = pd.DataFrame(cleaned_rows)
    if cleaned_df.empty:
        cleaned_df = pd.DataFrame(
            columns=[
                "year",
                "p90_p10_all_population",
                "p90_p10_excl_student_households",
            ]
        )
    else:
        cleaned_df = cleaned_df.sort_values("year").reset_index(drop=True)
    return cleaned_df


def main():
    if not USA_RAW_PATH.exists():
        raise FileNotFoundError(f"USA source file not found: {USA_RAW_PATH}")
    if not PH_RAW_PATH.exists():
        raise FileNotFoundError(f"Philippines source file not found: {PH_RAW_PATH}")
    if not NORWAY_RAW_PATH.exists():
        raise FileNotFoundError(f"Norway source file not found: {NORWAY_RAW_PATH}")
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    usa_df = clean_usa_dataset()
    ph_df = clean_philippines_dataset()
    norway_df = clean_norway_p90_p10_dataset()

    usa_csv_path = PROCESSED_DIR / "usa_income_distribution_clean.csv"
    ph_csv_path = PROCESSED_DIR / "philippines_gini_clean.csv"
    norway_csv_path = PROCESSED_DIR / "norway_p90_p10_clean.csv"
    usa_df.to_csv(usa_csv_path, index=False, encoding="utf-8")
    ph_df.to_csv(ph_csv_path, index=False, encoding="utf-8")
    norway_df.to_csv(norway_csv_path, index=False, encoding="utf-8")

    with sqlite3.connect(DB_PATH) as conn:
        usa_df.to_sql("usa_clean", conn, if_exists="replace", index=False)
        ph_df.to_sql("philippines_clean", conn, if_exists="replace", index=False)
        norway_df.to_sql("norway_p90_p10_clean", conn, if_exists="replace", index=False)

    print(f"Clean USA rows: {len(usa_df)} -> {usa_csv_path}")
    print(f"Clean Philippines rows: {len(ph_df)} -> {ph_csv_path}")
    print(f"Clean Norway P90/P10 rows: {len(norway_df)} -> {norway_csv_path}")
    print("Wrote tables to database.db: usa_clean, philippines_clean, norway_p90_p10_clean")


if __name__ == "__main__":
    main()