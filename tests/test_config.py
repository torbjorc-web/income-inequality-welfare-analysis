import io

import pandas as pd

from src import config


def test_paths_point_inside_the_project():
    assert config.BASE_DIR.is_dir()
    assert (config.BASE_DIR / "dashboard.py").exists()
    assert config.DB_PATH == config.BASE_DIR / "database" / "database.db"


def test_required_tables_cover_every_table_the_dashboard_queries():
    assert config.REQUIRED_TABLES == {
        "norway_inequality_indicators_clean",
        "usa_clean",
        "philippines_clean",
        "norway_public_services",
    }
    assert config.USER_COUNTRY_TABLE not in config.REQUIRED_TABLES


def test_csv_template_parses_and_matches_the_upload_schema():
    df = pd.read_csv(io.StringIO(config.CSV_TEMPLATE))

    assert list(df.columns) == [
        "country",
        "year",
        "gini",
        "p90_p10",
        "s80_s20",
        "welfare_proxy_value",
        "welfare_proxy_label",
        "source",
        "notes",
    ]
    assert len(df) == 3
    assert df["gini"].between(0, 1).all()
    assert df["year"].between(1900, 2100).all()


def test_csv_template_passes_the_upload_validator():
    from src.services.upload import validate_country_upload

    df = pd.read_csv(io.StringIO(config.CSV_TEMPLATE))
    assert validate_country_upload(df) == []
