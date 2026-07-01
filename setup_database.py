import sqlite3
from pathlib import Path
import pandas as pd

RAW_DIR = Path('data/raw')
DB_DIR = Path('database')
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / 'database.db'

CSV_TABLES = [
    ('norway', RAW_DIR / 'Norge Inntektsfordelingen belyst ved ulike ulikhetsmål. Inntekt etter skatt per forbruksenhet (EU-skala).csv'),
    ('usa', RAW_DIR / 'USA Income Distribution Measures.csv'),
    ('philippines', RAW_DIR / 'Gini Philippines version 2.csv'),
    ('norway_public_services', RAW_DIR / 'figur-1-offentlige-utgif.csv'),
    ('norway_public_services_2', RAW_DIR / 'Tabell2 Fordelingseffekter off tjenester(Tabell 2).csv'),
    ('norway_public_services_3', RAW_DIR / 'Tabell3 Fordelingseffekter off tjenester(Tabell 3).csv'),
    ('norway_public_services_4', RAW_DIR / 'Tabell4 Fordelingseffekter off tjenester(Tabell 4).csv'),
    ('norway_public_services_5', RAW_DIR / 'figur-2-bidrag-til-eu-sk.csv'),
]


def clean_columns(df):
    df = df.copy()
    df.columns = [str(c).strip().replace('\n', ' ').replace('  ', ' ') for c in df.columns]
    return df


def detect_delimiter(path, encoding):
    with open(path, 'r', encoding=encoding, errors='ignore') as f:
        sample_lines = []
        for line in f:
            line = line.strip()
            if not line:
                continue
            sample_lines.append(line)
            if len(sample_lines) >= 20:
                break

    semicolon_count = sum(line.count(';') for line in sample_lines)
    comma_count = sum(line.count(',') for line in sample_lines)
    return ';' if semicolon_count >= comma_count else ','


def load_csv(path):
    for enc in ('utf-8-sig', 'utf-8', 'latin1'):
        try:
            delimiter = detect_delimiter(path, enc)
            return pd.read_csv(path, encoding=enc, sep=delimiter, engine='python', on_bad_lines='skip')
        except Exception:
            pass
    with open(path, 'r', encoding='utf-8', errors='ignore', newline='') as f:
        delimiter = ';'
        try:
            f.seek(0)
            sample = []
            for line in f:
                line = line.strip()
                if line:
                    sample.append(line)
                if len(sample) >= 20:
                    break
            semicolon_count = sum(line.count(';') for line in sample)
            comma_count = sum(line.count(',') for line in sample)
            delimiter = ';' if semicolon_count >= comma_count else ','
        except Exception:
            pass
        f.seek(0)
        return pd.read_csv(f, sep=delimiter, engine='python', on_bad_lines='skip')


def main():
    configured_files = {file_path.name for _, file_path in CSV_TABLES}
    available_files = {p.name for p in RAW_DIR.glob('*.csv')}

    missing_in_setup = sorted(available_files - configured_files)
    missing_in_folder = sorted(configured_files - available_files)

    if missing_in_setup:
        print(f'WARNING: CSV files in data/raw not listed in CSV_TABLES: {missing_in_setup}')
    if missing_in_folder:
        print(f'WARNING: CSV files listed in CSV_TABLES but not found in data/raw: {missing_in_folder}')

    with sqlite3.connect(DB_PATH) as conn:
        for table_name, file_path in CSV_TABLES:
            if not file_path.exists():
                print(f'SKIP: {file_path} not found')
                continue
            try:
                df = load_csv(file_path)
                df = clean_columns(df)
                df.to_sql(table_name, conn, if_exists='replace', index=False)
                print(f'OK: {table_name} <- {file_path.name} ({len(df)} rows, {len(df.columns)} cols)')
            except Exception as e:
                print(f'ERROR: {file_path.name}: {e}')

    print(f'Database created at: {DB_PATH}')


if __name__ == '__main__':
    main()