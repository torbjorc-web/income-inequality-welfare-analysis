import io

import pandas as pd
import pytest

from src.services.upload import normalize_mapped_upload, validate_country_upload

FULL_MAPPING = {
    "year": "Year",
    "gini": "Gini",
    "p90_p10": "P90P10",
    "s80_s20": "S80S20",
    "welfare_proxy_value": "Proxy",
    "welfare_proxy_label": "ProxyLabel",
    "source": "Source",
    "notes": "Notes",
}

MINIMAL_MAPPING = {"year": "Year", "gini": "Gini"}


@pytest.fixture
def raw_upload():
    csv = (
        "Country,Year,Gini,P90P10,S80S20,Proxy,ProxyLabel,Source,Notes\n"
        " Kenya ,2019,0.42,9.5,7.1,12.0,Coverage,KNBS,first\n"
        " Kenya ,2021,0.40,9.1,6.8,13.0,Coverage,KNBS,second\n"
    )
    return pd.read_csv(io.StringIO(csv))


def valid_frame():
    return pd.DataFrame(
        {
            "country": ["Kenya", "Kenya"],
            "year": pd.array([2019, 2021], dtype="Int64"),
            "gini": [0.42, 0.40],
        }
    )


def test_normalize_maps_every_column_and_strips_country_values(raw_upload):
    out = normalize_mapped_upload(raw_upload, "Use column", "Country", "", FULL_MAPPING)

    assert list(out.columns) == [
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
    assert out["country"].tolist() == ["Kenya", "Kenya"]
    assert out["year"].tolist() == [2019, 2021]
    assert out["gini"].tolist() == pytest.approx([0.42, 0.40])
    assert out["notes"].tolist() == ["first", "second"]


def test_normalize_applies_a_fixed_country_name(raw_upload):
    out = normalize_mapped_upload(raw_upload, "Use fixed country name", None, "  Kenya  ", FULL_MAPPING)

    assert out["country"].tolist() == ["Kenya", "Kenya"]


def test_normalize_fills_unmapped_optional_columns(raw_upload):
    out = normalize_mapped_upload(raw_upload, "Use fixed country name", None, "Kenya", MINIMAL_MAPPING)

    assert out[["p90_p10", "s80_s20", "welfare_proxy_value"]].isna().all().all()
    assert out["welfare_proxy_label"].tolist() == ["", ""]
    assert out["source"].tolist() == ["", ""]
    assert out["notes"].tolist() == ["", ""]


def test_normalize_coerces_unparsable_numbers_to_missing():
    raw = pd.DataFrame({"Year": ["2019", "not-a-year"], "Gini": ["0.42", "high"]})

    out = normalize_mapped_upload(raw, "Use fixed country name", None, "Kenya", MINIMAL_MAPPING)

    assert out["year"].tolist() == [2019, pd.NA]
    assert out["gini"].iloc[0] == pytest.approx(0.42)
    assert pd.isna(out["gini"].iloc[1])


def test_normalize_produces_nullable_integer_years(raw_upload):
    out = normalize_mapped_upload(raw_upload, "Use column", "Country", "", FULL_MAPPING)

    assert str(out["year"].dtype) == "Int64"


def test_valid_upload_has_no_errors():
    assert validate_country_upload(valid_frame()) == []


def test_empty_upload_is_rejected():
    errors = validate_country_upload(pd.DataFrame(columns=["country", "year", "gini"]))

    assert errors == ["The uploaded file has no rows after mapping."]


def test_missing_required_columns_are_reported_and_short_circuit():
    errors = validate_country_upload(pd.DataFrame({"country": ["Kenya"]}))

    assert len(errors) == 1
    assert "year" in errors[0] and "gini" in errors[0]


def test_blank_country_is_rejected():
    df = valid_frame()
    df.loc[0, "country"] = "   "

    assert "Country cannot be empty." in validate_country_upload(df)


def test_non_numeric_year_is_rejected():
    df = valid_frame()
    df["year"] = ["2019", "nineteen"]

    assert "Year must be numeric for all rows." in validate_country_upload(df)


@pytest.mark.parametrize("bad_year", [1899, 2101])
def test_out_of_range_year_is_rejected(bad_year):
    df = valid_frame()
    df.loc[0, "year"] = bad_year

    assert "Year must be between 1900 and 2100." in validate_country_upload(df)


def test_non_numeric_gini_is_rejected():
    df = valid_frame()
    df["gini"] = ["0.42", "very unequal"]

    assert "Gini must be numeric for all rows." in validate_country_upload(df)


@pytest.mark.parametrize("bad_gini", [-0.01, 1.01, 42.0])
def test_out_of_range_gini_is_rejected(bad_gini):
    df = valid_frame()
    df.loc[0, "gini"] = bad_gini

    assert "Gini must be between 0 and 1." in validate_country_upload(df)


@pytest.mark.parametrize("boundary", [0.0, 1.0])
def test_gini_bounds_are_inclusive(boundary):
    df = valid_frame()
    df.loc[0, "gini"] = boundary

    assert validate_country_upload(df) == []


def test_duplicate_country_year_rows_are_rejected():
    df = valid_frame()
    df.loc[1, "year"] = 2019

    assert "Duplicate country-year rows found in upload." in validate_country_upload(df)


def test_same_year_for_different_countries_is_allowed():
    df = valid_frame()
    df.loc[1, ["country", "year"]] = ["Uganda", 2019]

    assert validate_country_upload(df) == []


def test_multiple_problems_are_reported_together():
    df = valid_frame()
    df.loc[0, "country"] = ""
    df.loc[0, "gini"] = 2.0

    errors = validate_country_upload(df)

    assert "Country cannot be empty." in errors
    assert "Gini must be between 0 and 1." in errors


def test_normalized_malformed_csv_fails_validation():
    raw = pd.DataFrame({"Year": ["2019", "2019"], "Gini": ["0.42", "0.44"]})
    out = normalize_mapped_upload(raw, "Use fixed country name", None, "Kenya", MINIMAL_MAPPING)

    assert "Duplicate country-year rows found in upload." in validate_country_upload(out)
