"""Gold-layer validation.

Structural checks (grain uniqueness, referential integrity, nulls) plus a set of
economic checks that the structural ones cannot catch.

The economic checks exist because the failures that actually bit this project were
all of that kind. Two indicators pointed at the same source URL and loaded happily
as distinct metrics with identical values. Every soum series was compared across a
period in which the price level rose sevenfold. Neither is a broken join, and no
amount of primary-key checking would have found either.

Exit code is non-zero if any check fails, so the pipeline stops rather than
publishing a warehouse that is internally consistent and economically wrong.
"""

import sys

# Windows consoles default to a legacy codepage (cp1251 here), which kills any
# print carrying a non-ASCII character. Force UTF-8 before anything prints.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold")

NATIONAL_REGION_CODE = 1700

# The deflated national series should reproduce the World Bank's independently
# published real growth rate. It is the one check that proves the deflation is
# right rather than merely applied.
RECONCILIATION_TOLERANCE_PP = 0.5

failures = []


def check(condition, description, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {description}{(' - ' + detail) if detail else ''}")
    if not condition:
        failures.append(description)
    return condition


def load(filename):
    return pd.read_csv(os.path.join(GOLD_PATH, filename))


def main():
    print("Gold-layer validation\n")

    dim_region = load("dim_region.csv")
    dim_metric = load("dim_metric.csv")
    dim_year = load("dim_year.csv")
    fact = load("fact_economic.csv")

    print(f"dim_region {len(dim_region):>6} rows")
    print(f"dim_metric {len(dim_metric):>6} rows")
    print(f"dim_year   {len(dim_year):>6} rows")
    print(f"fact       {len(fact):>6} rows, {fact.year.min()}-{fact.year.max()}")

    print("\nStructural checks:")
    grain = ["region_code", "year", "metric_id"]
    check(fact.duplicated(subset=grain).sum() == 0, "fact grain is unique",
          f"{fact.duplicated(subset=grain).sum()} duplicates")
    check(fact[grain].notna().all().all(), "no nulls in key columns")
    check(fact["value"].notna().all(), "no null values")

    orphan_region = set(fact.region_code) - set(dim_region.region_code)
    orphan_metric = set(fact.metric_id) - set(dim_metric.metric_id)
    orphan_year = set(fact.year) - set(dim_year.year)
    check(not orphan_region, "every region_code resolves", str(orphan_region))
    check(not orphan_metric, "every metric_id resolves", str(orphan_metric))
    check(not orphan_year, "every year resolves", str(orphan_year))

    print("\nSource integrity:")
    # Two metrics loading identical values across every region and year almost
    # always means two config entries pointing at the same source file.
    wide = fact.pivot_table(index=["region_code", "year"], columns="metric_id", values="value")
    dupe_pairs = []
    cols = list(wide.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            both = wide[[a, b]].dropna()
            if len(both) > 20 and both[a].equals(both[b]):
                names = dim_metric.set_index("metric_id")["metric_code"]
                dupe_pairs.append(f"{names[a]} == {names[b]}")
    check(not dupe_pairs, "no two metrics carry identical series", "; ".join(dupe_pairs))

    print("\nEconomic checks:")
    deflatable = dim_metric[dim_metric.is_deflatable]
    covered = fact[fact.metric_id.isin(deflatable.metric_id)]
    have_real = covered.real_value.notna().sum()
    check(have_real > 0 and have_real == len(covered.dropna(subset=["value"])),
          f"all {len(deflatable)} current-price series carry a real_value",
          f"{have_real}/{len(covered)}")

    # Nothing published at current prices should be presented without a real
    # counterpart, and nothing already real should have been deflated twice.
    not_deflatable = dim_metric[~dim_metric.is_deflatable]
    wrongly_deflated = fact[fact.metric_id.isin(not_deflatable.metric_id) & fact.real_value.notna()]
    check(len(wrongly_deflated) == 0, "nothing outside the soum series was deflated",
          f"{len(wrongly_deflated)} rows")

    gdp_id = dim_metric.loc[dim_metric.metric_code == "regional_gdp", "metric_id"]
    if len(gdp_id):
        nat = fact[(fact.metric_id == gdp_id.iloc[0]) &
                   (fact.region_code == NATIONAL_REGION_CODE)].set_index("year").sort_index()
        wb = dim_year.set_index("year")["real_gdp_growth_pct"]
        ours = nat["real_value"].pct_change() * 100
        gap = (ours - wb).dropna().abs()
        gap = gap[gap.index >= 2011]
        check(len(gap) > 0 and gap.max() < RECONCILIATION_TOLERANCE_PP,
              "deflated GDP growth reconciles with World Bank real growth",
              f"max gap {gap.max():.3f}pp over {len(gap)} years")

    print("\nCoverage:")
    for grain_name, sub in fact.merge(dim_metric[["metric_id", "grain"]], on="metric_id").groupby("grain"):
        print(f"  {grain_name:9s} {len(sub):>6,} rows, {sub.year.min()}-{sub.year.max()}, "
              f"{sub.metric_id.nunique()} metrics, {sub.region_code.nunique()} region(s)")

    # The series do not all end in the same year, and a couple run a year or two
    # ahead on projections. Comparing each against the maximum would flag almost
    # everything, so the benchmark is the median last year: what "current" means
    # for this warehouse. Only series falling short of that are worth naming.
    last_years = fact.groupby("metric_id").year.max()
    benchmark = int(last_years.median())
    codes = dim_metric.set_index("metric_id")["metric_code"]

    ahead = last_years[last_years > benchmark]
    behind = last_years[last_years < benchmark].sort_values()

    print(f"\n  most series are complete through {benchmark}")
    if len(ahead):
        print(f"  {len(ahead)} run ahead of it: " +
              ", ".join(f"{codes[m]} to {y}" for m, y in ahead.items()))
    if len(behind):
        print(f"  {len(behind)} stop short of it:")
        for m, y in behind.items():
            print(f"    {codes[m]:38s} ends {y}  ({benchmark - y} year(s) short)")

    print()
    if failures:
        print(f"VALIDATION FAILED: {len(failures)} check(s)")
        for f in failures:
            print(f"  - {f}")
        raise SystemExit(1)

    print("All checks passed.")


if __name__ == "__main__":
    main()
