"""Gold-layer loader.

Real-terms and per-capita conversion used to happen here, at analysis time. It now
happens once in gold_transform.py and lands in the fact table, so this module only
joins and filters. Anything that has to be true of every consumer of the data
belongs upstream of all of them.

The earlier version also dropped any metric with no observation in the final year,
silently. That removed consumer_goods_output, whose series ends in 2022, without
anything in the output saying so. Trimming ragged series is now opt-in and it warns.
"""
import warnings
from pathlib import Path

import pandas as pd

DEFAULT_START = 2010
DEFAULT_END = 2025


def _read_csv(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Missing file: {path}. Run `python scripts/main_pipeline.py --steps all` first."
        )
    return pd.read_csv(p)


def load_panel(
    data_root="data/gold",
    start=DEFAULT_START,
    end=DEFAULT_END,
    grain=None,
    require_final_year=False,
):
    """Load the gold layer and return (df, dim_metric, dim_region, dim_year).

    Parameters
    ----------
    grain : 'regional', 'national' or None
        The stat.uz series carry all fourteen regions but begin in 2010; the World
        Bank series are national only and reach back to 1987. Filter to one of them
        when a chart cannot honestly mix the two.
    require_final_year : bool
        Drop metrics with no observation in `end`. Off by default, and it warns
        about what it removed when switched on.
    """
    root = Path(data_root)

    fact = _read_csv(root / "fact_economic.csv")
    dim_metric = _read_csv(root / "dim_metric.csv")
    dim_region = _read_csv(root / "dim_region.csv")
    dim_year = _read_csv(root / "dim_year.csv")

    df = (
        fact.merge(dim_metric, on="metric_id", how="left")
            .merge(dim_region, on="region_code", how="left")
            .merge(dim_year, on="year", how="left")
    )

    df = df[(df["year"] >= start) & (df["year"] <= end)]

    if grain is not None:
        df = df[df["grain"] == grain]

    if require_final_year:
        present = set(df.loc[df["year"] == end, "metric_code"])
        dropped = sorted(set(df["metric_code"]) - present)
        if dropped:
            warnings.warn(
                f"Dropping {len(dropped)} metric(s) with no observation in {end}: "
                f"{', '.join(dropped)}"
            )
        df = df[df["metric_code"].isin(present)]

    return df, dim_metric, dim_region, dim_year


def pivot_national(df, value_col="real_value", region_name="Republic of Uzbekistan"):
    """National time series, years x metric_code.

    Defaults to the deflated column. Pass value_col='value' only when the nominal
    figure is what is actually wanted, which is rarer than it looks: comparing two
    soum figures from different years compares two different soums.
    """
    nat = df[df["region_name"] == region_name]
    col = value_col if value_col in nat.columns and nat[value_col].notna().any() else "value"
    return nat.pivot_table(index="year", columns="metric_code", values=col)


def pivot_regional(df, metric_code, value_col="real_value_per_capita", exclude_national=True):
    """One metric across regions, years x region.

    Excludes the Republic total by default. region_code 1700 sits in the same column
    as the fourteen regions that sum to it, so leaving it in double-counts every
    total and makes every inequality measure wrong.
    """
    sub = df[df["metric_code"] == metric_code]
    if exclude_national:
        sub = sub[~sub["is_national"]]

    col = value_col if value_col in sub.columns and sub[value_col].notna().any() else "value"
    return sub.pivot_table(index="year", columns="region_short", values=col)
