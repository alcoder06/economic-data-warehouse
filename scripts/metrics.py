"""Reusable metric computations: Gini, productivity, regional shares."""
import numpy as np
import pandas as pd


def gini(array):
    """Gini coefficient for a 1-D array (ignores negatives)."""
    arr = np.array(array, dtype=float)
    arr = arr[arr >= 0]
    if len(arr) == 0 or arr.sum() == 0:
        return np.nan
    arr = np.sort(arr)
    n = len(arr)
    index = np.arange(1, n + 1)
    return (2 * np.sum(index * arr)) / (n * np.sum(arr)) - (n + 1) / n


def compute_productivity(df):
    """GDP per economically active person by region and year.

    df must contain metric_codes 'regional_gdp' and 'economically_active_population'.
    Returns a pivot table indexed by year with regions as columns.
    """
    gdp = df[df['metric_code'] == 'regional_gdp']
    labor = df[df['metric_code'] == 'economically_active_population']

    gdp_pivot = gdp.pivot_table(index='year', columns='region_name', values='value')
    labor_pivot = labor.pivot_table(index='year', columns='region_name', values='value')

    common_years = gdp_pivot.index.intersection(labor_pivot.index)
    return gdp_pivot.loc[common_years] / labor_pivot.loc[common_years]


def compute_regional_shares(regional_pivot, national_series):
    """Regional shares as percent of national total (regions × years).

    regional_pivot: DataFrame index=year, columns=regions.
    national_series: Series indexed by year.
    """
    shares = regional_pivot.div(national_series, axis=0) * 100
    return shares.T


def gini_over_time(regional_pivot):
    """Gini coefficient for each year from a regional pivot (year × region)."""
    results = [
        {'year': year, 'gini_coefficient': gini(regional_pivot.loc[year].values)}
        for year in regional_pivot.index
    ]
    return pd.DataFrame(results).set_index('year')
