import pandas as pd
import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

METADATA_PATH = os.path.join(BASE_DIR, "config", "metadata.json")
SILVER_PATH = os.path.join(BASE_DIR, "data", "silver")
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold")

os.makedirs(GOLD_PATH, exist_ok=True)


def create_dim_region():
    print("Creating dim_region...")

    region_frames = []
    for file in os.listdir(SILVER_PATH):
        if not file.endswith(".csv"):
            continue

        df = pd.read_csv(os.path.join(SILVER_PATH, file))
        if "region_code" in df.columns and "region_name" in df.columns:
            region_frames.append(df[["region_code", "region_name"]])

    if not region_frames:
        print("No region data found.")
        return

    dim_region = pd.concat(region_frames)
    dim_region = dim_region.drop_duplicates().sort_values("region_code").reset_index(drop=True)
    dim_region.to_csv(os.path.join(GOLD_PATH, "dim_region.csv"), index=False)
    print("dim_region done.")


def create_dim_metric():
    print("Creating dim_metric...")

    with open(METADATA_PATH, "r") as f:
        metadata = json.load(f)

    records = []
    for idx, metric_code in enumerate(sorted(metadata.keys()), start=1):
        records.append({
            "metric_id": idx,
            "metric_code": metric_code,
            "metric_name": metric_code.replace("_", " ").title(),
            "unit": metadata[metric_code].get("unit")
        })

    pd.DataFrame(records).to_csv(os.path.join(GOLD_PATH, "dim_metric.csv"), index=False)
    print("dim_metric done.")


def create_fact_economic():
    print("Creating fact_economic...")

    dim_metric = pd.read_csv(os.path.join(GOLD_PATH, "dim_metric.csv"))
    fact_frames = []

    for file in os.listdir(SILVER_PATH):
        if not file.endswith(".csv"):
            continue

        df = pd.read_csv(os.path.join(SILVER_PATH, file))
        metric_code = file.replace(".csv", "")
        metric_row = dim_metric[dim_metric["metric_code"] == metric_code]
        if metric_row.empty:
            print(f"Skipping {metric_code}, metric not found.")
            continue

        year_columns = [col for col in df.columns if col.isdigit()]
        if not year_columns:
            continue

        df_long = df.melt(
            id_vars=["region_code"],
            value_vars=year_columns,
            var_name="year",
            value_name="value"
        )
        df_long["metric_id"] = int(metric_row["metric_id"].iloc[0])
        fact_frames.append(df_long)

    if not fact_frames:
        print("No fact data created.")
        return

    fact_economic = pd.concat(fact_frames)
    fact_economic["year"] = fact_economic["year"].astype(int)
    fact_economic["value"] = pd.to_numeric(fact_economic["value"], errors="coerce")
    fact_economic = fact_economic.dropna().drop_duplicates()
    fact_economic = fact_economic[["region_code", "year", "metric_id", "value"]]
    fact_economic.to_csv(os.path.join(GOLD_PATH, "fact_economic.csv"), index=False)

    dup = fact_economic.duplicated(subset=["region_code", "year", "metric_id"]).sum()
    print(f"fact_economic done. duplicate rows: {dup}")


if __name__ == "__main__":
    create_dim_region()
    create_dim_metric()
    create_fact_economic()
