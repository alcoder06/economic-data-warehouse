# Uzbekistan Economic Data Warehouse

A data pipeline and Power BI report on Uzbekistan's economy, 1987 to 2025, built from
the national statistics agency's open API and the World Bank.

Twenty-one regional indicators and sixteen national ones go in. A 5,451-row star
schema comes out, and the point of the whole thing is one column in it.

---

## The finding

Uzbekistan's nominal GDP rose **1,643 per cent** between 2010 and 2024.

**91.3 per cent of that is the price level.** Real growth was 143 per cent — an
economy that roughly tripled, not one that grew seventeenfold.

That correction is not a footnote. It reverses two conclusions that look solid in the
published data:

| | Nominal | Real |
|---|---|---|
| GDP growth, 2010-2024 | +1,643% | +143% |
| Growth in 2018 | +33.9% | +5.7% |
| Correlation of GDP growth with investment growth | **+0.674** | **+0.036** |
| Regional convergence, 2010-2024 | — | reverses in 2017 |

The middle row is the one worth pausing on. The relationship between investment and
growth — the standard evidence that an expansion is investment-driven — is **+0.67**
on the published series and **+0.04** once both are deflated. Both series are
denominated in soums, and the soum lost most of its value over the period. Two series
carrying the same inflation trend co-move whether or not either causes the other.

An earlier version of this repository reported that correlation as a headline finding.
It was reproducible, correctly joined, and wrong.

> **Portfolio project.** Public data from the [Statistics Agency of the Republic of
> Uzbekistan](https://siat.stat.uz/) and the World Bank Open Data API. Not affiliated
> with, endorsed by, or produced for either.

---

## Why this project exists

I study economics alongside data science, and this repository is where the two meet.

Its companion piece,
[olist-marketplace-analytics](https://github.com/alcoder06/olist-marketplace-analytics),
is the engineering half: a PostgreSQL warehouse with a 3NF core, SCD2 dimensions,
role-playing date keys and a partitioned fact table. That project answers *can this
be built*.

This one answers a different question, because the pipeline was never what made it
hard. The first version of this repo had clean bronze-silver-gold separation, a
correct star schema, unique grain, referential integrity that held, and a validation
script that passed every check. Every conclusion it drew was wrong in the same way,
and no data-quality framework was ever going to catch it. Nothing about a soum series
compared against itself across a sevenfold change in the price level is *malformed*.

What caught it was knowing that stat.uz writes "at current prices" on its unit labels,
and that the som was floated in September 2017. That is domain knowledge, not
tooling, and it is the entire difference between the two versions of this project.

---

## The pipeline

```
config/sources.json          21 stat.uz SDMX indicators, 14 regions + national, 2010-2026
config/sources_worldbank.json  16 World Bank series, national, 1987-2025
        |
     bronze/     raw CSV as published, plus the .xlsx metadata card for each indicator
        |
     silver/     region codes and names standardised, year columns identified
        |
      gold/      star schema: fact_economic + dim_region, dim_metric, dim_year
```

```bash
pip install -r requirements.txt
python scripts/main_pipeline.py --steps all
```

Steps run in dependency order regardless of the order you type them, because
`gold_transform` needs both the World Bank deflator and the metadata cards before it
can produce a real value:

```bash
python scripts/main_pipeline.py --steps download metadata worldbank transform gold validate
```

### Two sources, one star

| | stat.uz | World Bank |
|---|---|---|
| Grain | 14 regions + Republic total | Republic only |
| Period | 2010-2026 | 1987-2025 |
| Indicators | 21 | 16 |
| Supplies | the regional detail | prices, population, the long run |

Both land in one `dim_metric` and one `fact_economic`, separated by a `source` and a
`grain` attribute rather than by being kept in separate tables. One star is easier to
query and easier to explain; the attributes stop anyone mixing the two by accident.

The World Bank series are not decoration. The stat.uz catalogue publishes no price
index that covers the period — its CPI series is broken out by COICOP category and
stops in 2020 — and no population series usable as a per-capita denominator until you
find indicator 246. Without an external deflator, every soum series in the warehouse
is uninterpretable across time.

### What the metadata cards gave up

Each SDMX dataset ships an `.xlsx` whose second sheet is a metadata card: official
indicator code, full name, periodicity, methodology URL, the compiler's notes, and the
unit. The earlier pipeline read the unit and discarded the rest.

The unit string is where the project turns:

```
"at current prices, billion soums"
```

That phrase, parsed rather than skimmed, is what tells the pipeline which nine series
are nominal and have to be deflated before anyone compares two years of them. It now
becomes a `price_basis` column on `dim_metric`, and `is_deflatable` keys off it.

---

## Validation

`scripts/validate_data.py` runs structural checks — grain uniqueness, referential
integrity, nulls — and then three that the structural ones cannot catch.

**No two metrics carry identical series.** The earlier `sources.json` had
`employment_rate` and `unemployed_population` pointing at the same URL. The two loaded
as distinct metrics with byte-identical values and passed every check, because nothing
about a duplicate is malformed. The real unemployment indicator is 1313; 1311 is the
employment rate, and its English name field is blank, which is presumably how they got
conflated.

**Nothing outside the soum series was deflated.** Deflating a dollar series by a soum
deflator would be worse than leaving it nominal.

**The deflated series reconciles with an independent benchmark.** Applying a deflator
is easy; applying the right one is the question. So the deflated national GDP series
is compared year by year against the World Bank's separately published real growth
rate:

```
year   nominal   deflated   World Bank   gap
2011     31.2%      8.13%        8.13%   0.000
2016     15.8%      6.72%        6.72%   0.000
2017     27.4%      4.73%        4.73%   0.000
2018     33.9%      5.68%        5.68%   0.000
2024     21.7%      6.65%        6.65%   0.000

mean absolute gap over 14 years: 0.0000 pp
```

The pipeline exits non-zero if that gap exceeds 0.5pp, so a broken deflator join stops
the build instead of quietly publishing nominal numbers under a real label.

---

## What the data shows

### The 2017 reform is a currency event in the nominal series

The som was floated in September 2017, moving from roughly 4,200 to 8,100 per dollar.
Every soum-denominated series inflates with it.

Nominal GDP growth accelerates from 15.8% (2016) to 33.9% (2018) — the fastest in the
series. Real growth over the same years *slows*, to 4.7% and 5.7%, the weakest
readings outside the 2020 pandemic. The two measures move in opposite directions
through the reform, and only one of them is measuring output.

### Regional convergence ran until 2016, then reversed

Measured properly — on real values, per head — Uzbekistan's regions were converging
and then stopped.

| Period | β | p | Verdict |
|---|---|---|---|
| 2010-2016 | −0.023 | 0.040 | **convergence**, poorer regions growing faster |
| 2017-2024 | +0.059 | 0.002 | **divergence**, richer regions pulling away |
| 2010-2024 | +0.025 | 0.052 | nothing significant |

The third row is the methodological point. Pooling two regimes with opposite signs
returns a coefficient that misses significance, and anyone running only the
full-period regression would conclude the country has no convergence dynamics at all.
Sigma-convergence and the Gini agree on both the direction and the 2016/17 turning
point.

Measurement choice decides the answer here too. On nominal GDP *levels* the Gini
drifts 0.275 → 0.328 and reads as slow structural change. On real GDP *per capita* it
falls 0.215 → 0.191 to 2016 and then climbs to 0.325 — a different shape, with the
turning point in it. The levels measure is substantially counting which regions are
populous and how much the price level moved.

### The long view

The World Bank series reach back to 1987, four years before independence: the
transition recession, the long gradualist period, the reform, the pandemic.
Agriculture falls from 25.5% of GDP to 16.6% across the period. The 1990s inflation
episode dwarfs 2017, which is why the float reads as a shock in a 2010-based chart and
as a bump in a 1990-based one.

---

## The report

Build specification, model, and every measure with its reasoning:
**[powerbi/README.md](powerbi/README.md)** and
**[powerbi/dax/measures.md](powerbi/dax/measures.md)**.

Three visible pages, one hidden drillthrough, 31 measures, zero calculated columns.

- **The nominal illusion** — the four numbers above, the two GDP lines, and an
  interactive nominal/real toggle on the investment correlation so a reader can watch
  it collapse rather than be told about it.
- **The long view, 1987-2025** — real GDP per capita banded by policy era, structural
  change, inflation in historical scale.
- **Regional divergence** — the beta-convergence scatter with a period slicer whose
  trend line changes sign, both Gini measures, regions ranked on real GDP per capita.

Two design decisions carry the argument. Nominal is the warm colour and real is the
teal, everywhere, without exception, so the distinction survives skimming. And there
is no map: fourteen regions on a choropleth would look accomplished and communicate
less than a sorted bar, because area encodes territory and Navoi is vast and small.

Every row-level calculation — deflation, per-capita, the Gini series, the convergence
regressions, the policy-era labels — happens in `gold_transform.py` and arrives in
Power BI as data. A value fixed for a row should be computed by the pipeline that
built the row, not by the report that reads it.

---

## Repo contents

```
config/          source definitions and the generated data dictionary
data/bronze/     raw CSV as published + metadata_raw/ xlsx cards + worldbank/
data/silver/     standardised
data/gold/       fact_economic, dim_region, dim_metric, dim_year, fact_convergence
scripts/         pipeline, loader, metrics, diagnostics, forecasting
notebooks/       uzbekistan_economic_analysis.ipynb
powerbi/         model spec, DAX reference, theme
sql/             schema and analytical queries
```

| Script | Does |
|---|---|
| `main_pipeline.py` | orchestrates, enforces step order |
| `download_data.py` | stat.uz regional CSVs |
| `download_metadata.py` | metadata cards → data dictionary, parses `price_basis` |
| `download_worldbank.py` | World Bank national series |
| `transform_data.py` | bronze → silver |
| `gold_transform.py` | star schema, real terms, per capita, inequality, convergence |
| `validate_data.py` | structural + economic checks, non-zero exit on failure |
| `load_data.py` | gold loader for the notebook |
| `metrics.py` | Gini, beta- and sigma-convergence, productivity |
| `regression_diagnostics.py` | OLS with Breusch-Pagan, VIF, Durbin-Watson, Newey-West |
| `forecasting.py` | ARIMA with prediction intervals, Monte Carlo Gini |

---

## Notes and limitations

- The national deflator is applied uniformly to all regions. No regional price index
  is published, so real regional growth is understated where local inflation ran
  faster than the national rate. This is the single largest caveat on the convergence
  results.
- Fourteen regions is a small cross-section. The convergence regressions are reported
  with p-values and R², and should be read as descriptive.
- `consumer_goods_output` ends in 2022 and seven series end in 2024 while most run to
  2025. `validate_data.py` reports the ragged edges rather than trimming them silently.
- The stat.uz unemployment series changes methodology around 2018, roughly doubling
  the measured level. The World Bank's ILO-modelled series is carried alongside for
  comparability.
- 2024 figures are marked preliminary in the source metadata.

## Stack

Python (pandas, statsmodels, matplotlib) · Power BI Desktop · PostgreSQL-compatible
DDL · stat.uz SDMX API · World Bank Open Data API

## Sources

- [Statistics Agency of the Republic of Uzbekistan](https://siat.stat.uz/) — SDMX open
  data, 21 regional indicators. Indicator codes and methodology links are preserved in
  `dim_metric`.
- [World Bank Open Data](https://data.worldbank.org/country/uzbekistan) — 16 national
  series including the GDP deflator that makes the rest of it interpretable.
