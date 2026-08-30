// ============================================================================
// Uzbekistan Economic Analysis - create all measures in one pass.
//
// Run in Tabular Editor 2 (free): File > Preferences > Allow unsupported Power BI
// features, then connect to the running Power BI Desktop instance, paste this into
// the C# Script tab and press F5. Then Model > Save to connected database (Ctrl+S)
// and switch back to Desktop.
//
// Re-runnable: an existing measure of the same name is updated rather than
// duplicated, so fixing one measure means editing here and running the whole file
// again.
// ============================================================================

var target = Model.Tables["_Measure"];

Action<string, string, string, string> upsert = (name, expression, folder, format) =>
{
    Measure m = target.Measures.FirstOrDefault(x => x.Name == name);
    if (m == null) m = target.AddMeasure(name);
    m.Expression      = expression;
    m.DisplayFolder   = folder;
    if (!string.IsNullOrEmpty(format)) m.FormatString = format;
};

upsert(
    @"Value (nominal)",
    @"VAR MetricsInScope = DISTINCTCOUNT('Metric'[metric_id])
RETURN
    IF(MetricsInScope > 1, BLANK(), SUM('Fact'[value]))",
    @"1 Base",
    @"#,##0.0");

upsert(
    @"Value (real)",
    @"VAR MetricsInScope = DISTINCTCOUNT('Metric'[metric_id])
RETURN
    IF(MetricsInScope > 1, BLANK(), SUM('Fact'[real_value]))",
    @"1 Base",
    @"#,##0.0");

upsert(
    @"Value (real per capita)",
    @"VAR MetricsInScope = DISTINCTCOUNT('Metric'[metric_id])
RETURN
    IF(MetricsInScope > 1, BLANK(), SUM('Fact'[real_value_per_capita]))",
    @"1 Base",
    @"#,##0.0000");

upsert(
    @"GDP Nominal",
    @"CALCULATE(
    SUM('Fact'[value]),
    'Metric'[metric_code] = ""regional_gdp"",
    'Region'[is_national] = TRUE
)",
    @"2 National",
    @"#,##0");

upsert(
    @"GDP Real",
    @"CALCULATE(
    SUM('Fact'[real_value]),
    'Metric'[metric_code] = ""regional_gdp"",
    'Region'[is_national] = TRUE
)",
    @"2 National",
    @"#,##0");

upsert(
    @"Investment Nominal",
    @"CALCULATE(
    SUM('Fact'[value]),
    'Metric'[metric_code] = ""fixed_capital_investment"",
    'Region'[is_national] = TRUE
)",
    @"2 National",
    @"#,##0");

upsert(
    @"Investment Real",
    @"CALCULATE(
    SUM('Fact'[real_value]),
    'Metric'[metric_code] = ""fixed_capital_investment"",
    'Region'[is_national] = TRUE
)",
    @"2 National",
    @"#,##0");

upsert(
    @"GDP Nominal Growth %",
    @"VAR ThisYear = SELECTEDVALUE('Year'[year])
VAR Current  = [GDP Nominal]
VAR Previous = CALCULATE([GDP Nominal], 'Year'[year] = ThisYear - 1)
RETURN
    DIVIDE(Current - Previous, Previous)",
    @"3 Growth",
    @"0.0%");

upsert(
    @"GDP Real Growth %",
    @"VAR ThisYear = SELECTEDVALUE('Year'[year])
VAR Current  = [GDP Real]
VAR Previous = CALCULATE([GDP Real], 'Year'[year] = ThisYear - 1)
RETURN
    DIVIDE(Current - Previous, Previous)",
    @"3 Growth",
    @"0.0%");

upsert(
    @"Investment Nominal Growth %",
    @"VAR ThisYear = SELECTEDVALUE('Year'[year])
VAR Current  = [Investment Nominal]
VAR Previous = CALCULATE([Investment Nominal], 'Year'[year] = ThisYear - 1)
RETURN
    DIVIDE(Current - Previous, Previous)",
    @"3 Growth",
    @"0.0%");

upsert(
    @"Investment Real Growth %",
    @"VAR ThisYear = SELECTEDVALUE('Year'[year])
VAR Current  = [Investment Real]
VAR Previous = CALCULATE([Investment Real], 'Year'[year] = ThisYear - 1)
RETURN
    DIVIDE(Current - Previous, Previous)",
    @"3 Growth",
    @"0.0%");

upsert(
    @"Price Level Multiple",
    @"VAR FirstYear = MIN('Year'[year])
VAR LastYear  = MAX('Year'[year])
VAR First = CALCULATE(MAX('Year'[gdp_deflator]), 'Year'[year] = FirstYear)
VAR Last  = CALCULATE(MAX('Year'[gdp_deflator]), 'Year'[year] = LastYear)
RETURN
    DIVIDE(Last, First)",
    @"4 Nominal illusion",
    @"0.00""x""");

upsert(
    @"Nominal Growth Multiple",
    @"VAR FirstYear = MIN('Year'[year])
VAR LastYear  = MAX('Year'[year])
RETURN
    DIVIDE(
        CALCULATE([GDP Nominal], 'Year'[year] = LastYear),
        CALCULATE([GDP Nominal], 'Year'[year] = FirstYear)
    )",
    @"4 Nominal illusion",
    @"0.00""x""");

upsert(
    @"Real Growth Multiple",
    @"VAR FirstYear = MIN('Year'[year])
VAR LastYear  = MAX('Year'[year])
RETURN
    DIVIDE(
        CALCULATE([GDP Real], 'Year'[year] = LastYear),
        CALCULATE([GDP Real], 'Year'[year] = FirstYear)
    )",
    @"4 Nominal illusion",
    @"0.00""x""");

upsert(
    @"Share of Growth That Is Price",
    @"VAR NominalGrowth = [Nominal Growth Multiple] - 1
VAR RealGrowth    = [Real Growth Multiple] - 1
RETURN
    IF(
        NominalGrowth > 0,
        1 - DIVIDE(RealGrowth, NominalGrowth)
    )",
    @"4 Nominal illusion",
    @"0.0%");

upsert(
    @"GDP Nominal Indexed",
    @"VAR BaseYear = CALCULATE(MIN('Year'[year]), ALLSELECTED('Year'))
VAR BaseValue = CALCULATE([GDP Nominal], 'Year'[year] = BaseYear, ALLSELECTED('Year'))
RETURN
    DIVIDE([GDP Nominal], BaseValue) * 100",
    @"4 Nominal illusion",
    @"#,##0");

upsert(
    @"GDP Real Indexed",
    @"VAR BaseYear = CALCULATE(MIN('Year'[year]), ALLSELECTED('Year'))
VAR BaseValue = CALCULATE([GDP Real], 'Year'[year] = BaseYear, ALLSELECTED('Year'))
RETURN
    DIVIDE([GDP Real], BaseValue) * 100",
    @"4 Nominal illusion",
    @"#,##0");

upsert(
    @"Corr GDP vs Investment",
    @"VAR UseReal = SELECTEDVALUE('Price Basis'[Basis], ""Real"") = ""Real""
VAR Pairs =
    ADDCOLUMNS(
        FILTER(
            VALUES('Year'[year]),
            'Year'[year] >= 2011 && 'Year'[year] <= 2024
        ),
        ""@GDP"", IF(UseReal, CALCULATE([GDP Real Growth %]), CALCULATE([GDP Nominal Growth %])),
        ""@Inv"", IF(UseReal, CALCULATE([Investment Real Growth %]), CALCULATE([Investment Nominal Growth %]))
    )
VAR Clean = FILTER(Pairs, NOT ISBLANK([@GDP]) && NOT ISBLANK([@Inv]))
VAR N     = COUNTROWS(Clean)
VAR MeanX = AVERAGEX(Clean, [@GDP])
VAR MeanY = AVERAGEX(Clean, [@Inv])
VAR Cov   = SUMX(Clean, ([@GDP] - MeanX) * ([@Inv] - MeanY))
VAR SdX   = SQRT(SUMX(Clean, ([@GDP] - MeanX) ^ 2))
VAR SdY   = SQRT(SUMX(Clean, ([@Inv] - MeanY) ^ 2))
RETURN
    IF(N > 2, DIVIDE(Cov, SdX * SdY))",
    @"5 Correlation",
    @"+0.000;-0.000");

upsert(
    @"GDP Growth (selected basis)",
    @"VAR UseReal = SELECTEDVALUE('Price Basis'[Basis], ""Real"") = ""Real""
RETURN
    IF(UseReal, [GDP Real Growth %], [GDP Nominal Growth %])",
    @"5 Correlation",
    @"0.0%");

upsert(
    @"Investment Growth (selected basis)",
    @"VAR UseReal = SELECTEDVALUE('Price Basis'[Basis], ""Real"") = ""Real""
RETURN
    IF(UseReal, [Investment Real Growth %], [Investment Nominal Growth %])",
    @"5 Correlation",
    @"0.0%");

upsert(
    @"Gini (real GDP per capita)",
    @"AVERAGE('Year'[gini_real_gdp_pc])",
    @"6 Regional",
    @"0.000");

upsert(
    @"Gini (nominal GDP levels)",
    @"AVERAGE('Year'[gini_nominal_levels])",
    @"6 Regional",
    @"0.000");

upsert(
    @"Regional Dispersion",
    @"AVERAGE('Year'[sigma_log_dispersion])",
    @"6 Regional",
    @"0.000");

upsert(
    @"Region Share of National %",
    @"VAR RegionValue = [Value (real)]
VAR NationalValue =
    CALCULATE([Value (real)], 'Region'[is_national] = TRUE, REMOVEFILTERS('Region'))
RETURN
    DIVIDE(RegionValue, NationalValue)",
    @"6 Regional",
    @"0.0%");

upsert(
    @"Beta Coefficient",
    @"SELECTEDVALUE('Convergence'[beta])",
    @"7 Convergence",
    @"+0.000;-0.000");

upsert(
    @"Beta P Value",
    @"SELECTEDVALUE('Convergence'[p_value])",
    @"7 Convergence",
    @"0.000");

upsert(
    @"Beta R Squared",
    @"SELECTEDVALUE('Convergence'[r_squared])",
    @"7 Convergence",
    @"0.000");

upsert(
    @"Convergence Verdict",
    @"SELECTEDVALUE('Convergence'[verdict], ""Select one period"")",
    @"7 Convergence",
    @"");

upsert(
    @"Convergence Verdict Colour",
    @"SWITCH(
    SELECTEDVALUE('Convergence'[verdict]),
    ""convergence"", ""#2E7D5B"",
    ""divergence"",  ""#B33A3A"",
    ""#4A5761""
)",
    @"7 Convergence",
    @"");

upsert(
    @"Convergence Title",
    @"VAR Period = SELECTEDVALUE('Convergence'[period])
RETURN
    IF(
        ISBLANK(Period),
        ""Regional convergence: select a period"",
        Period & "" ("" & SELECTEDVALUE('Convergence'[start_year]) & ""-"" &
        SELECTEDVALUE('Convergence'[end_year]) & ""):  beta = "" &
        FORMAT(SELECTEDVALUE('Convergence'[beta]), ""+0.000"") & "",  p = "" &
        FORMAT(SELECTEDVALUE('Convergence'[p_value]), ""0.000"")
    )",
    @"8 Titles",
    @"");

upsert(
    @"Price Basis Title",
    @"""GDP and investment growth, "" &
LOWER(SELECTEDVALUE('Price Basis'[Basis], ""real"")) &
"" terms  (r = "" & FORMAT([Corr GDP vs Investment], ""+0.000"") & "")""",
    @"8 Titles",
    @"");

upsert(
    @"Initial Level (log)",
    @"AVERAGE('ConvergencePoints'[log_initial])",
    @"7 Convergence",
    @"0.00");

upsert(
    @"Annualised Growth %",
    @"AVERAGE('ConvergencePoints'[annual_growth_pct])",
    @"7 Convergence",
    @"0.0");

Info("Created or updated 33 measures.");