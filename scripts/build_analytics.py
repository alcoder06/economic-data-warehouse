"""Derive the analytical tables the report reads: growth accounting, investment
efficiency, sector contributions, shift-share and the peer benchmark.

Everything here is a fixed property of a year or a period rather than something that
should respond to a slicer, so it is computed once and stored. A Gini, a regression
coefficient and a TFP residual all need the whole cross-section or the whole series
before they yield one number; deriving them in the report would recompute them on
every interaction to get the same answer, and would let a reader filter to four
regions and receive something still labelled "the Gini".

Runs after gold_transform.py, which it depends on for the deflated national series.
"""

import sys
import os

# Windows consoles default to a legacy codepage (cp1251 here), which kills any
# print carrying a non-ASCII character. Force UTF-8 before anything prints.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import numpy as np
import pandas as pd

from growth_accounting import (
    ALPHA_DEFAULT, DELTA_DEFAULT, capital_stock, solow_decomposition,
    solow_sensitivity, incremental_capital_output_ratio,
    growth_contributions_by_sector, shift_share, employed_persons,
)

BASE_DIR = os.path.dirname(SCRIPTS_DIR)
GOLD = os.path.join(BASE_DIR, "data", "gold")
WB_NATIONAL = os.path.join(BASE_DIR, "data", "bronze", "worldbank", "national_context.csv")
WB_BENCHMARK = os.path.join(BASE_DIR, "data", "bronze", "worldbank", "benchmark.csv")

# Two independent tests for an unusable year, because the sector shares fail in two
# different ways.
#
# A component can go missing, in which case the three shares stop accounting for
# GDP: 2017 sums to 77.7 per cent against roughly 92 either side, with industry
# down 11 points.
SECTOR_SUM_MIN = 85.0
#
# Or output can be reclassified between components, in which case the sum stays
# perfect and only the split moves: in 2010 agriculture gains 5.4 points and
# industry loses 8.2 while the total holds at 89. No economy reallocates a twelfth
# of its output between sectors in a year, so this is a definitional change in the
# source. Genuine structural change in these series runs under 4 points a year.
SECTOR_MAX_ANNUAL_SHIFT = 4.0

SECTOR_VA = {"Agriculture": "wb_agriculture_pct_gdp",
             "Industry":    "wb_industry_pct_gdp",
             "Services":    "wb_services_pct_gdp"}
SECTOR_EMP = {"Agriculture": "wb_employment_agriculture_pct",
              "Industry":    "wb_employment_industry_pct",
              "Services":    "wb_employment_services_pct"}

WB_CONFIG = os.path.join(BASE_DIR, "config", "sources_worldbank.json")


def peer_country_codes():
    """The ISO3 codes we asked for as countries.

    Anything else the API returns is an aggregate. Matching on a hardcoded aggregate
    list does not work: the API answers the request for LMC and UMC with the codes
    XN and XT in its iso3 field, so the only reliable test is membership of the
    country list we sent.
    """
    import json
    with open(WB_CONFIG, "r", encoding="utf-8") as f:
        return set(json.load(f)["benchmark"]["countries"])


def load_wb():
    return pd.read_csv(WB_NATIONAL).set_index("year")


def build_country_dimension_and_benchmark():
    """Peer countries and aggregates, so every national figure can be drawn against
    a comparator. Nearly every chart in the World Bank's Uzbekistan reporting is."""
    print("Building benchmark...")

    if not os.path.exists(WB_BENCHMARK):
        print("  no benchmark file; skipping")
        return None, None

    bench = pd.read_csv(WB_BENCHMARK)

    dim = (bench[["country_code", "country_name"]]
           .drop_duplicates()
           .sort_values("country_code")
           .reset_index(drop=True))
    dim["is_aggregate"] = ~dim["country_code"].isin(peer_country_codes())
    dim["is_uzbekistan"] = dim["country_code"] == "UZB"
    # Peer group as the IMF and World Bank define it for Uzbekistan, kept separate
    # from the reform comparators so a chart can show either.
    dim["peer_group"] = np.where(
        dim["is_aggregate"], "Aggregate",
        np.where(dim["country_code"].isin(["KAZ", "KGZ", "TJK", "TKM", "AZE", "ARM", "GEO"]),
                 "Post-Soviet peer", "Reform comparator"))
    dim.loc[dim["is_uzbekistan"], "peer_group"] = "Uzbekistan"

    dim.to_csv(os.path.join(GOLD, "dim_country.csv"), index=False)
    bench.to_csv(os.path.join(GOLD, "fact_benchmark.csv"), index=False)

    print(f"  dim_country: {len(dim)} entities "
          f"({(~dim.is_aggregate).sum()} countries, {dim.is_aggregate.sum()} aggregates)")
    print(f"  fact_benchmark: {len(bench):,} rows, {bench.metric_code.nunique()} indicators")
    return dim, bench


def build_growth_accounting(wb):
    """Solow decomposition on the World Bank basis, with a sensitivity table."""
    print("Building growth accounting...")

    Y = wb["wb_real_gdp"].dropna()
    inv = (wb["wb_capital_formation_pct_gdp"] / 100 * Y).dropna()
    emp = employed_persons(wb["wb_population"], wb["wb_dependency_ratio"],
                           wb["wb_participation_pct"], wb["wb_unemployment_pct"]).dropna()

    K = capital_stock(inv, Y, delta=DELTA_DEFAULT)
    dec = solow_decomposition(Y, K, emp, alpha=ALPHA_DEFAULT)

    dec["capital_stock"] = K.reindex(dec.index)
    dec["capital_output_ratio"] = (K / Y).reindex(dec.index)
    dec["employed_persons"] = emp.reindex(dec.index)
    dec["alpha"] = ALPHA_DEFAULT
    dec["delta"] = DELTA_DEFAULT
    dec = dec.reset_index().rename(columns={"index": "year"})
    dec.to_csv(os.path.join(GOLD, "fact_growth_accounting.csv"), index=False)

    sens = solow_sensitivity(Y, inv, emp)
    sens.to_csv(os.path.join(GOLD, "fact_growth_sensitivity.csv"), index=False)

    print(f"  fact_growth_accounting: {len(dec)} years, {dec.year.min()}-{dec.year.max()}")
    print(f"  fact_growth_sensitivity: {len(sens)} alpha/delta combinations, "
          f"TFP contribution {sens.mean_tfp_contrib.min():.2f} to {sens.mean_tfp_contrib.max():.2f}")
    return dec


def build_investment_efficiency(wb):
    """ICOR and the investment rate. The World Bank charts this for Uzbekistan in
    Figure 31 of the 2022 Systematic Country Diagnostic."""
    print("Building investment efficiency...")

    Y = wb["wb_real_gdp"].dropna()
    inv = (wb["wb_capital_formation_pct_gdp"] / 100 * Y).dropna()

    icor = incremental_capital_output_ratio(inv, Y).reset_index().rename(columns={"index": "year"})
    icor.to_csv(os.path.join(GOLD, "fact_investment_efficiency.csv"), index=False)

    clean = icor[~icor.is_outlier]
    print(f"  fact_investment_efficiency: {len(icor)} years "
          f"({icor.is_outlier.sum()} flagged as near-zero-growth outliers)")
    print(f"    ICOR {clean.icor.iloc[0]:.2f} ({int(clean.year.iloc[0])}) "
          f"-> {clean.icor.iloc[-1]:.2f} ({int(clean.year.iloc[-1])})")
    return icor


def build_sector_contributions(wb):
    """Contributions to real GDP growth by sector, with unreliable years flagged.

    This is the chart the World Bank Country Economic Update opens with. It is the
    right opening because contributions sum to the growth rate, so it answers where
    growth came from rather than merely which sector grew.
    """
    print("Building sector contributions...")

    Y = wb["wb_real_gdp"].dropna()
    shares = wb[list(SECTOR_VA.values())].rename(columns={v: k for k, v in SECTOR_VA.items()})

    sector_sum = shares.sum(axis=1)
    incomplete = sector_sum[(sector_sum < SECTOR_SUM_MIN) & sector_sum.notna()].index.tolist()

    jump = shares.diff().abs().max(axis=1)
    reclassified = jump[jump > SECTOR_MAX_ANNUAL_SHIFT].index.tolist()

    unreliable = sorted(set(incomplete) | set(reclassified))

    contrib = growth_contributions_by_sector(Y, shares).reset_index().rename(columns={"index": "year"})

    # The two failure modes need different treatment, because a contribution is a
    # change and a change spans two levels.
    #
    # A missing component corrupts one level, so both the change into that year and
    # the change out of it are wrong: flag the year and the next.
    #
    # A reclassification shifts the level permanently onto a new basis. Only the
    # change across the break is wrong; every later change compares two levels on
    # the same basis and is fine. Flag the year alone.
    bad_years = set(incomplete) | {y + 1 for y in incomplete} | set(reclassified)
    contrib["shares_reliable"] = ~contrib["year"].isin(bad_years)
    contrib.to_csv(os.path.join(GOLD, "fact_sector_contributions.csv"), index=False)

    print(f"  fact_sector_contributions: {len(contrib)} years")
    if incomplete:
        print(f"    shares sum below {SECTOR_SUM_MIN}% (component missing): {incomplete}")
    if reclassified:
        print(f"    single sector moves over {SECTOR_MAX_ANNUAL_SHIFT}pp (reclassified): {reclassified}")
    print(f"    -> shares_reliable = False for {sorted(bad_years)}")
    usable = contrib[contrib.shares_reliable & (contrib.year >= 1999)]
    print(f"    usable from 1999: {len(usable)} of {len(contrib[contrib.year >= 1999])} years")
    return contrib


def build_shift_share(wb):
    """Within-sector versus between-sector sources of productivity growth."""
    print("Building shift-share...")

    Y = wb["wb_real_gdp"].dropna()
    emp = employed_persons(wb["wb_population"], wb["wb_dependency_ratio"],
                           wb["wb_participation_pct"], wb["wb_unemployment_pct"]).dropna()

    va_share = wb[list(SECTOR_VA.values())].rename(columns={v: k for k, v in SECTOR_VA.items()})
    emp_share = wb[list(SECTOR_EMP.values())].rename(columns={v: k for k, v in SECTOR_EMP.items()})

    va = va_share.div(100).mul(Y, axis=0)
    emp_level = emp_share.div(100).mul(emp, axis=0)
    productivity = (va / emp_level).dropna()

    periods = [(1995, 2007, "Gradualist"), (2008, 2016, "Pre-reform"),
               (2017, 2024, "Post-reform"), (1995, 2024, "Full period")]

    rows = []
    for start, end, label in periods:
        if start not in productivity.index or end not in productivity.index:
            continue
        r = shift_share(productivity, emp_share, start, end)
        r["period"] = label
        r["decomposition"] = "sectoral"
        rows.append(r)

    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(GOLD, "fact_shift_share.csv"), index=False)

    print(f"  fact_shift_share: {len(out)} periods")
    for _, r in out.iterrows():
        print(f"    {r.period:12s} {int(r.start_year)}-{int(r.end_year)}: "
              f"within {r.within_pct:6.1f}%  between {r.between_pct:5.1f}%")
    return out


def main():
    wb = load_wb()
    build_country_dimension_and_benchmark()
    build_growth_accounting(wb)
    build_investment_efficiency(wb)
    build_sector_contributions(wb)
    build_shift_share(wb)
    print("\nAnalytics layer complete.")


if __name__ == "__main__":
    main()
