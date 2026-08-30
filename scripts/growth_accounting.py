"""Growth accounting, investment efficiency and structural change.

These are the diagnostics the IMF and the World Bank apply to Uzbekistan, computed
here from public data so the result can be checked rather than cited.

Four calculations:

**Capital stock**, by the perpetual inventory method. Uzbekistan publishes an
investment flow, not a stock, so the stock has to be accumulated:
K(t) = (1-d)K(t-1) + I(t), initialised at the steady state K(0) = I(0)/(g+d).
Both the depreciation rate and the initialisation are assumptions, which is why the
Solow decomposition below is reported across a range of them rather than at a point.

**Solow decomposition.** With a Cobb-Douglas production function Y = A K^a L^(1-a),
growth in output splits into a weighted sum of growth in capital and labour plus a
residual. The residual is total factor productivity: whatever the measured inputs do
not explain. It is not a measurement of technology so much as a measurement of our
ignorance, and it is the single number the World Bank Country Economic Memorandum
(2025) calls "central" to Uzbekistan reaching upper-middle-income status.

**Incremental capital-output ratio.** How many units of investment buy one unit of
extra output. Rising ICOR means the same growth costs more capital each year. The
World Bank's Systematic Country Diagnostic charts this for Uzbekistan directly
(Figure 31).

**Shift-share.** Whether labour productivity rose because sectors got more productive
(within) or because workers moved to more productive sectors (between). The SCD's
finding is "limited intersectoral shifts in employment from less to more productive
sectors", which is a claim this decomposition can test.
"""

import sys

# Windows consoles default to a legacy codepage (cp1251 here), which kills any
# print carrying a non-ASCII character. Force UTF-8 before anything prints.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd

# Capital share of income. 0.35 is the conventional value for a developing economy
# and the one the IMF uses for Uzbekistan; the sensitivity band spans plausible
# alternatives rather than asserting a single figure.
ALPHA_DEFAULT = 0.35
ALPHA_RANGE = (0.30, 0.40)

# Annual depreciation of the capital stock.
DELTA_DEFAULT = 0.05
DELTA_RANGE = (0.04, 0.07)

SECTORS = {
    "Agriculture": ("wb_agriculture_pct_gdp", "wb_employment_agriculture_pct"),
    "Industry":    ("wb_industry_pct_gdp",    "wb_employment_industry_pct"),
    "Services":    ("wb_services_pct_gdp",    "wb_employment_services_pct"),
}


def capital_stock(investment, output, delta=DELTA_DEFAULT):
    """Accumulate a capital stock from an investment flow.

    Initialised at the steady state implied by the series' own average growth, which
    is the standard treatment when no benchmark stock is published. The first years
    of the resulting series are the least trustworthy, since they carry the most of
    that assumption; by construction the influence decays at (1-delta) per year.
    """
    investment = investment.dropna().sort_index()
    output = output.reindex(investment.index)

    g = np.log(output.iloc[-1] / output.iloc[0]) / (len(output) - 1)
    k0 = investment.iloc[0] / (g + delta)

    stock = [k0]
    for t in range(1, len(investment)):
        stock.append((1 - delta) * stock[-1] + investment.iloc[t])

    return pd.Series(stock, index=investment.index, name="capital_stock")


def solow_decomposition(output, capital, labour, alpha=ALPHA_DEFAULT):
    """Split output growth into capital, labour and residual TFP contributions.

    Returns percentage-point contributions that sum to the growth rate. Log
    differences rather than percentage changes, so the parts add exactly instead of
    approximately.
    """
    years = output.index.intersection(capital.index).intersection(labour.index)
    y, k, l = output[years], capital[years], labour[years]

    d_y, d_k, d_l = np.log(y).diff(), np.log(k).diff(), np.log(l).diff()

    return pd.DataFrame({
        "real_growth_pct":  d_y * 100,
        "capital_contrib":  alpha * d_k * 100,
        "labour_contrib":   (1 - alpha) * d_l * 100,
        "tfp_contrib":      (d_y - alpha * d_k - (1 - alpha) * d_l) * 100,
    }).dropna()


def solow_sensitivity(output, investment, labour,
                      alphas=ALPHA_RANGE, deltas=DELTA_RANGE):
    """TFP contribution across the plausible range of alpha and delta.

    The point of publishing this alongside the headline decomposition is that a TFP
    residual is only as solid as the assumptions behind the capital stock, and a
    reader is entitled to see how far the answer moves when they are varied.
    """
    rows = []
    for alpha in alphas:
        for delta in deltas:
            k = capital_stock(investment, output, delta=delta)
            dec = solow_decomposition(output, k, labour, alpha=alpha)
            rows.append({
                "alpha": alpha,
                "delta": delta,
                "mean_tfp_contrib": dec["tfp_contrib"].mean(),
                "mean_capital_contrib": dec["capital_contrib"].mean(),
                "tfp_share_of_growth": dec["tfp_contrib"].mean() / dec["real_growth_pct"].mean(),
            })
    return pd.DataFrame(rows)


def incremental_capital_output_ratio(investment, output):
    """Units of investment per unit of extra output.

    The lag on the investment rate matters: this year's growth is bought with last
    year's capital, and pairing them contemporaneously understates the ratio in any
    year when investment is accelerating.

    A near-zero growth rate sends the ratio to infinity and a negative one makes it
    negative, and neither is a sensible reading of "capital per unit of extra
    output". Those years are flagged rather than dropped: a pandemic and a
    transition recession are real reasons for capital to buy no growth, and removing
    them silently would flatter the series.
    """
    inv_rate = (investment / output)
    growth = output.pct_change()

    df = pd.DataFrame({
        "investment_pct_gdp": inv_rate * 100,
        "real_growth_pct": growth * 100,
        "icor": inv_rate.shift(1) / growth,
    })
    df["is_outlier"] = (df["real_growth_pct"] < 2.0)
    return df.dropna(subset=["icor"])


def growth_contributions_by_sector(real_gdp, sector_shares):
    """Percentage-point contribution of each sector to real GDP growth.

    contribution(i) = change in (share(i) x real GDP) / real GDP(t-1)

    Contributions sum exactly to the growth rate, which is why this is the chart the
    World Bank Country Economic Update opens with rather than a panel of sector
    growth rates: it answers where growth came from, not merely which sector grew.
    """
    va = sector_shares.div(100).mul(real_gdp, axis=0).dropna()
    prev = real_gdp.reindex(va.index).shift(1)
    contrib = va.diff().div(prev, axis=0) * 100
    contrib["total_growth_pct"] = contrib.sum(axis=1)
    return contrib.dropna()


def shift_share(productivity, employment_share, start, end):
    """Decompose aggregate productivity growth into within, between and interaction.

    within      = sum over sectors of  s(i,0) * (p(i,1) - p(i,0))
    between     = sum over sectors of  (s(i,1) - s(i,0)) * p(i,0)
    interaction = sum over sectors of  (s(i,1) - s(i,0)) * (p(i,1) - p(i,0))

    A large `within` and a near-zero `between` means sectors are improving but labour
    is not moving to where output per worker is higher — which is structural change
    failing to happen, and is exactly what the World Bank reports for Uzbekistan.
    """
    p0, p1 = productivity.loc[start], productivity.loc[end]
    s0, s1 = employment_share.loc[start], employment_share.loc[end]

    sectors = p0.dropna().index.intersection(p1.dropna().index)
    p0, p1, s0, s1 = p0[sectors], p1[sectors], s0[sectors], s1[sectors]
    s0, s1 = s0 / s0.sum(), s1 / s1.sum()

    base = (s0 * p0).sum()
    within = (s0 * (p1 - p0)).sum()
    between = ((s1 - s0) * p0).sum()
    interaction = ((s1 - s0) * (p1 - p0)).sum()

    return {
        "start_year": start, "end_year": end,
        "total_pct": (within + between + interaction) / base * 100,
        "within_pct": within / base * 100,
        "between_pct": between / base * 100,
        "interaction_pct": interaction / base * 100,
    }


def employed_persons(population, dependency_ratio, participation_pct, unemployment_pct):
    """Reconstruct the number of people in work from World Bank ratios.

    The API publishes participation and unemployment as rates and the age structure
    as a dependency ratio, but no employment level. Working-age population follows
    from the dependency ratio, and the two rates convert it to employment.
    """
    working_age = population * 100 / (100 + dependency_ratio)
    labour_force = working_age * participation_pct / 100
    return labour_force * (1 - unemployment_pct / 100)
