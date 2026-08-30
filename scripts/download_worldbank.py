"""Download national and comparator series from the World Bank Open Data API.

Three things come from here that stat.uz does not publish.

Prices and population. Every stat.uz value series is at current prices and the
catalogue carries no usable price index, so without an external deflator every soum
figure in the warehouse is uninterpretable across time.

Depth. The World Bank series reach back to 1987, four years before independence,
which puts the 2017 reform inside the full post-Soviet arc rather than a 15-year
window.

Comparators. Nearly every figure in the World Bank Country Economic Update and
Systematic Country Diagnostic for Uzbekistan is drawn against peers. A growth rate on
its own is a number; the same rate against Kazakhstan and Vietnam is a finding. The
peer set is fetched in one request per indicator rather than one per country-indicator
pair, which is 13 calls instead of 169.
"""

import sys

# Windows consoles default to a legacy codepage (cp1251 here), which kills any
# print carrying a non-ASCII character. Force UTF-8 before anything prints.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import json
import logging
import os
import time

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "sources_worldbank.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "bronze", "worldbank")

API_ROOT = "https://api.worldbank.org/v2/country"
RETRIES = 3
BACKOFF = 3

os.makedirs(OUTPUT_PATH, exist_ok=True)


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch(entities, wb_code, start, end):
    """Return the API's rows for one indicator across one or more entities.

    `entities` is a semicolon-joined list of ISO3 codes, which the API accepts in a
    single request. Retried with a backoff: the World Bank endpoint times out often
    enough that a single failure should not lose an indicator.
    """
    url = f"{API_ROOT}/{entities}/indicator/{wb_code}"
    params = {"format": "json", "per_page": "20000", "date": f"{start}:{end}"}

    for attempt in range(RETRIES):
        try:
            response = requests.get(url, params=params, timeout=90)
            if response.status_code != 200:
                logging.warning(f"{wb_code}: HTTP {response.status_code}")
                time.sleep(BACKOFF)
                continue

            payload = response.json()
            # The API answers with [metadata, rows]; a bad code returns a
            # single-element list carrying a message rather than an HTTP error.
            if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
                return []
            return payload[1]
        except Exception as e:
            if attempt == RETRIES - 1:
                logging.error(f"{wb_code}: {type(e).__name__} after {RETRIES} attempts")
                return []
            time.sleep(BACKOFF)
    return []


def download_national(cfg):
    """The full indicator set for Uzbekistan, wide: one column per indicator."""
    country = cfg["country"]
    start, end = cfg["start_year"], cfg["end_year"]
    frames = {}

    for name, spec in cfg["indicators"].items():
        rows = fetch(country, spec["wb_code"], start, end)
        values = {int(r["date"]): r["value"] for r in rows if r["value"] is not None}

        if not values:
            logging.warning(f"{name} ({spec['wb_code']}): no data")
            continue

        frames[name] = pd.Series(values).sort_index()
        logging.info(f"{name}: {len(values)} years, {min(values)}-{max(values)}")

    if not frames:
        raise SystemExit("No World Bank national series downloaded; cannot continue.")

    combined = pd.DataFrame(frames)
    combined.index.name = "year"
    combined.to_csv(os.path.join(OUTPUT_PATH, "national_context.csv"))
    logging.info(f"national_context.csv: {len(combined)} years x {len(combined.columns)} indicators")
    return combined


def download_benchmark(cfg):
    """The comparator set, long: country x year x metric.

    Long rather than wide because the entity count is the thing that varies here,
    and a wide frame would need a column per country per indicator.
    """
    bench = cfg["benchmark"]
    entities = bench["countries"] + bench["aggregates"]
    joined = ";".join(entities)
    start, end = cfg["start_year"], cfg["end_year"]

    records = []
    for name, wb_code in bench["indicators"].items():
        rows = fetch(joined, wb_code, start, end)
        kept = 0

        for r in rows:
            if r["value"] is None:
                continue
            records.append({
                "country_code": r["countryiso3code"] or r["country"]["id"],
                "country_name": r["country"]["value"],
                "year": int(r["date"]),
                "metric_code": name,
                "value": r["value"],
            })
            kept += 1

        logging.info(f"{name}: {kept} observations across {len(entities)} entities")

    if not records:
        logging.warning("No benchmark data downloaded; peer comparisons will be empty.")
        return pd.DataFrame()

    df = pd.DataFrame(records).sort_values(["metric_code", "country_code", "year"])
    df.to_csv(os.path.join(OUTPUT_PATH, "benchmark.csv"), index=False)

    logging.info(f"benchmark.csv: {len(df):,} rows, "
                 f"{df.country_code.nunique()} entities, {df.metric_code.nunique()} indicators")
    return df


def main():
    cfg = load_config()
    logging.info(f"Downloading {len(cfg['indicators'])} national indicators for {cfg['country']}...")
    download_national(cfg)

    bench = cfg["benchmark"]
    logging.info(f"Downloading {len(bench['indicators'])} indicators for "
                 f"{len(bench['countries'])} peers + {len(bench['aggregates'])} aggregates...")
    download_benchmark(cfg)


if __name__ == "__main__":
    main()
