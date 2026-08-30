# Visual catalogue

What belongs in a country economic dashboard, why, and the exact fields that support
each visual.

The structure follows the World Bank Country Economic Update and Systematic Country
Diagnostic for Uzbekistan, and the IMF Article IV. Those documents converge on a block
order — real sector, prices, external, labour, living standards — and on two
conventions this project had been missing: **opening with contributions to growth
rather than levels**, and **drawing nearly every figure against peers.**

The one block they do not have is the regional panel. That is where this project adds
rather than reproduces.

---

## Part 1 — The evidence behind the structure

| Source | What it does | What it implies here |
|---|---|---|
| **WB Country Economic Update** | 11 figures: sectoral contributions → inflation → BoP → trade structure → financial → employment by sector → GDP p.c. and poverty → budget → debt | The block order, and that Figure 1 is a *contributions* chart |
| **WB Systematic Country Diagnostic** | 60 figures, ~a quarter titled "vs. Peers" or "vs. Selected Countries". Figure 31 charts ICOR directly | Benchmark everything; ICOR is a first-class indicator |
| **IMF 2024 Article IV** | "Rapid investment growth has not been associated with acceleration of TFP beyond the 1–2 percent rates observed over 2012–16" | Growth accounting is the diagnostic, and our 1.81 for 2017–19 lands inside their range |
| **WB CEM 2025** | Raising TFP "central" to upper-middle-income by 2030 | TFP is the headline number, not a footnote |
| **OECD Regional Outlook** | Subnational convergence and productivity | Validates the regional block as a real genre |

---

## Part 2 — Visual grammar

| Visual | Use for | Avoid for |
|---|---|---|
| **Stacked column, signed** | Contributions summing to a total — the opening chart | Shares that do not sum to a meaningful whole |
| **KPI card + sparkline + delta** | The five numbers a reader must leave with | Anything needing context to read |
| **Line** | Levels and indices | More than ~5 series |
| **Column with zero line** | Growth *rates*, where sign matters | Levels |
| **Indexed line, base = 100** | Series in different units | When magnitude is the point |
| **100% stacked area** | Composition over time | When the total also matters |
| **Ranked horizontal bar** | Regions or peers in one year | Time series |
| **Dumbbell / slope** | Change between exactly two years | More than two periods |
| **Scatter + fitted line** | A claimed relationship | Anything where time is the real variable |
| **Choropleth** | *Where*, when geography is the point | *How much* — area encodes territory |
| **Heatmap, entity × year** | Which unit and which year broke pattern | Precise reading of a cell |
| **Error band / range** | Sensitivity of an assumption-dependent estimate | Observed data |

Two conventions the macro reader expects: **regime shading** (`Year[policy_era]`,
`Year[currency_era]`) and **a visible zero line on every rate chart**.

---

## Part 3 — The catalogue

`[Brackets]` are measures; everything else is a column. New tables from the analytics
layer are marked **new**.

### Page 1 — Growth and its sources

*Is the economy growing, what is the growth made of, and how does that compare?*

**1.1 KPI row** — five cards, sparkline and YoY delta on each.

| Card | Field |
|---|---|
| Real GDP growth | `fact_growth_accounting[real_growth_pct]` **new** |
| TFP contribution | `fact_growth_accounting[tfp_contrib]` **new** |
| Investment, % of GDP | `fact_investment_efficiency[investment_pct_gdp]` **new** |
| GNI per capita, Atlas | `wb_gni_per_capita_atlas` |
| Population | `wb_population` |

**1.2 Contributions to real GDP growth, by sector.** Stacked column with a zero line.
`fact_sector_contributions` **new** — `year` × `Agriculture`, `Industry`, `Services`,
with `total_growth_pct` as a line overlay.

This is the World Bank's Figure 1 and it is the right opening: contributions sum to
the growth rate, so it answers where growth came from rather than which sector grew.

**Filter `shares_reliable = TRUE`, or break the series at 2017.** The World Bank's
2017 sector shares for Uzbekistan sum to 77.7% against ~92% in adjacent years, and
industry alone drops 11pp then rebounds 16pp. Plotting it produces a −11 / +18
contribution swing that is a reporting error, not an economy.

**1.3 Growth accounting: capital, labour, TFP.** Stacked column, `fact_growth_accounting`
**new** — `capital_contrib`, `labour_contrib`, `tfp_contrib`, summing to
`real_growth_pct`.

The report's central chart. The capital contribution rises from 0.54 (1996–2007) to
2.90 (2017–19) while TFP falls from 4.19 to 1.81. Growth held; its engine changed.

**1.4 Sensitivity band.** Small range chart or a caption. `fact_growth_sensitivity`
**new** — TFP contribution across α ∈ {0.30, 0.40} and δ ∈ {0.04, 0.07} moves only
between 2.40 and 2.66.

Show it. A TFP residual is only as good as the capital-stock assumptions behind it,
and a reader is entitled to see how far the answer moves. That it barely moves is the
point.

**1.5 Real GDP per capita vs peers.** Line, `fact_benchmark` **new** filtered to
`wb_real_gdp_per_capita`, `dim_country[country_name]` as the series.
Highlight Uzbekistan; grey the peers. Use `dim_country[peer_group]` to switch between
post-Soviet peers, reform comparators and the three aggregates.

---

### Page 2 — The price of growth

*What does each point of growth now cost?*

**2.1 ICOR against the investment share.** Dual line, `fact_investment_efficiency`
**new** — `investment_pct_gdp` and `icor` by year.

Investment rises from ~25% to ~35% of GDP while ICOR goes 4.42 → 5.11. The same
growth costs more capital every year. **Filter or mark `is_outlier`** — five years of
near-zero or negative growth send the ratio meaningless.

**2.2 Capital-output ratio.** Line, `fact_growth_accounting[capital_output_ratio]`
**new**. Capital deepening, the mechanism behind 2.1.

**2.3 Investment share vs peers.** Ranked bar or line, `fact_benchmark` filtered to
`wb_capital_formation_pct_gdp`. Uzbekistan invests more of its output than almost any
comparator — which is the finding, given 2.1.

**2.4 Shift-share: within vs between.** Stacked bar by period, `fact_shift_share`
**new** — `within_pct`, `between_pct`, `interaction_pct`.

Between-sector contribution runs 2.9% → 0.9% → **−0.6%**. Sectors improve; labour does
not move to where output per worker is higher. This is the World Bank's *"limited
intersectoral shifts in employment from less to more productive sectors"*, computed
rather than quoted.

**2.5 Employment by sector.** 100% stacked area, `wb_employment_agriculture_pct`,
`wb_employment_industry_pct`, `wb_employment_services_pct`. The other half of 2.4.

**2.6 Nominal vs real GDP, indexed.** Line, `[GDP Real Indexed]`, `[GDP Nominal Indexed]`.

Now a supporting exhibit, not the thesis. It earns its place here as the reason
everything on pages 1 and 2 is computable at all: 91.3% of published growth is the
price level, and none of the above can be done on nominal series.

---

### Page 3 — Prices, external, labour

**3.1 Inflation vs peers.** Line, `fact_benchmark` / `wb_inflation_cpi_pct`.
**3.2 Deflator vs CPI**, both 2010 = 100. `Year[gdp_deflator]`, `Year[cpi]`.
**3.3 Exchange rate**, log axis. `Year[exchange_rate_uzs_usd]`. Annotate Sept 2017.
**3.4 Current account, FDI, remittances.** Line. `wb_current_account_pct_gdp`,
`wb_fdi_pct_gdp`, `wb_remittances_pct_gdp`.
**3.5 Fiscal balance.** Column. `wb_revenue_pct_gdp`, `wb_expense_pct_gdp`,
`wb_net_lending_pct_gdp` — 2011–2023 only, so mark the window.
**3.6 Okun's law.** Scatter, 14-region panel: regional real GDP growth against the
change in the regional unemployment rate. Coefficient **−0.044** (p = 0.010) against a
typical −0.3: growth barely moves unemployment.
**3.7 Participation and dependency.** Line. `wb_participation_pct`,
`wb_participation_female_pct`, `wb_dependency_ratio`.

---

### Page 4 — Regional

*The block no institutional report carries.*

**4.1 Beta-convergence scatter** + `Convergence[period]` slicer.
`ConvergencePoints[log_initial]` × `[annual_growth_pct]`, labelled by `region_short`.
Slope flips sign: β = −0.023 (p = .040) pre-reform, +0.059 (p = .002) post-float. The
pooled period reports nothing at p = 0.052 — leave that state in the slicer, it is the
methodological finding.

**4.2 Map**, real GDP per capita. Set Data Category to State/Province; if geocoding
fails use Shape Map with a TopoJSON of the viloyatlar. Read as *where*, never *how
much* — Navoi is largest by area and nearly smallest by population.

**4.3 Regions ranked**, real GDP per capita, latest year. The honest companion to 4.2.

**4.4 Two Ginis.** `[Gini (real GDP per capita)]` and `[Gini (nominal GDP levels)]`.
Showing both makes the measurement choice visible.

**4.5 Region × year heatmap.** Matrix, `region_short` × `year`, `[GDP Real Growth %]`.

**4.6 Regional shares of national GDP.** 100% stacked area or treemap.

---

### Page 5 (hidden) — Region detail, drillthrough on `Region[region_name]`

Small multiples against the national path. Heading bound to
`SELECTEDVALUE('Region'[region_name])`.

---

### Page 6 — Sources and method

A table off `dim_metric`: `metric_name`, `official_code`, `unit_raw`, `price_basis`,
`source`, `periodicity`, `methodology_url`. Plus:

- **The α and δ assumptions**, with the sensitivity table
- **The two data-quality catches**: stat.uz publishing two indicators from one URL, and
  the World Bank's 2017 sector shares failing to sum
- **The reconciliation**: deflated GDP growth against World Bank published real growth,
  0.000pp mean absolute gap over 14 years

This is where the warehouse and the economics visibly meet. `price_basis`,
`is_deflatable`, `is_national` and `grain` are four columns that encode domain
knowledge into the schema rather than bolting it onto the charts.

---

## Part 4 — What to leave out

Pie charts. Dual axes pairing unrelated series. Gauges. A map as the hero. Nominal soum
series without a real counterpart. Any chart type chosen for variety.

**6–8 visuals per page.** Every visual is a query.

---

## Part 5 — Traps in this model

| Trap | What happens | Fix |
|---|---|---|
| Missing `Region[is_national] = False` | Regional totals double — 1700 is the Republic, in the same column as its 14 regions | Visual-level filter on every regional visual |
| Dragging `Fact[value]` | Sums soums, dollars, kWh, people, percentages | Use measures; `value` is *Do not summarize* |
| No metric filter on `Value (…)` | Blank — the unit guard firing correctly | Always filter `Metric[metric_code]` |
| Mixing `grain` regional and national | 1987–2009 has no regional data | Filter `Year[has_regional_data]` |
| `value` across years | Measures inflation | Use `real_value` |
| Sector contributions at 2017 | −11 / +18 artefact | `shares_reliable = TRUE` |
| ICOR at low-growth years | Meaningless or negative | `is_outlier = FALSE` |
| Peer charts without `dim_country` | Aggregates plotted as countries | Filter `is_aggregate` |
| Fiscal series before 2011 | Empty axis | Window to 2011–2023 |

---

## Part 6 — Model additions still needed

The analytics tables are not in the Power BI model yet. Load and relate:

| Table | Relate on | Notes |
|---|---|---|
| `fact_growth_accounting` | `year` → `Year[year]` | one row per year |
| `fact_investment_efficiency` | `year` → `Year[year]` | |
| `fact_sector_contributions` | `year` → `Year[year]` | unpivot the three sectors for a stacked chart |
| `fact_growth_sensitivity` | none — disconnected | 4 rows, read directly |
| `fact_shift_share` | none — disconnected | 4 rows, one per period |
| `fact_benchmark` | `year` → `Year[year]`, `country_code` → `dim_country` | 5,907 rows |
| `dim_country` | to `fact_benchmark` | 13 entities |

`fact_sector_contributions` arrives wide (one column per sector). Unpivot it in Power
Query to `year / sector / contribution_pp` so one stacked column chart can read it.

---

## Build order

Start with 1.3, the growth accounting stack. It is the report's central claim, it uses
a new table, and if it renders correctly the analytics layer is wired correctly.
Then 1.2, then page 2, then the peers, then regional.

Theme last: **View → Themes → Browse** → `powerbi/theme/Uzbekistan_theme.json`.
Real is teal `#0E6E64`, nominal is orange `#C4622D`, everywhere, without exception.
