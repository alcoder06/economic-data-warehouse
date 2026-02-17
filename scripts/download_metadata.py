import os
import json
import requests
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(BASE_DIR, "config", "sources.json")
METADATA_OUTPUT_PATH = os.path.join(BASE_DIR, "config", "metadata.json")
METADATA_RAW_PATH = os.path.join(BASE_DIR, "data", "metadata_raw")

os.makedirs(METADATA_RAW_PATH, exist_ok=True)


def load_sources():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def normalize_unit(unit_raw):
    """
    Standardizes unit names.
    """
    if not unit_raw:
        return None

    unit = unit_raw.strip().lower()

    # Currency normalization
    if "billion" in unit and "soum" in unit:
        return "billion UZS"
    if "million" in unit and "soum" in unit:
        return "million UZS"
    if "thousand" in unit and "soum" in unit:
        return "thousand UZS"

    # USD
    if "usd" in unit:
        return "million USD"

    # Electricity
    if "kw" in unit:
        return "million kWh"

    # Tons
    if "ton" in unit:
        return "thousand tons"

    # Percent
    if "percent" in unit:
        return "%"

    # People / persons
    if "thousand" in unit and "people" in unit:
        return "thousand persons"
    if "person" in unit:
        return "persons"

    # Units count
    if "unit" in unit:
        return "units"

    return unit_raw.strip()


def download_xlsx(indicator_name, csv_url):
    xlsx_url = csv_url.replace(".csv", ".xlsx")

    print(f"Downloading metadata for {indicator_name}...")

    response = requests.get(xlsx_url)

    if response.status_code == 200:
        file_path = os.path.join(METADATA_RAW_PATH, f"{indicator_name}.xlsx")
        with open(file_path, "wb") as f:
            f.write(response.content)
        return file_path
    else:
        print(f"Failed to download {indicator_name}")
        return None


def extract_unit_from_xlsx(file_path):
    try:
        df = pd.read_excel(file_path, sheet_name=1, engine="openpyxl")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

    df.columns = df.columns.str.strip().str.lower()

    if "name_en" not in df.columns or "value_en" not in df.columns:
        print(f"Metadata columns not found in {file_path}")
        return None

    unit_row = df[df["name_en"].astype(str).str.contains("unit", case=False, na=False)]

    if unit_row.empty:
        print(f"No unit row found in {file_path}")
        return None

    full_text = str(unit_row["value_en"].values[0]).strip()

    if "," in full_text:
        raw_unit = full_text.split(",")[-1].strip()
    else:
        raw_unit = full_text

    return normalize_unit(raw_unit)


def main():
    sources = load_sources()
    metadata_dict = {}

    for indicator, csv_url in sources.items():
        xlsx_path = download_xlsx(indicator, csv_url)

        if xlsx_path:
            unit = extract_unit_from_xlsx(xlsx_path)

            metadata_dict[indicator] = {
                "unit": unit
            }

    with open(METADATA_OUTPUT_PATH, "w") as f:
        json.dump(metadata_dict, f, indent=4)

    print("Metadata extraction and normalization completed.")


if __name__ == "__main__":
    main()
