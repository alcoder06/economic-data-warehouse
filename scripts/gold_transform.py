"""Build the analytics star schema from the silver layer.

Three things happen here that the silver layer cannot do on its own.

Real terms. Ten of the stat.uz series are published at current prices. Over 2010-2024
the price level rose 7.2x while nominal GDP rose 17.4x, so roughly nine tenths of the
apparent growth in any soum series is the price level rather than output. Every
current-price soum series therefore gets a `real_value` in constant 2010 soums,
computed from the World Bank GDP deflator. Series denominated in USD are left alone:
deflating dollars by a soum deflator would be worse than not deflating at all.

Per capita. Volume series get a `value_per_capita` and `real_value_per_capita`
against the regional permanent population. This matters most for inequality work,
where a Gini computed on GDP levels largely measures which regions are populous.

The national row. region_code 1700 is the Republic total and sits in the same column
as the fourteen regions that compose it. Summing the column double-counts, so the
region dimension carries an `is_national` flag for the reporting layer to filter on.
"""

import sys

# Windows consoles default to a legacy codepage (cp1251 here), which kills any
# print carrying a non-ASCII character. Force UTF-8 before anything prints.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import json
import os

import numpy as np
import pandas as pd

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

BASE_DIR = os.path.dirname(SCRIPTS_DIR)

METADATA_PATH = os.path.join(BASE_DIR, "config", "metadata.json")
WORLDBANK_CONFIG_PATH = os.path.join(BASE_DIR, "config", "sources_worldbank.json")
SILVER_PATH = os.path.join(BASE_DIR, "data", "silver")
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold")
WORLDBANK_PATH = os.path.join(BASE_DIR, "data", "bronze", "worldbank", "national_context.csv")

os.makedirs(GOLD_PATH, exist_ok=True)

NATIONAL_REGION_CODE = 1700
BASE_YEAR = 2010

# The September 2017 float roughly halved the som against the dollar and fed
# straight into the price level. Any comparison spanning it is comparing two
# different currency regimes, so the year dimension labels the eras.
FLOAT_YEAR = 2017

# Start of the analysable record, and the single start date for every chart.
#
# stat.uz publishes no regional series before 2010, so the regional half of this
# project cannot begin earlier whatever the national data allows. Running the
# national pages from an earlier year would buy twelve years of extra history at
# the cost of every page starting somewhere different, and charts that do not share
# an x-axis are read against each other incorrectly.
#
# The earlier years are weak on their own terms in any case. The transition
# recession makes every rate enormous, hyperinflation makes every level
# meaningless, the World Bank sector shares oscillate by six points a year in both
# directions, and stat.uz notes that GDP was "revised to take into account the
# non-observed economy in accordance with the 2008 SNA methodology" - the shadow
# economy was not in the accounts, and the further back you go the less of it is
# captured.
#
# One named constant, carried on dim_year as a flag, so every visual filters on one
# field rather than a year typed separately into each.
ANALYSIS_START_YEAR = 2010

# Metrics where a per-capita figure is meaningful. Rates, shares, indices and
# population itself are excluded: dividing a percentage by population is nonsense.
NON_PER_CAPITA_UNITS = {"%", None}
NON_PER_CAPITA_METRICS = {"population", "fixed_capital_investment_per_capita", "employment_rate"}


def load_metadata():
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_worldbank_config():
    with open(WORLDBANK_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["indicators"]


def create_dim_region():
    """Region dimension, with the national total flagged so it can be excluded."""
    print("Creating dim_region...")

    frames = []
    for file in sorted(os.listdir(SILVER_PATH)):
        if not file.endswith(".csv"):
            continue
        df = pd.read_csv(os.path.join(SILVER_PATH, file))
        if {"region_code", "region_name"}.issubset(df.columns):
            frames.append(df[["region_code", "region_name"]])

    if not frames:
        raise SystemExit("No region data found in silver layer.")

    dim = (
        pd.concat(frames)
        .drop_duplicates()
        .sort_values("region_code")
        .reset_index(drop=True)
    )

    dim["is_national"] = dim["region_code"] == NATIONAL_REGION_CODE
    dim["region_type"] = np.where(
        dim["is_national"], "Republic total",
        np.where(dim["region_name"].str.contains("city", case=False), "City",
        np.where(dim["region_name"].str.contains("Karakalpakstan", case=False),
                 "Autonomous republic", "Region")),
    )
    # Short label for chart axes, where "Republic of Karakalpakstan" will not fit.
    dim["region_short"] = (
        dim["region_name"]
        .str.replace(" region", "", regex=False)
        .str.replace("Republic of ", "", regex=False)
        .str.replace("Uzbekistan", "UZBEKISTAN", regex=False)
    )

    dim.to_csv(os.path.join(GOLD_PATH, "dim_region.csv"), index=False)
    print(f"  dim_region: {len(dim)} rows ({(~dim.is_national).sum()} regions + national total)")
    return dim


def create_dim_metric(metadata, wb_config):
    """Metric dimension: the stat.uz data dictionary plus the World Bank national series.

    Both sources land in one dimension rather than two, so the model stays a single
    star. `source` and `grain` separate them for anyone querying it: the stat.uz
    series carry all fourteen regions from 2010, the World Bank series are national
    only but reach back to 1987.
    """
    print("Creating dim_metric...")

    records = []
    for idx, code in enumerate(sorted(metadata.keys()), start=1):
        meta = metadata[code]
        unit = meta.get("unit")
        is_uzs = unit in ("billion UZS", "million UZS", "thousand UZS")

        records.append({
            "metric_id": idx,
            "metric_code": code,
            "metric_name": meta.get("indicator_name") or code.replace("_", " ").title(),
            "metric_short": code.replace("_", " ").title(),
            "official_code": meta.get("official_code"),
            "unit": unit,
            "unit_raw": meta.get("unit_raw"),
            "price_basis": meta.get("price_basis"),
            # Only soum series can be deflated by a soum deflator.
            "is_deflatable": bool(is_uzs and meta.get("price_basis") == "current"),
            "per_capita_meaningful": bool(
                code not in NON_PER_CAPITA_METRICS and unit not in NON_PER_CAPITA_UNITS
            ),
            "source": meta.get("source"),
            "source_id": meta.get("source_id"),
            "grain": "regional",
            "metric_group": "stat.uz regional indicator",
            "periodicity": meta.get("periodicity"),
            "methodology_url": meta.get("methodology_url"),
            "notes": " | ".join(meta.get("notes", [])) or None,
        })

    offset = len(records)
    for idx, code in enumerate(sorted(wb_config.keys()), start=offset + 1):
        spec = wb_config[code]
        records.append({
            "metric_id": idx,
            "metric_code": code,
            "metric_name": spec["metric_name"],
            "metric_short": spec["metric_name"],
            "official_code": spec["wb_code"],
            "unit": spec["unit"],
            "unit_raw": spec["unit"],
            # World Bank series arrive already in constant terms, as an index, a
            # ratio or USD. None of them is a current-price soum series.
            "price_basis": "not applicable",
            "is_deflatable": False,
            "per_capita_meaningful": False,
            "source": "World Bank",
            "source_id": spec["wb_code"],
            "grain": "national",
            "metric_group": spec.get("group"),
            "periodicity": "annual",
            "methodology_url": f"https://data.worldbank.org/indicator/{spec['wb_code']}",
            "notes": spec.get("note"),
        })

    dim = pd.DataFrame(records)
    dim.to_csv(os.path.join(GOLD_PATH, "dim_metric.csv"), index=False)
    by_source = dim.groupby("source").size().to_dict()
    print(f"  dim_metric: {len(dim)} rows {by_source}, {dim.is_deflatable.sum()} deflatable")
    return dim


def policy_era(year):
    """Label each year with the policy regime in force.

    A period-average chart needs a period to average over, and a 16-year line chart
    reads better banded than bare.

    Numbered from the start of the analysis window rather than from independence,
    because everything before 2010 is out of scope and an axis labelled 4 through 7
    with no 1 to 3 invites the question of what is missing.

    The breaks are the ones the literature uses: the commodity-priced expansion to
    2016, the 2017 liberalisation that floated the som, the pandemic, and the
    recovery.
    """
    if year < ANALYSIS_START_YEAR:
        return "0. Before analysis window"
    if year <= 2016:
        return "1. Pre-reform boom"
    if year <= 2019:
        return "2. Reform and float"
    if year == 2020:
        return "3. Pandemic"
    return "4. Post-pandemic"


def create_dim_year(fact_years, regional_years):
    """Year dimension carrying the deflator, so the report never derives it at query time."""
    print("Creating dim_year...")

    wb = pd.read_csv(WORLDBANK_PATH).set_index("year")

    dim = pd.DataFrame({"year": sorted(fact_years)}).set_index("year")
    dim = dim.join(wb[[c for c in (
        "wb_gdp_deflator", "wb_cpi", "wb_exchange_rate_uzs_usd", "wb_real_gdp_growth_pct"
    ) if c in wb.columns]])

    dim = dim.rename(columns={
        "wb_gdp_deflator": "gdp_deflator",
        "wb_cpi": "cpi",
        "wb_exchange_rate_uzs_usd": "exchange_rate_uzs_usd",
        "wb_real_gdp_growth_pct": "real_gdp_growth_pct",
    })

    # Rebase the index series so the base year reads exactly 100.
    for col in ("gdp_deflator", "cpi"):
        if col in dim.columns and BASE_YEAR in dim.index and pd.notna(dim.loc[BASE_YEAR, col]):
            dim[col] = dim[col] / dim.loc[BASE_YEAR, col] * 100

    dim["deflator_ratio"] = dim["gdp_deflator"] / 100
    dim["currency_era"] = np.where(
        dim.index < FLOAT_YEAR, "Managed rate (pre-2017)", "Floating rate (2017+)"
    )
    dim["is_float_year"] = dim.index == FLOAT_YEAR
    dim["policy_era"] = [policy_era(y) for y in dim.index]
    dim["decade"] = (dim.index // 10 * 10).astype(str) + "s"
    # Regional analysis is only possible where stat.uz publishes; the World Bank
    # series run 23 years earlier and a chart mixing the two has to say so.
    dim["has_regional_data"] = dim.index.isin(regional_years)
    # The national analysis window. Every national visual filters on this.
    dim["in_analysis_window"] = dim.index >= ANALYSIS_START_YEAR

    dim = dim.reset_index()
    dim.to_csv(os.path.join(GOLD_PATH, "dim_year.csv"), index=False)

    covered = dim["deflator_ratio"].notna().sum()
    print(f"  dim_year: {len(dim)} rows ({dim.year.min()}-{dim.year.max()}), "
          f"deflator for {covered}, analysis window {dim.in_analysis_window.sum()}, "
          f"regional {dim.has_regional_data.sum()}")
    return dim


def create_fact_economic(dim_metric, dim_year):
    """Long fact table with nominal, real and per-capita measures."""
    print("Creating fact_economic...")

    frames = []
    for file in sorted(os.listdir(SILVER_PATH)):
        if not file.endswith(".csv"):
            continue

        df = pd.read_csv(os.path.join(SILVER_PATH, file))
        metric_code = file.replace(".csv", "")
        row = dim_metric[dim_metric["metric_code"] == metric_code]

        if row.empty:
            print(f"  skipping {metric_code}: not in dim_metric")
            continue

        year_columns = [c for c in df.columns if str(c).strip().isdigit()]
        if not year_columns:
            continue

        long = df.melt(
            id_vars=["region_code"],
            value_vars=year_columns,
            var_name="year",
            value_name="value",
        )
        long["metric_id"] = int(row["metric_id"].iloc[0])
        frames.append(long)

    fact = pd.concat(frames)
    fact["year"] = fact["year"].astype(int)
    fact["value"] = pd.to_numeric(fact["value"], errors="coerce")
    fact = fact.dropna(subset=["value"]).drop_duplicates(
        subset=["region_code", "year", "metric_id"], keep="first"
    )

    # Real terms: constant 2010 soums, soum series only.
    deflatable = set(dim_metric.loc[dim_metric["is_deflatable"], "metric_id"])
    ratios = dim_year.set_index("year")["deflator_ratio"]

    fact["deflator_ratio"] = fact["year"].map(ratios)
    mask = fact["metric_id"].isin(deflatable) & fact["deflator_ratio"].notna()
    fact["real_value"] = np.where(mask, fact["value"] / fact["deflator_ratio"], np.nan)

    # Per capita, against regional permanent population (published in thousands).
    pop_id = dim_metric.loc[dim_metric["metric_code"] == "population", "metric_id"]
    if len(pop_id):
        pop = (
            fact[fact["metric_id"] == pop_id.iloc[0]]
            .set_index(["region_code", "year"])["value"]
            .mul(1_000)
        )
        keys = pd.MultiIndex.from_arrays([fact["region_code"], fact["year"]])
        fact["population"] = pop.reindex(keys).to_numpy()

        per_capita = set(dim_metric.loc[dim_metric["per_capita_meaningful"], "metric_id"])
        pc_mask = fact["metric_id"].isin(per_capita) & fact["population"].notna()

        fact["value_per_capita"] = np.where(pc_mask, fact["value"] / fact["population"], np.nan)
        fact["real_value_per_capita"] = np.where(
            pc_mask & fact["real_value"].notna(),
            fact["real_value"] / fact["population"],
            np.nan,
        )
    else:
        fact["population"] = np.nan
        fact["value_per_capita"] = np.nan
        fact["real_value_per_capita"] = np.nan

    fact = fact[[
        "region_code", "year", "metric_id",
        "value", "real_value", "value_per_capita", "real_value_per_capita",
    ]]

    # Append the World Bank national series against the Republic region code, so
    # one fact table answers both the regional and the long-run national question.
    wb_rows = build_worldbank_rows(dim_metric)
    fact = pd.concat([fact, wb_rows], ignore_index=True)

    fact = fact.sort_values(["metric_id", "region_code", "year"]).reset_index(drop=True)
    fact.to_csv(os.path.join(GOLD_PATH, "fact_economic.csv"), index=False)

    print(f"  fact_economic: {len(fact):,} rows "
          f"({len(fact) - len(wb_rows):,} regional + {len(wb_rows):,} national)")
    print(f"    with real_value:       {fact.real_value.notna().sum():,}")
    print(f"    with value_per_capita: {fact.value_per_capita.notna().sum():,}")
    print(f"    year range:            {fact.year.min()}-{fact.year.max()}")
    dup = fact.duplicated(subset=["region_code", "year", "metric_id"]).sum()
    print(f"    duplicate grain rows:  {dup}")
    return fact


def build_worldbank_rows(dim_metric):
    """Reshape the wide World Bank context file into fact rows at the national code."""
    wb = pd.read_csv(WORLDBANK_PATH)
    lookup = dim_metric.set_index("metric_code")["metric_id"]

    long = wb.melt(id_vars="year", var_name="metric_code", value_name="value").dropna(subset=["value"])
    long = long[long["metric_code"].isin(lookup.index)]
    long["metric_id"] = long["metric_code"].map(lookup)
    long["region_code"] = NATIONAL_REGION_CODE

    # These series are already real, indexed or expressed as a ratio, so the
    # real-terms and per-capita columns do not apply to them.
    for col in ("real_value", "value_per_capita", "real_value_per_capita"):
        long[col] = np.nan

    return long[[
        "region_code", "year", "metric_id",
        "value", "real_value", "value_per_capita", "real_value_per_capita",
    ]]


def create_inequality_measures(fact, dim_metric, dim_region, dim_year):
    """Compute regional inequality and convergence once, here, not in the report.

    A Gini coefficient needs the whole cross-section of a year before it can produce
    a single number, which makes it expensive and awkward to express in DAX and
    trivial in pandas. It is also a fixed property of a year rather than something
    that should respond to a slicer, so it belongs on the year dimension. The same
    argument applies to the convergence regressions, which land in their own small
    table because they describe a period rather than a year.
    """
    print("Computing inequality and convergence measures...")

    from metrics import beta_convergence, gini

    gdp_id = dim_metric.loc[dim_metric.metric_code == "regional_gdp", "metric_id"].iloc[0]
    regional = dim_region.loc[~dim_region.is_national, "region_code"]

    gdp = fact[(fact.metric_id == gdp_id) & (fact.region_code.isin(regional))]
    pivot_pc = gdp.pivot_table(index="year", columns="region_code", values="real_value_per_capita")
    pivot_lv = gdp.pivot_table(index="year", columns="region_code", values="value")

    rows = []
    for year in pivot_pc.index:
        pc = pivot_pc.loc[year].dropna()
        lv = pivot_lv.loc[year].dropna()
        if len(pc) < 5:
            continue
        rows.append({
            "year": year,
            "gini_real_gdp_pc": gini(pc.values),
            # Kept alongside so the report can show what the naive choice would say.
            "gini_nominal_levels": gini(lv.values) if len(lv) >= 5 else np.nan,
            "sigma_log_dispersion": np.log(pc).std(),
        })

    measures = pd.DataFrame(rows)
    dim_year = dim_year.merge(measures, on="year", how="left")
    dim_year.to_csv(os.path.join(GOLD_PATH, "dim_year.csv"), index=False)

    # Convergence regressions. The split is the whole point: pooling the two
    # regimes reports nothing happening, because they have opposite signs.
    periods = {
        "Full period": (2010, 2024),
        "Pre-reform": (2010, 2016),
        "Post-float": (2017, 2024),
    }

    results = []
    for label, (start, end) in periods.items():
        if start not in pivot_pc.index or end not in pivot_pc.index:
            continue
        model, data = beta_convergence(pivot_pc, start, end)
        beta = model.params["log_initial"]
        pval = model.pvalues["log_initial"]
        results.append({
            "period": label, "start_year": start, "end_year": end,
            "beta": beta, "p_value": pval, "r_squared": model.rsquared,
            "n_regions": int(model.nobs),
            "verdict": ("no significant relationship" if pval >= 0.05
                        else "convergence" if beta < 0 else "divergence"),
        })

    conv = pd.DataFrame(results)
    conv.to_csv(os.path.join(GOLD_PATH, "fact_convergence.csv"), index=False)

    # The scatter behind each regression: one point per region per period. Held as
    # data rather than derived in the report, because the x axis is a log of a
    # single year's value and the y axis is an annualised rate between two years,
    # and expressing either as a measure would mean recomputing at every redraw
    # what is a fixed property of the region and the period.
    points = []
    for label, (start, end) in periods.items():
        if start not in pivot_pc.index or end not in pivot_pc.index:
            continue
        y0, y1 = pivot_pc.loc[start].dropna(), pivot_pc.loc[end].dropna()
        for code in y0.index.intersection(y1.index):
            points.append({
                "period": label,
                "region_code": code,
                "log_initial": np.log(y0[code]),
                "annual_growth_pct": np.log(y1[code] / y0[code]) / (end - start) * 100,
            })

    pts = pd.DataFrame(points)
    pts.to_csv(os.path.join(GOLD_PATH, "fact_convergence_points.csv"), index=False)
    print(f"  fact_convergence_points: {len(pts)} rows "
          f"({pts.period.nunique()} periods x {pts.region_code.nunique()} regions)")

    print(f"  dim_year: inequality measures for {len(measures)} years")
    for r in results:
        print(f"  {r['period']:12s} {r['start_year']}-{r['end_year']}  "
              f"beta={r['beta']:+.4f} p={r['p_value']:.3f} -> {r['verdict']}")
    return dim_year, conv


def main():
    metadata = load_metadata()
    wb_config = load_worldbank_config()

    dim_region = create_dim_region()
    dim_metric = create_dim_metric(metadata, wb_config)

    # The year dimension spans both sources: stat.uz from 2010, World Bank from 1987.
    regional_years = set()
    for file in os.listdir(SILVER_PATH):
        if file.endswith(".csv"):
            cols = pd.read_csv(os.path.join(SILVER_PATH, file), nrows=0).columns
            regional_years.update(int(c) for c in cols if str(c).strip().isdigit())

    wb_years = set(pd.read_csv(WORLDBANK_PATH)["year"])

    dim_year = create_dim_year(regional_years | wb_years, regional_years)
    fact = create_fact_economic(dim_metric, dim_year)
    create_inequality_measures(fact, dim_metric, dim_region, dim_year)
    print("\nGold layer complete.")


if __name__ == "__main__":
    main()
