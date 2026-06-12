"""Gold-layer data loader with optional real-value deflation."""
from pathlib import Path
import pandas as pd
import numpy as np
import warnings


def _read_csv(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return pd.read_csv(p)


def load_panel(data_root='data/gold', start=2010, end=2024, deflator_metric=None):
    """Load gold-layer tables and return a cleaned panel dataframe.

    Pass deflator_metric to compute a 'real_value' column for currency series
    (base = first available year of the deflator at the national level).
    Returns (df, dim_metric, dim_region, fact_enriched).
    """
    data_root = Path(data_root)

    fact = _read_csv(data_root / 'fact_economic.csv')
    dim_metric = _read_csv(data_root / 'dim_metric.csv')
    dim_region = _read_csv(data_root / 'dim_region.csv')

    fact_enriched = fact.merge(dim_metric, on='metric_id', how='left')
    fact_enriched = fact_enriched.merge(dim_region, on='region_code', how='left')

    df = fact_enriched[['region_name', 'year', 'metric_code', 'value', 'unit']].copy()
    df = df[(df['year'] >= start) & (df['year'] <= end)]

    # only keep metrics present in the final year
    metrics_final = df[df['year'] == end]['metric_code'].unique()
    df = df[df['metric_code'].isin(metrics_final)]

    if deflator_metric is not None:
        defl = df[
            (df['metric_code'] == deflator_metric) &
            (df['region_name'] == 'Republic of Uzbekistan')
        ][['year', 'value']].drop_duplicates()

        if defl.empty:
            warnings.warn(f"Deflator metric '{deflator_metric}' not found. Returning nominal values.")
        else:
            defl = defl.set_index('year').sort_index()
            base = defl['value'].iloc[0]
            defl = defl['value'] / base
            df = df.merge(defl.rename('deflator_ratio'), left_on='year', right_index=True, how='left')
            mask_currency = df['unit'].str.contains('sum|uzs|soms|сум', case=False, na=False)
            df.loc[mask_currency & df['deflator_ratio'].notna(), 'real_value'] = (
                df.loc[mask_currency & df['deflator_ratio'].notna(), 'value'] /
                df.loc[mask_currency & df['deflator_ratio'].notna(), 'deflator_ratio']
            )

    return df, dim_metric, dim_region, fact_enriched


def pivot_national(df, region_name='Republic of Uzbekistan'):
    """Return a pivoted national time-series DataFrame (years × metric_code)."""
    nat = df[df['region_name'] == region_name]
    value_col = 'real_value' if 'real_value' in nat.columns else 'value'
    pivot = nat.pivot_table(index='year', columns='metric_code', values=value_col)
    return pivot
