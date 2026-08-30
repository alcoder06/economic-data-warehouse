"""Download and parse the stat.uz indicator metadata sheets into a data dictionary.

Each SDMX dataset ships an .xlsx whose second sheet is a metadata card: official
indicator code, full name, unit, periodicity, methodology link and the compiler's
notes. The earlier version of this script read one field out of that card and
discarded the rest.

The unit string is the important one, and not only for labelling. stat.uz writes
"at current prices, billion soums" for every soum-denominated series, which is the
flag that says the series is nominal and has to be deflated before it can be
compared across years. That string is parsed here into a `price_basis` field the
gold layer keys its real-terms conversion off.
"""

import sys

# Windows consoles default to a legacy codepage (cp1251 here), which kills any
# print carrying a non-ASCII character. Force UTF-8 before anything prints.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import json
import os
import re

import pandas as pd
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(BASE_DIR, "config", "sources.json")
METADATA_OUTPUT_PATH = os.path.join(BASE_DIR, "config", "metadata.json")
METADATA_RAW_PATH = os.path.join(BASE_DIR, "data", "metadata_raw")

os.makedirs(METADATA_RAW_PATH, exist_ok=True)

# Metadata-card row labels, as they appear in the English column, mapped to our field names.
FIELD_LABELS = {
    "indicator name": "indicator_name",
    "identification": "official_code",
    "unit of measurement": "unit_raw",
    "periodicity": "periodicity",
    "calculation methodology": "methodology_url",
    "official statistics preparer": "preparer",
    "name of department": "department",
    "last modified date": "last_modified",
    "date of first publication": "first_published",
    "note": "notes",
    "classifiers": "classifiers",
}

CURRENCY_TOKENS = ("soum", "sum", "uzs")


def load_sources():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_unit(unit_raw):
    """Map a raw unit string from the source API to a canonical label."""
    if not unit_raw:
        return None

    unit = unit_raw.strip().lower()

    if "billion" in unit and any(t in unit for t in CURRENCY_TOKENS):
        return "billion UZS"
    if "million" in unit and any(t in unit for t in CURRENCY_TOKENS):
        return "million UZS"
    if "thousand" in unit and any(t in unit for t in CURRENCY_TOKENS):
        return "thousand UZS"
    if "usd" in unit:
        return "million USD"
    if "kw" in unit:
        return "million kWh"
    if "ton" in unit:
        return "thousand tons"
    if "percent" in unit or unit.strip() == "%":
        return "%"
    if "thousand" in unit and ("people" in unit or "person" in unit):
        return "thousand persons"
    if "person" in unit or "people" in unit:
        return "persons"
    if "unit" in unit:
        return "units"

    return unit_raw.strip()


def classify_price_basis(unit_raw):
    """Return 'current', 'constant' or 'not applicable' for a raw unit string.

    Anything measured in soums and not explicitly marked constant is treated as
    current-price, which is how stat.uz publishes its value series.
    """
    if not unit_raw:
        return "unknown"

    unit = unit_raw.lower()
    is_currency = any(t in unit for t in CURRENCY_TOKENS) or "usd" in unit

    if not is_currency:
        return "not applicable"
    if "constant" in unit or "comparable" in unit:
        return "constant"
    return "current"


def download_xlsx(indicator_name, csv_url):
    xlsx_url = csv_url.replace(".csv", ".xlsx")
    print(f"Downloading metadata for {indicator_name}...")

    response = requests.get(xlsx_url, timeout=60)

    if response.status_code != 200:
        print(f"  failed: HTTP {response.status_code}")
        return None

    file_path = os.path.join(METADATA_RAW_PATH, f"{indicator_name}.xlsx")
    with open(file_path, "wb") as f:
        f.write(response.content)
    return file_path


def parse_metadata_card(file_path):
    """Read the metadata sheet and return the fields named in FIELD_LABELS.

    Rows are label/value pairs rather than a table, and a card may repeat a label
    (notably 'Note'), so repeated values are collected into a list.
    """
    try:
        df = pd.read_excel(file_path, sheet_name=1, engine="openpyxl")
    except Exception as e:
        print(f"  error reading {file_path}: {e}")
        return {}

    df.columns = df.columns.str.strip().str.lower()
    if "name_en" not in df.columns or "value_en" not in df.columns:
        print(f"  metadata columns not found in {file_path}")
        return {}

    collected = {}
    for _, row in df.iterrows():
        label = str(row["name_en"]).strip().lower()
        value = str(row["value_en"]).strip()

        if not value or value.lower() == "nan":
            continue

        for needle, field in FIELD_LABELS.items():
            if needle in label:
                collected.setdefault(field, []).append(value)
                break

    # Collapse single-valued fields; keep notes as a list since cards carry several.
    result = {}
    for field, values in collected.items():
        deduped = list(dict.fromkeys(values))
        result[field] = deduped if field == "notes" else deduped[0]

    return result


def main():
    sources = load_sources()
    metadata_dict = {}

    for indicator, csv_url in sources.items():
        xlsx_path = download_xlsx(indicator, csv_url)
        if not xlsx_path:
            continue

        card = parse_metadata_card(xlsx_path)
        unit_raw = card.get("unit_raw")

        # A handful of cards ship an empty English name; fall back to the config key.
        name = card.get("indicator_name") or indicator.replace("_", " ").capitalize()

        metadata_dict[indicator] = {
            "indicator_name": name,
            "official_code": card.get("official_code"),
            "unit": normalize_unit(unit_raw),
            "unit_raw": unit_raw,
            "price_basis": classify_price_basis(unit_raw),
            "periodicity": card.get("periodicity"),
            "source": "stat.uz",
            "source_id": re.search(r"sdmx_data_(\d+)", csv_url).group(1),
            "methodology_url": card.get("methodology_url"),
            "department": card.get("department"),
            "last_modified": card.get("last_modified"),
            "notes": card.get("notes", []),
        }

    with open(METADATA_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata_dict, f, indent=4, ensure_ascii=False)

    current = [k for k, v in metadata_dict.items() if v["price_basis"] == "current"]
    print(f"\nMetadata written for {len(metadata_dict)} indicators.")
    print(f"{len(current)} are published at current prices and require deflation:")
    for k in current:
        print(f"  {k} ({metadata_dict[k]['unit']})")


if __name__ == "__main__":
    main()
