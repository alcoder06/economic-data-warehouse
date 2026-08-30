"""Regional inequality and convergence measures.

Two families of measure live here and they answer different questions.

Inequality measures (Gini, log dispersion) describe the spread of the distribution
in a single year. Convergence measures (beta, sigma) describe whether that spread is
closing, and beta additionally says whether the closing is being driven by poorer
regions catching up rather than by richer ones falling back.

Every one of them is sensitive to what you feed it. A Gini on regional GDP levels is
substantially a measure of which regions are populous, and a Gini on nominal values
is partly a measure of the price level. The functions here take whatever series you
pass, so the choice of `real_value_per_capita` over `value` is the caller's to make
and the one that decides whether the answer means anything.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm


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


def gini_over_time(regional_pivot):
    """Gini coefficient for each year from a regional pivot (index=year, columns=regions)."""
    return pd.DataFrame(
        [{"year": year, "gini_coefficient": gini(regional_pivot.loc[year].dropna().values)}
         for year in regional_pivot.index]
    ).set_index("year")


def sigma_convergence(regional_pivot):
    """Standard deviation of log values per year.

    Sigma-convergence is the plain question: is the cross-regional spread shrinking?
    Logs are used so the measure is scale-free and a doubling counts the same at
    every income level. A falling series means regions are becoming more alike.
    """
    return pd.DataFrame(
        [{"year": year, "log_sd": np.log(regional_pivot.loc[year].dropna()).std()}
         for year in regional_pivot.index]
    ).set_index("year")


def beta_convergence(regional_pivot, start, end):
    """Regress average annual growth on initial level (Barro and Sala-i-Martin).

    Fits  (1/T) * ln(y_end / y_start)  =  a + b * ln(y_start)

    A negative and significant b is beta-convergence: regions that started poorer
    grew faster, so the distribution is closing from below. A positive b is
    divergence, with the already-rich pulling away.

    Beta and sigma can disagree, and when they do beta is the more informative of
    the two: catch-up growth can be happening while one-off shocks widen the spread.
    Returns the fitted statsmodels result plus the frame it was fitted on, so the
    caller can run diagnostics or plot the scatter.
    """
    y_start = regional_pivot.loc[start].dropna()
    y_end = regional_pivot.loc[end].dropna()
    common = y_start.index.intersection(y_end.index)

    if len(common) < 5:
        raise ValueError(f"Only {len(common)} regions present in both {start} and {end}")

    data = pd.DataFrame({
        "log_initial": np.log(y_start[common]),
        "growth": np.log(y_end[common] / y_start[common]) / (end - start),
    })

    model = sm.OLS(data["growth"], sm.add_constant(data[["log_initial"]])).fit()
    return model, data


def convergence_summary(regional_pivot, periods):
    """Run beta_convergence over several sub-periods and tabulate the verdicts.

    Splitting the sample is not optional here. Over 2010-2024 as a whole the
    coefficient is insignificant, which reads as "nothing happening". It is actually
    a sign reversal: significant convergence up to 2016 and significant divergence
    after it, averaging out to nothing when the two regimes are pooled.
    """
    rows = []
    for label, (start, end) in periods.items():
        model, _ = beta_convergence(regional_pivot, start, end)
        beta = model.params["log_initial"]
        pval = model.pvalues["log_initial"]

        if pval >= 0.05:
            verdict = "no significant relationship"
        else:
            verdict = "convergence" if beta < 0 else "divergence"

        rows.append({
            "period": label, "start": start, "end": end,
            "beta": beta, "p_value": pval, "r_squared": model.rsquared,
            "n_regions": int(model.nobs), "verdict": verdict,
        })

    return pd.DataFrame(rows).set_index("period")


def compute_productivity(df, value_col="real_value"):
    """Output per economically active person, by region and year.

    Defaults to the deflated series. On nominal values this measure mostly tracks
    the price level: soum output per worker rose 17x over 2010-2024 without anyone
    becoming seventeen times more productive.
    """
    gdp = df[df["metric_code"] == "regional_gdp"]
    labor = df[df["metric_code"] == "economically_active_population"]

    col = value_col if value_col in df.columns else "value"
    gdp_pivot = gdp.pivot_table(index="year", columns="region_name", values=col)
    labor_pivot = labor.pivot_table(index="year", columns="region_name", values="value")

    common_years = gdp_pivot.index.intersection(labor_pivot.index)
    return gdp_pivot.loc[common_years] / labor_pivot.loc[common_years]


def compute_regional_shares(regional_pivot, national_series):
    """Regional shares as percent of national total (regions x years)."""
    return regional_pivot.div(national_series, axis=0).mul(100).T
