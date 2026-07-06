import pandas as pd


def normalize_mapped_upload(raw_df, country_mode, country_column, fixed_country, mapping):
    out = pd.DataFrame()

    if country_mode == "Use column":
        out["country"] = raw_df[country_column].astype(str).str.strip()
    else:
        out["country"] = fixed_country.strip()

    out["year"] = raw_df[mapping["year"]]
    out["gini"] = raw_df[mapping["gini"]]

    for optional_col in [
        "p90_p10",
        "s80_s20",
        "welfare_proxy_value",
        "welfare_proxy_label",
        "source",
        "notes",
    ]:
        source_col = mapping.get(optional_col)
        if source_col:
            out[optional_col] = raw_df[source_col]
        else:
            out[optional_col] = None

    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    out["gini"] = pd.to_numeric(out["gini"], errors="coerce")
    out["p90_p10"] = pd.to_numeric(out["p90_p10"], errors="coerce")
    out["s80_s20"] = pd.to_numeric(out["s80_s20"], errors="coerce")
    out["welfare_proxy_value"] = pd.to_numeric(out["welfare_proxy_value"], errors="coerce")
    out["welfare_proxy_label"] = out["welfare_proxy_label"].astype(str).replace({"nan": ""})
    out["source"] = out["source"].astype(str).replace({"nan": ""})
    out["notes"] = out["notes"].astype(str).replace({"nan": ""})

    return out


def validate_country_upload(df):
    errors = []
    if df.empty:
        errors.append("The uploaded file has no rows after mapping.")
        return errors

    required_columns = ["country", "year", "gini"]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        errors.append(f"Missing required mapped columns: {', '.join(missing)}")
        return errors

    if df["country"].astype(str).str.strip().eq("").any():
        errors.append("Country cannot be empty.")

    year_values = pd.to_numeric(df["year"], errors="coerce")
    if year_values.isna().any():
        errors.append("Year must be numeric for all rows.")
    elif ((year_values < 1900) | (year_values > 2100)).any():
        errors.append("Year must be between 1900 and 2100.")

    gini_values = pd.to_numeric(df["gini"], errors="coerce")
    if gini_values.isna().any():
        errors.append("Gini must be numeric for all rows.")
    elif ((gini_values < 0) | (gini_values > 1)).any():
        errors.append("Gini must be between 0 and 1.")

    if df.assign(year=year_values).duplicated(subset=["country", "year"]).any():
        errors.append("Duplicate country-year rows found in upload.")

    return errors
