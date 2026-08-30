# Power BI report

Build specification for the Uzbekistan economic analysis report: the model, the
measures, the pages, and the reasoning behind each.

The gold layer is already shaped for this. Everything below is assembly.

---

## Connecting

Get Data → Text/CSV, one query per file, from `data/gold/`:

| File | Rename to | Rows |
|---|---|---|
| `fact_economic.csv` | `Fact` | 5,451 |
| `dim_metric.csv` | `Metric` | 37 |
| `dim_region.csv` | `Region` | 15 |
| `dim_year.csv` | `Year` | 40 |
| `fact_convergence.csv` | `Convergence` | 3 |

Point the queries at a **parameter** rather than an absolute path. File → Options →
Parameters, create `DataFolder` as text, default to your local `data/gold`, and set
each query's source to `Folder.Files(DataFolder)`. Without it every query hardcodes
`D:\...\your-name\...` and the file will not refresh on anyone else's machine.

Two more tables are created in the report rather than loaded:

```
Enter Data → "Price Basis", one text column "Basis", two rows: Nominal, Real
Enter Data → "_Measure", one column, one blank row; hide the column
```

`Price Basis` is a disconnected slicer table read by `SELECTEDVALUE`. `_Measure`
holds every measure so they sit together at the top of the field list instead of
being scattered across the tables whose columns they happen to reference.

### Load-time settings

- **Auto Date/Time off** (File → Options → Data Load). The grain is the year and
  there are no dates in the model. Left on, it silently builds a hidden date
  hierarchy per date column.
- **Every numeric column in `Fact` → Summarization: Do not summarize.** This is the
  important one. One `value` column carries billions of soums, millions of dollars,
  kilowatt-hours, people and percentages, so a reader who drags `value` onto a card
  gets their sum. Blocking implicit aggregation forces everything through the
  measures, which carry the unit guard.
- Hide `region_code`, `metric_id`, `deflator_ratio` from report view. Keys and
  intermediate columns are for the engine.

---

## The model

```
              Region (15)                Metric (37)
                   |                          |
           region_code                   metric_id
                   |                          |
                   +------ Fact (5,451) ------+
                              |
                            year
                              |
                          Year (40)          Convergence (3, disconnected)
                                             Price Basis (2, disconnected)
```

One fact, three dimensions, all relationships single-direction and one-to-many from
the dimension side. No role-playing dimensions, no inactive relationships, no
bidirectional filters.

The topology is deliberately dull. The difficulty in this model is not structural —
it is that a single `value` column means different things on different rows, and no
relationship diagram can express that. It has to be handled in the dimension
attributes and the measures. See [dax/measures.md](dax/measures.md).

### What the dimension flags are for

| Column | Why it exists |
|---|---|
| `Region[is_national]` | `region_code` 1700 is the Republic total, sitting in the same column as the fourteen regions that sum to it. Every regional aggregate must exclude it or the country is counted twice. |
| `Metric[grain]` | `regional` series (stat.uz, 14 regions, from 2010) versus `national` (World Bank, Republic only, from 1987). A visual mixing them is comparing different populations. |
| `Metric[is_deflatable]` | The nine current-price soum series. Only these have a `real_value`. |
| `Metric[price_basis]` | Parsed from the publisher's own unit string, "at current prices, billion soums". |
| `Year[has_regional_data]` | False before 2010. Stops a regional visual rendering 23 years of empty axis. |
| `Year[policy_era]` | Six labelled regimes. A 39-year chart is unreadable without them. |

---

## Layout grid

Canvas 1280 × 720. One outer margin, one gap, used everywhere:

```
outer margin   24 px
gap            16 px
usable width   1232 px

4 columns   296 px each
3 columns   400 px each
2 columns   608 px each
```

Vertical bands, consistent across all pages:

```
y=24    h=48    header (title left, slicers right)
y=88    h=96    KPI cards
y=200   h=280   hero visual
y=496   h=200   supporting row
```

The numbers are not special. What matters is that there is one of each, so no gap is
ever decided twice and neighbouring visuals line up without anyone eyeballing them.

---

## Page 1 — The nominal illusion

*Is the economy growing as fast as the headline numbers say?*

The page exists to answer no, and to show its working.

**Cards** (four, 296 wide, equal size because none outranks the others):

| Card | Measure | Reads |
|---|---|---|
| Nominal GDP growth | `Nominal Growth Multiple` | 17.43x |
| Price level | `Price Level Multiple` | 7.17x |
| Real GDP growth | `Real Growth Multiple` | 2.43x |
| Of which is price | `Share of Growth That Is Price` | 91.3% |

Read left to right they are the argument in four numbers.

**Hero — Nominal vs real GDP, indexed 2010 = 100** (line chart, full width, 280 high)

- X: `Year[year]`, filtered 2010–2025
- Y: two lines, nominal and real, both rebased to 100 at 2010
- Nominal in `#C4622D`, real in `#0E6E64`

The colour assignment is fixed across the whole report and carries the argument:
**nominal is always the warm colour, real is always the teal.** By page three a
reader knows which is which without checking the legend.

The two lines end at 1,743 and 243. Leave the axis linear. A log axis would make the
gap look modest and readable, which is exactly the impression the page exists to
correct.

**Bottom left — Growth rates by year** (clustered column, 608 wide)

Nominal and real growth side by side per year. The pair to look at is 2017 and 2018,
where nominal accelerates to 27.4% and 33.9% while real slows to 4.7% and 5.7%.

Side by side rather than stacked, because the question is which is larger in a given
year, and stacking makes that a comparison of segment lengths against a moving base.

**Bottom right — Investment and GDP growth** (scatter, 608 wide)

- X: `GDP ... Growth %`, Y: `Investment ... Growth %`, one point per year 2011–2024
- A `Price Basis` slicer above it, and a card showing `Corr GDP vs Investment`

Toggling the slicer moves the correlation from **+0.674** to **+0.036** and scatters
the points. The reader performs the finding rather than being told it.

This is the page's second argument and it needs the interaction: told that a
correlation is spurious, a reader has to take it on trust; handed the switch, they
watch it happen.

---

## Page 2 — The long view, 1987–2025

*Where does the 2017 reform sit in the whole independence era?*

Page one establishes that the recent numbers mislead. This page puts the corrected
numbers in a frame long enough to interpret them, using the World Bank series that
reach back four years before independence.

**Hero — Real GDP per capita, 1987–2025** (line, full width)

- Y: `wb_real_gdp_per_capita`, constant 2015 USD
- Background shading by `Year[policy_era]`, six bands, light neutral fills

The shape the bands explain: a transition recession through the mid-1990s, a long
flat gradualist period, acceleration from about 2003, and the reform period.

**Supporting row** (three visuals, 400 wide each)

1. **Structural change** — stacked area, agriculture / industry / services as % of
   GDP, 1987–2025. Agriculture's share falls by more than half across the period.
2. **Inflation** — line, `wb_inflation_cpi_pct`. The 1990s scale dwarfs everything
   recent, which is the point: it is why 2017 looks mild in context and severe in a
   2010-based chart.
3. **Openness and remittances** — two lines, trade and remittances as % of GDP.

**Cards**: GNI per capita (Atlas), trade openness, remittances % of GDP,
gross capital formation % of GDP.

Use the investment *share of GDP* here, not the soum investment series from page one.
A share is already a real quantity — both numerator and denominator inflate together
— so it answers "how much of output goes to investment" without any deflation at all.
That it agrees with the deflated series is a check on both.

**A note on the page**: add a caption reading *Regional data begins in 2010; this page
is national only.* `Year[has_regional_data]` marks it. Leaving a reader to assume
regional coverage runs the full 39 years is the kind of gap that gets found in a
follow-up question rather than on the page.

---

## Page 3 — Regional divergence

*Is growth reaching all regions, and did that change?*

**Hero — Beta-convergence scatter** (full width, 280 high)

- X: log real GDP per capita in the start year
- Y: annualised growth rate over the period
- One point per region, labelled with `Region[region_short]`
- Trend line on, `Convergence` period slicer above

Slice to **Pre-reform (2010–2016)**: the line slopes down, β = −0.023, p = 0.040.
Poorer regions grew faster.

Slice to **Post-float (2017–2024)**: the line slopes up, β = +0.059, p = 0.002,
R² = 0.574. Richer regions pulled away.

Slice to **Full period**: β = +0.025, p = 0.052 — nothing significant. That third
state is worth leaving in the slicer rather than hiding, because it is the finding.
Pooling two regimes with opposite signs reports that nothing happened. Anyone who ran
only the full-period regression would conclude Uzbekistan has no convergence dynamics
at all.

**Card** — `Convergence Verdict`, with `Convergence Verdict Colour` driving the font
colour through conditional formatting (Format → Callout value → fx → Field value).

Three fixed categories rather than a colour scale. A gradient over a regression
coefficient says only that darker is larger; the reader needs to know which side of
zero it is on.

**Bottom row**

1. **Inequality over time** (608 wide) — two lines, `Gini (real GDP per capita)` and
   `Gini (nominal GDP levels)`.

   The nominal line drifts 0.275 → 0.328 and looks like slow structural change. The
   real per-capita line falls 0.215 → 0.191 to 2016, then climbs to 0.325 — a
   different shape with a turning point in it. Showing both is the honest way to make
   the point that the measure choice, not the data, produced the earlier answer.

2. **Real GDP per capita by region** (608 wide) — bar chart, latest year, sorted
   descending, `Region[is_national] = False` as a visual-level filter.

   Set that filter explicitly on the visual. It is the one every regional chart in
   this model needs and the one that is easy to forget, and forgetting it puts a bar
   for the whole country next to the fourteen regions that compose it.

---

## Page 4 — Region detail (hidden, drillthrough)

Drillthrough field: `Region[region_name]`. Right-clicking any region on page three
arrives here with that filter carried.

A heading bound to `SELECTEDVALUE('Region'[region_name])`, then a small multiple or
matrix over that region's indicators: real GDP per capita, investment, employment
rate, population, industrial output, each as a sparkline against the national path.

Keep the back button Power BI adds automatically. A reader three levels into a filter
state with no way back will use the browser's back button and lose the whole session.

---

## Design rationale

A dashboard is an argument, not a container. Three rules ran through this one.

### The colour carries the claim

Nominal is `#C4622D` everywhere. Real is `#0E6E64` everywhere. No exceptions, on any
page, for any indicator.

That consistency is doing analytical work rather than decorative work. The report's
whole thesis is that one of these two series is misleading and the other is not, and
a reader who has to re-read a legend on each page never internalises which is which.
Fixed encoding means the argument survives being skimmed.

It is also why there is no second accent colour for variety. Every additional hue
would compete with the one distinction the report is built on.

### Less is more

Eleven visuals across three visible pages. What was left out was left out on purpose:
no map, no gauges, no decorative icons, no KPI nobody asked for.

The map is the notable omission. Fourteen regions on a choropleth of Uzbekistan would
look accomplished and would communicate less than the sorted bar chart it would
replace: area on a map encodes territory size, not economic size, and Navoi is vast
and small. A sorted bar puts the regions in the order the question asks about.

Conditional formatting uses three fixed categories rather than a gradient, for the
same reason throughout: a rule states a threshold a reader can act on, a gradient only
says more is more.

Restraint here is also a performance decision. Every visual is a query. A page
carrying twenty responds more slowly than a page carrying eleven whether or not the
reader looks at all twenty, and the cost lands twice — once in how long the page takes
to answer and once in how long the reader takes to find what they came for.

### Push the work upstream

Every row-level calculation happens in `gold_transform.py`: the deflator join, the
real values, per-capita, the Gini series, the policy-era labels, the convergence
regressions. The model contains **31 measures and zero calculated columns**.

The split is the standard one — a value fixed for a row is a column, a value that
depends on the reader's selection is a measure — applied one layer further back. If
the pipeline that built the row could have written the value down, neither a column
nor a measure should be computing it.

The Gini is the clearest case, and the reason is not only performance. A Gini
computed in DAX would respond to the region slicer, so a reader selecting four
regions would get the inequality among those four, displayed under a label saying
"Gini". Computing it upstream makes it a property of the year, which is what it is.

### What this draws on

- Robert Barro and Xavier Sala-i-Martin, *Economic Growth* (1992). Beta-convergence
  and the initial-level regression used on page three
- Edward Tufte, *The Visual Display of Quantitative Information* (1983). Data-ink,
  and the case against the choropleth
- Colin Ware, *Information Visualization: Perception for Design*. Preattentive
  attributes; why fixed colour encoding survives skimming
- Stephen Few, *Information Dashboard Design* (2006)
- Nielsen Norman Group, *F-Shaped Pattern for Reading Web Content* (2006)

---

## Publishing

Publish to the Power BI Service, then Share → Publish to web (public) for a link that
needs no sign-in. The report reads static CSVs, so it needs no gateway and no
scheduled refresh — a refresh means re-running the pipeline and republishing.

Save the `.pbix` to this folder and add the screenshots to `powerbi/images/`.

## Contents

```
dax/measures.md         every measure, with the reasoning
theme/                  report theme as JSON
images/                 report screenshots
README.md               this file
```
