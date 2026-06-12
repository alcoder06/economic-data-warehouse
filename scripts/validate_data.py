import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold")


def load_gold_table(filename: str) -> pd.DataFrame:
    path = os.path.join(GOLD_PATH, filename)
    return pd.read_csv(path)


def main() -> None:
    print("Running gold-layer validation...")

    dim_region = load_gold_table("dim_region.csv")
    dim_metric = load_gold_table("dim_metric.csv")
    fact = load_gold_table("fact_economic.csv")

    print(f"dim_region rows: {len(dim_region)}")
    print(f"dim_metric rows: {len(dim_metric)}")
    print(f"fact_economic rows: {len(fact)}")

    missing_region = fact[~fact["region_code"].isin(dim_region["region_code"])]["region_code"].unique()
    missing_metric = fact[~fact["metric_id"].isin(dim_metric["metric_id"])]["metric_id"].unique()

    print("\nReferential integrity checks:")
    print(f"  missing region_code values: {len(missing_region)}")
    print(f"  missing metric_id values: {len(missing_metric)}")

    duplicate_count = fact.duplicated(subset=["region_code", "year", "metric_id"]).sum()
    print(f"\nDuplicate fact rows: {duplicate_count}")

    null_counts = fact.isnull().sum()
    print("\nNull counts in fact_economic:")
    print(null_counts)

    year_range = fact["year"].agg(["min", "max"]).to_dict()
    region_count = fact["region_code"].nunique()
    metric_count = fact["metric_id"].nunique()

    print("\nFact summary:")
    print(f"  year range: {year_range['min']} to {year_range['max']}")
    print(f"  distinct regions: {region_count}")
    print(f"  distinct metrics: {metric_count}")

    coverage = fact.groupby(["year", "metric_id"])["region_code"].nunique().describe()
    print("\nRegion coverage per year-metric group:")
    print(coverage)

    print("\nValidation completed.")


if __name__ == "__main__":
    main()
