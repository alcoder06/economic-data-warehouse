"""ARIMA forecasting with 95% prediction intervals and Monte Carlo Gini simulation."""
from pathlib import Path
import numpy as np
import pandas as pd
import warnings
from statsmodels.tsa.arima.model import ARIMA
import matplotlib.pyplot as plt


def select_arima_order(series, p_max=2, d_values=(0, 1), q_max=2):
    """Grid-search (p,d,q) by AIC over the given ranges."""
    best_aic = np.inf
    best_order = None
    for d in d_values:
        for p in range(p_max + 1):
            for q in range(q_max + 1):
                try:
                    model = ARIMA(series, order=(p, d, q)).fit()
                    if model.aic < best_aic:
                        best_aic = model.aic
                        best_order = (p, d, q)
                except Exception:
                    continue
    if best_order is None:
        raise RuntimeError('No ARIMA model could be fit for this series')
    return best_order


def forecast_series(series, steps=6, order=None):
    """Fit ARIMA and return a DataFrame with columns: mean, lower, upper."""
    series = series.dropna()
    if order is None:
        order = select_arima_order(series)

    model = ARIMA(series, order=order).fit()
    fc = model.get_forecast(steps=steps)
    mean = fc.predicted_mean
    ci = fc.conf_int(alpha=0.05)
    years = np.arange(series.index.max() + 1, series.index.max() + 1 + steps)
    df = pd.DataFrame({
        'year': years,
        'mean': mean.values.flatten(),
        'lower': ci.iloc[:, 0].values.flatten(),
        'upper': ci.iloc[:, 1].values.flatten(),
    }).set_index('year')
    return df, model


def forecast_regions_and_gini(regional_df, steps=6, sims=500):
    """Forecast each region's series with ARIMA, then simulate Gini intervals via Monte Carlo.

    regional_df: DataFrame indexed by year, columns are region names.
    Returns (regional_forecast_df, gini_forecast_df) where gini_forecast_df
    has columns mean, lower, upper indexed by forecast year.
    """
    years = np.arange(regional_df.index.max() + 1, regional_df.index.max() + 1 + steps)
    regions = regional_df.columns

    point_forecasts = pd.DataFrame(index=years, columns=regions, dtype=float)
    ci_lower = pd.DataFrame(index=years, columns=regions, dtype=float)
    ci_upper = pd.DataFrame(index=years, columns=regions, dtype=float)

    for region in regions:
        series = regional_df[region].dropna()
        if len(series) < 6:
            warnings.warn(f'Not enough data for region {region}; using last observed value')
            point_forecasts[region] = series.iloc[-1]
            ci_lower[region] = series.iloc[-1]
            ci_upper[region] = series.iloc[-1]
            continue
        try:
            order = select_arima_order(series)
            model = ARIMA(series, order=order).fit()
            fc = model.get_forecast(steps=steps)
            mean = fc.predicted_mean
            ci = fc.conf_int(alpha=0.05)
            point_forecasts[region] = mean.values.flatten()
            ci_lower[region] = ci.iloc[:, 0].values.flatten()
            ci_upper[region] = ci.iloc[:, 1].values.flatten()
        except Exception:
            # fallback: hold last value
            last = series.iloc[-1]
            point_forecasts[region] = last
            ci_lower[region] = last
            ci_upper[region] = last

    # Monte Carlo: sample region values from their forecast distributions, compute Gini each draw
    gini_sims = np.zeros((sims, steps))
    for sim in range(sims):
        sim_vals = np.zeros((steps, len(regions)))
        for i, region in enumerate(regions):
            mu = point_forecasts[region].values
            # approximate std from half-width of 95% CI
            std = (ci_upper[region].values - ci_lower[region].values) / (2 * 1.96)
            std = np.where(std <= 0, 1e-6, std)
            draws = np.clip(np.random.normal(mu, std), 0, None)
            sim_vals[:, i] = draws
        for t in range(steps):
            arr = np.sort(sim_vals[t, :])
            n = len(arr)
            if arr.sum() == 0:
                gini_sims[sim, t] = 0
            else:
                index = np.arange(1, n + 1)
                gini_sims[sim, t] = (2 * np.sum(index * arr)) / (n * np.sum(arr)) - (n + 1) / n

    gini_df = pd.DataFrame({
        'year': years,
        'mean': gini_sims.mean(axis=0),
        'lower': np.percentile(gini_sims, 2.5, axis=0),
        'upper': np.percentile(gini_sims, 97.5, axis=0),
    }).set_index('year')

    point_forecasts.index.name = 'year'
    return point_forecasts, gini_df


def plot_forecast_with_ci(actual_series, forecast_df, title='', ylabel='', out_path=None):
    """Plot actual series + forecast mean with shaded 95% CI band."""
    plt.figure(figsize=(8, 4))
    plt.plot(actual_series.index, actual_series.values, marker='o', label='Actual')
    plt.plot(forecast_df.index, forecast_df['mean'], marker='o', linestyle='--', label='Forecast')
    plt.fill_between(forecast_df.index, forecast_df['lower'], forecast_df['upper'],
                     color='gray', alpha=0.3, label='95% CI')
    plt.axvline(actual_series.index.max(), linestyle=':', color='k')
    plt.xlabel('Year')
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_path)
    plt.show()
