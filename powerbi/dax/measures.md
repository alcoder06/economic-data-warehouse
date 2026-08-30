# DAX reference

Every measure in the model, with the reasoning where a choice was not obvious.

Tables are renamed on load to what they hold rather than to the file they came from:
`Fact` is `fact_economic`, `Metric`, `Region` and `Year` are the three dimensions,
`Convergence` is the three-row regression summary, and `_Measure` is an empty table
that exists only to hold measures.

---

## The problem every measure here is working around

The fact table is tall. One `value` column carries all thirty-seven indicators, and
those indicators are measured in billions of soums, millions of dollars, millions of
kilowatt-hours, persons, percentages and index points.

Nothing in Power BI stops a reader dragging `value` onto a card. Doing so returns the
sum of soums, dollars, people and percentages, which is a number with no meaning
presented with the same authority as any other. The model has to make that hard.

Two mechanisms do it, and between them they account for most of what follows:

- **No implicit measures.** Every numeric column in `Fact` is set to *Summarization:
  Do not summarize*, so dragging a raw column produces a column of values rather than
  a total. Aggregation happens only through the measures below.
- **A unit guard.** Measures that could span metrics return `BLANK()` when more than
  one metric is in filter context, rather than adding incompatible units together.

---

## Base measures

### Value (nominal)

```dax
Value (nominal) =
VAR MetricsInScope = DISTINCTCOUNT('Metric'[metric_id])
RETURN
    IF(MetricsInScope > 1, BLANK(), SUM('Fact'[value]))
```

The unit guard. One metric in context returns its total; more than one returns blank,
because there is no correct way to add billion soums to percentage points.

Blank rather than an error message, because a blank card reads as "this combination
has no answer" and stops the reader, while an error reads as a broken report and
sends them to ask whether the data is loaded.

### Value (real)

```dax
Value (real) =
VAR MetricsInScope = DISTINCTCOUNT('Metric'[metric_id])
RETURN
    IF(MetricsInScope > 1, BLANK(), SUM('Fact'[real_value]))
```

Constant 2010 soums. Returns blank for the twenty-eight metrics that are not
current-price soum series, and that blank is deliberate rather than a gap: a
percentage has no real counterpart, and a dollar series deflated by a soum deflator
would be worse than the nominal figure it replaced.

`real_value` is computed in `gold_transform.py`, not here. It is a fixed property of
a row, so it is a column, computed once at refresh and compressed with the rest of
the table. Deriving it in DAX would recompute it on every interaction to get the same
answer.

### Value (real per capita)

```dax
Value (real per capita) =
VAR MetricsInScope = DISTINCTCOUNT('Metric'[metric_id])
RETURN
    IF(MetricsInScope > 1, BLANK(), SUM('Fact'[real_value_per_capita]))
```

---

## National GDP

The headline series, pinned to one metric and to the Republic total so the measure
means the same thing wherever it is used.

```dax
GDP Nominal =
CALCULATE(
    SUM('Fact'[value]),
    'Metric'[metric_code] = "regional_gdp",
    'Region'[is_national] = TRUE
)

GDP Real =
CALCULATE(
    SUM('Fact'[real_value]),
    'Metric'[metric_code] = "regional_gdp",
    'Region'[is_national] = TRUE
)
```

`'Region'[is_national] = TRUE` is doing real work. `region_code` 1700 is the Republic
total and sits in the same column as the fourteen regions that sum to it, so a
measure that does not pin the region returns the country counted twice whenever no
region slicer is applied.

This is the single most common way to get a wrong number out of this model, and it is
wrong quietly: the figure is plausible, just double.

---

## Growth

### Why there is no date table

The grain is the year. There are no months, no quarters and no dates, so `Year` is a
table of integers rather than a date dimension, and the model has Auto Date/Time
switched off.

That rules out `SAMEPERIODLASTYEAR` and `DATEADD`, which need a marked date table.
The replacement is to subtract one from the year, which is what those functions would
have done anyway:

```dax
GDP Real Growth % =
VAR ThisYear = MAX('Year'[year])
VAR Current  = [GDP Real]
VAR Previous =
    CALCULATE([GDP Real], REMOVEFILTERS('Year'), 'Year'[year] = ThisYear - 1)
RETURN
    DIVIDE(Current - Previous, Previous)
```

`GDP Nominal Growth %` and the two investment equivalents follow the same shape.

`REMOVEFILTERS('Year')` before re-applying the year is the part that is easy to
leave out and wrong to. Page one carries a page-level filter of 2010 to 2024, so
without it the lookup for the previous year is intersected with that window and
2009 is unreachable from 2010 — every year at the left edge of any selection
returns blank. Clear the table first, then name the single year wanted, and the
measure answers the same way regardless of what the page or a slicer has narrowed
to.

`MAX` rather than `SELECTEDVALUE` for the same reason: it returns the last year in
context instead of blanking whenever more than one is present, which keeps the
measure usable in a total row and in a visual whose axis groups years.

Adding a date table to gain time intelligence the model cannot use would cost a
table, a relationship and a hidden trap: Auto Date/Time silently creates a date
hierarchy per date column, and on a model this small that overhead is a larger share
of it than the data.

`DIVIDE` throughout, so the first year of the series returns blank instead of
dividing by a missing previous year.

---

## The nominal illusion

These four carry the report's central argument.

### Price Level Multiple

```dax
Price Level Multiple =
VAR FirstYear = MIN('Year'[year])
VAR LastYear  = MAX('Year'[year])
VAR First = CALCULATE(MAX('Year'[gdp_deflator]), 'Year'[year] = FirstYear)
VAR Last  = CALCULATE(MAX('Year'[gdp_deflator]), 'Year'[year] = LastYear)
RETURN
    DIVIDE(Last, First)
```

How much the price level rose across whatever period is selected. Over 2010-2024 it
returns 7.17: prices multiplied sevenfold.

`MAX` over the deflator column rather than `SUM`, because the deflator is one value
per year and summing a selection of years would add index points together.

### Real Growth Multiple and Nominal Growth Multiple

```dax
Nominal Growth Multiple =
VAR FirstYear = MIN('Year'[year])
VAR LastYear  = MAX('Year'[year])
RETURN
    DIVIDE(
        CALCULATE([GDP Nominal], 'Year'[year] = LastYear),
        CALCULATE([GDP Nominal], 'Year'[year] = FirstYear)
    )

Real Growth Multiple =
VAR FirstYear = MIN('Year'[year])
VAR LastYear  = MAX('Year'[year])
RETURN
    DIVIDE(
        CALCULATE([GDP Real], 'Year'[year] = LastYear),
        CALCULATE([GDP Real], 'Year'[year] = FirstYear)
    )
```

17.43 and 2.43 respectively over 2010-2024.

### Share of Growth That Is Price

```dax
Share of Growth That Is Price =
VAR NominalGrowth = [Nominal Growth Multiple] - 1
VAR RealGrowth    = [Real Growth Multiple] - 1
RETURN
    IF(
        NominalGrowth > 0,
        1 - DIVIDE(RealGrowth, NominalGrowth)
    )
```

The headline number: **0.913**. Of the 1,643 per cent rise in nominal GDP between
2010 and 2024, 91.3 per cent is the price level and 8.7 per cent is output.

Subtracting one from each multiple before dividing matters. The ratio of the
multiples (2.43 / 17.43 = 0.14) answers a different question, and the difference
between them is the difference between "real output is 14 per cent of nominal" and
"9 per cent of the growth was real". The second is the one a reader wants.

The `IF` guards a selection with no growth to decompose.

### The two indexed series

```dax
GDP Nominal Indexed =
VAR BaseYear  = CALCULATE(MIN('Year'[year]), ALLSELECTED('Year'))
VAR BaseValue = CALCULATE([GDP Nominal], 'Year'[year] = BaseYear, ALLSELECTED('Year'))
RETURN
    DIVIDE([GDP Nominal], BaseValue) * 100
```

`GDP Real Indexed` is the same shape against `[GDP Real]`.

Both rebase to 100 at the first year *in the current selection*, which is what makes
the hero chart work: the two lines start together, and everything after that is the
gap the page exists to show. Plotting the raw series instead would put one line in
billions of soums and the other in a different-sized billions of soums, and the
reader would be comparing two quantities that were never on the same scale.

`ALLSELECTED` rather than `ALL`. `ALL` would ignore the year slicer and always index
to 1987, so a reader narrowing to 2015-2024 would get a chart that starts at 400
rather than 100. `ALLSELECTED` respects the slicer while ignoring the axis, which is
the distinction the base year needs.

---

## The spurious correlation

The finding that a nominal series and a real series can tell opposite stories, in a
form a reader can check by toggling one slicer.

```dax
Corr GDP vs Investment =
VAR UseReal = SELECTEDVALUE('Price Basis'[Basis], "Real") = "Real"
VAR Pairs =
    ADDCOLUMNS(
        FILTER(
            VALUES('Year'[year]),
            'Year'[year] >= 2011 && 'Year'[year] <= 2024
        ),
        "@GDP",
            IF(UseReal,
                CALCULATE([GDP Real Growth %]),
                CALCULATE([GDP Nominal Growth %])),
        "@Inv",
            IF(UseReal,
                CALCULATE([Investment Real Growth %]),
                CALCULATE([Investment Nominal Growth %]))
    )
VAR Clean  = FILTER(Pairs, NOT ISBLANK([@GDP]) && NOT ISBLANK([@Inv]))
VAR N      = COUNTROWS(Clean)
VAR MeanX  = AVERAGEX(Clean, [@GDP])
VAR MeanY  = AVERAGEX(Clean, [@Inv])
VAR Cov    = SUMX(Clean, ([@GDP] - MeanX) * ([@Inv] - MeanY))
VAR SdX    = SQRT(SUMX(Clean, ([@GDP] - MeanX) ^ 2))
VAR SdY    = SQRT(SUMX(Clean, ([@Inv] - MeanY) ^ 2))
RETURN
    IF(N > 2, DIVIDE(Cov, SdX * SdY))
```

Returns **+0.674** on nominal values and **+0.036** on real ones.

Both series are denominated in soums, and over this period the soum lost most of its
value. Two series inflating together correlate whether or not either drives the
other, so the nominal figure is measuring the shared price trend. Deflate both and
almost nothing is left.

Three things in the implementation are worth noting.

`ADDCOLUMNS` over `VALUES('Year'[year])` builds the pairs one year at a time, so each
`CALCULATE` runs in a single-year filter context and the growth measures return a
scalar. Calling them outside that iteration would evaluate them once over the whole
selection and correlate two numbers, which is not a correlation.

The `2011` lower bound is not cosmetic. 2010 is the first year of the series, so its
growth rate is blank, and a blank treated as zero would pull both means toward zero
and inflate the coefficient.

`'Price Basis'` is a one-column disconnected table holding "Nominal" and "Real". It
filters nothing; it is read with `SELECTEDVALUE` to switch the measure's behaviour.
That is what puts the toggle in the reader's hands, which is the point: the claim is
more convincing when they flip it themselves than when they are told the answer.

### Investment growth

```dax
Investment Nominal =
CALCULATE(SUM('Fact'[value]),
    'Metric'[metric_code] = "fixed_capital_investment", 'Region'[is_national] = TRUE)

Investment Real =
CALCULATE(SUM('Fact'[real_value]),
    'Metric'[metric_code] = "fixed_capital_investment", 'Region'[is_national] = TRUE)

Investment Real Growth % =
VAR ThisYear = SELECTEDVALUE('Year'[year])
RETURN
    DIVIDE(
        [Investment Real] - CALCULATE([Investment Real], 'Year'[year] = ThisYear - 1),
        CALCULATE([Investment Real], 'Year'[year] = ThisYear - 1)
    )
```

`Investment Nominal Growth %` follows the same shape against `[Investment Nominal]`.

### The switched axis measures

```dax
GDP Growth (selected basis) =
VAR UseReal = SELECTEDVALUE('Price Basis'[Basis], "Real") = "Real"
RETURN
    IF(UseReal, [GDP Real Growth %], [GDP Nominal Growth %])
```

`Investment Growth (selected basis)` is the same against the investment pair.

These are what the scatter's X and Y are actually bound to. Without them the toggle
would change the correlation card while the points stayed put, which would look like
a bug and would undercut the demonstration — the whole value of the interaction is
that the cloud visibly scatters as the coefficient collapses.

Defaulting to `"Real"` when nothing is selected, so the report opens on the correct
figure rather than the misleading one.

---

## Regional inequality

The Gini coefficients are columns on `Year`, computed in `gold_transform.py`. A Gini
needs the entire cross-section of a year sorted before it yields one number: cheap in
pandas, awkward and slow in DAX, and — decisively — it is a fixed property of a year
rather than something that should respond to a region slicer. Computing it in the
report would let a reader select four regions and get "the Gini", which would be the
inequality among those four and would be read as the inequality of the country.

```dax
Gini (real GDP per capita) = AVERAGE('Year'[gini_real_gdp_pc])
Gini (nominal GDP levels)  = AVERAGE('Year'[gini_nominal_levels])
Regional Dispersion        = AVERAGE('Year'[sigma_log_dispersion])
```

`AVERAGE` rather than `SUM`, so a multi-year selection returns the mean of the annual
coefficients instead of their total, which would be meaningless and large.

Both Ginis are exposed because the contrast is the point. On nominal levels
inequality drifts from 0.275 to 0.328 and looks like slow structural change. On real
GDP per capita it falls from 0.215 to 0.191 and then climbs to 0.325, which is a
different shape with a turning point in it. The first measure is partly counting
which regions are populous and how much the price level rose.

### Region Share of National

```dax
Region Share of National % =
VAR RegionValue = [Value (real)]
VAR NationalValue =
    CALCULATE([Value (real)], 'Region'[is_national] = TRUE, REMOVEFILTERS('Region'))
RETURN
    DIVIDE(RegionValue, NationalValue)
```

`REMOVEFILTERS('Region')` before re-applying `is_national` is required rather than
tidy. Without it the two filters intersect, and a page filtered to Samarkand asks for
rows that are both Samarkand and the national total. There are none, the denominator
is blank, and `DIVIDE` returns blank for every row — a chart that renders empty with
no error to explain why.

---

## Convergence

`Convergence` is a three-row table with no relationship to anything else. It is read
directly rather than aggregated, because each row is a completed regression.

```dax
Beta Coefficient = SELECTEDVALUE('Convergence'[beta])
Beta P Value     = SELECTEDVALUE('Convergence'[p_value])
Convergence Verdict = SELECTEDVALUE('Convergence'[verdict], "Select one period")

Convergence Verdict Colour =
SWITCH(
    SELECTEDVALUE('Convergence'[verdict]),
    "convergence", "#2E7D5B",
    "divergence",  "#B33A3A",
    "#4A5761"
)
```

`SELECTEDVALUE` with a fallback, so the card explains itself when several periods are
selected instead of silently showing one of them.

The colour measure is a rules-based lookup rather than a gradient. A gradient on a
regression coefficient would say only that darker is larger; the categories say which
direction is which, which is the thing the reader needs.

---

## Dynamic titles

```dax
Convergence Title =
VAR Period = SELECTEDVALUE('Convergence'[period])
VAR Beta   = SELECTEDVALUE('Convergence'[beta])
VAR P      = SELECTEDVALUE('Convergence'[p_value])
RETURN
    IF(
        ISBLANK(Period),
        "Regional convergence: select a period",
        Period & " (" & SELECTEDVALUE('Convergence'[start_year]) & "-" &
        SELECTEDVALUE('Convergence'[end_year]) & "): beta = " &
        FORMAT(Beta, "+0.000") & ", p = " & FORMAT(P, "0.000")
    )

Price Basis Title =
"National GDP, " &
LOWER(SELECTEDVALUE('Price Basis'[Basis], "real")) &
" terms, " & MIN('Year'[year]) & "-" & MAX('Year'[year])
```

A title that restates the current filter state costs one measure and removes the
commonest way to misread a screenshot, which is not knowing what was selected when it
was taken.

---

## Measure count

| | |
|---|---|
| Base measures with unit guard | 3 |
| Metric-pinned totals | 4 |
| Growth rates | 4 |
| Nominal illusion, including the two indexed series | 6 |
| Correlation, including the two switched axis measures | 3 |
| Inequality | 4 |
| Convergence | 5 |
| Dynamic titles | 2 |
| **Total** | **31** |

Calculated columns: none. Everything a row-level calculation would have produced —
`real_value`, `value_per_capita`, the deflator, the Gini series, the policy era
labels — is computed in `gold_transform.py` and arrives as data.

That is the same split Power BI's own guidance recommends, applied one layer further
back. A calculated column costs memory once at refresh; a measure costs time on every
interaction. A value that is fixed for a row should be neither, if the pipeline that
built the row could have written it down.
