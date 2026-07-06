from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "database" / "database.db"
USER_COUNTRY_TABLE = "user_country_indicators"

REQUIRED_TABLES = {
    "norway_inequality_indicators_clean",
    "usa_clean",
    "philippines_clean",
    "norway_public_services",
}

CSV_TEMPLATE = """country,year,gini,p90_p10,s80_s20,welfare_proxy_value,welfare_proxy_label,source,notes
South Africa,2018,0.630,15.2,9.8,13.5,Social grant coverage (%),Stats SA,Example row
South Africa,2021,0.620,14.9,9.4,14.1,Social grant coverage (%),Stats SA,Example row
South Africa,2023,0.610,14.5,9.0,14.8,Social grant coverage (%),Stats SA,Example row
"""
