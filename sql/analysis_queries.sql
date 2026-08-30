-- Analytical queries against the Uzbekistan economic star schema.
--
-- Two rules run through all of them and both exist because breaking either returns a
-- plausible wrong number rather than an error:
--
--   1. Regional aggregates filter `dim_region.is_national = FALSE`. region_code 1700
--      is the Republic total sitting in the same column as the fourteen regions that
--      compose it, so omitting the filter counts the country twice.
--   2. Anything comparing soum values across years uses `real_value`, not `value`.
--      The price level rose 7.2x between 2010 and 2024.

-- 1) The headline decomposition: how much of nominal growth was output?
WITH national_gdp AS (
    SELECT f.year, f.value AS nominal, f.real_value AS real
    FROM fact_economic f
    JOIN dim_metric m ON f.metric_id = m.metric_id
    JOIN dim_region r ON f.region_code = r.region_code
    WHERE m.metric_code = 'regional_gdp' AND r.is_national
),
endpoints AS (
    SELECT
        MAX(CASE WHEN year = 2010 THEN nominal END) AS nom_2010,
        MAX(CASE WHEN year = 2024 THEN nominal END) AS nom_2024,
        MAX(CASE WHEN year = 2010 THEN real    END) AS real_2010,
        MAX(CASE WHEN year = 2024 THEN real    END) AS real_2024
    FROM national_gdp
)
SELECT
    ROUND((nom_2024  / nom_2010  - 1) * 100, 0) AS nominal_growth_pct,
    ROUND((real_2024 / real_2010 - 1) * 100, 0) AS real_growth_pct,
    ROUND((1 - (real_2024 / real_2010 - 1)
             / (nom_2024  / nom_2010  - 1)) * 100, 1) AS pct_of_growth_that_is_price
FROM endpoints;

-- 2) Nominal against real growth, year by year. The reform years diverge.
WITH national_gdp AS (
    SELECT f.year, f.value AS nominal, f.real_value AS real
    FROM fact_economic f
    JOIN dim_metric m ON f.metric_id = m.metric_id
    JOIN dim_region r ON f.region_code = r.region_code
    WHERE m.metric_code = 'regional_gdp' AND r.is_national
)
SELECT
    g.year,
    y.policy_era,
    ROUND(100.0 * (g.nominal - LAG(g.nominal) OVER (ORDER BY g.year))
          / NULLIF(LAG(g.nominal) OVER (ORDER BY g.year), 0), 1) AS nominal_growth_pct,
    ROUND(100.0 * (g.real - LAG(g.real) OVER (ORDER BY g.year))
          / NULLIF(LAG(g.real) OVER (ORDER BY g.year), 0), 1)    AS real_growth_pct,
    ROUND(y.exchange_rate_uzs_usd, 0)                             AS uzs_per_usd
FROM national_gdp g
JOIN dim_year y ON g.year = y.year
ORDER BY g.year;

-- 3) Regional real GDP per capita, latest year, with rank and gap to the leader.
WITH latest AS (
    SELECT MAX(f.year) AS year
    FROM fact_economic f
    JOIN dim_metric m ON f.metric_id = m.metric_id
    WHERE m.metric_code = 'regional_gdp' AND f.real_value_per_capita IS NOT NULL
),
regional AS (
    SELECT r.region_short, f.year, f.real_value_per_capita AS gdp_pc
    FROM fact_economic f
    JOIN dim_metric m ON f.metric_id = m.metric_id
    JOIN dim_region r ON f.region_code = r.region_code
    WHERE m.metric_code = 'regional_gdp'
      AND NOT r.is_national
      AND f.year = (SELECT year FROM latest)
)
SELECT
    RANK() OVER (ORDER BY gdp_pc DESC) AS rank,
    region_short,
    ROUND(gdp_pc::numeric, 2) AS real_gdp_per_capita,
    ROUND((gdp_pc / MAX(gdp_pc) OVER () * 100)::numeric, 1) AS pct_of_leader
FROM regional
ORDER BY gdp_pc DESC;

-- 4) Beta-convergence inputs: starting level against annualised growth, per region.
--    Feed the two columns to a regression; a negative slope is convergence.
WITH bounds AS (SELECT 2017 AS start_year, 2024 AS end_year),
regional AS (
    SELECT r.region_short, f.year, f.real_value_per_capita AS gdp_pc
    FROM fact_economic f
    JOIN dim_metric m ON f.metric_id = m.metric_id
    JOIN dim_region r ON f.region_code = r.region_code
    WHERE m.metric_code = 'regional_gdp' AND NOT r.is_national
),
paired AS (
    SELECT
        g.region_short,
        MAX(CASE WHEN g.year = b.start_year THEN g.gdp_pc END) AS gdp_start,
        MAX(CASE WHEN g.year = b.end_year   THEN g.gdp_pc END) AS gdp_end,
        b.start_year, b.end_year
    FROM regional g CROSS JOIN bounds b
    GROUP BY g.region_short, b.start_year, b.end_year
)
SELECT
    region_short,
    ROUND(LN(gdp_start)::numeric, 4) AS log_initial_level,
    ROUND((LN(gdp_end / gdp_start) / (end_year - start_year) * 100)::numeric, 3)
        AS annualised_growth_pct
FROM paired
WHERE gdp_start IS NOT NULL AND gdp_end IS NOT NULL
ORDER BY log_initial_level;

-- 5) Regional inequality, measured two ways, from the precomputed year attributes.
SELECT year,
       ROUND(gini_nominal_levels::numeric, 3)   AS gini_on_nominal_levels,
       ROUND(gini_real_gdp_pc::numeric, 3)      AS gini_on_real_per_capita,
       ROUND(sigma_log_dispersion::numeric, 3)  AS log_dispersion,
       policy_era
FROM dim_year
WHERE gini_real_gdp_pc IS NOT NULL
ORDER BY year;

-- 6) The data dictionary: which series are nominal, and therefore need real_value.
SELECT metric_code, official_code, unit_raw, price_basis, is_deflatable, source, grain
FROM dim_metric
ORDER BY is_deflatable DESC, source, metric_code;

-- 7) Coverage audit: where each series starts and stops, and how complete it is.
SELECT m.metric_code,
       m.source,
       m.grain,
       MIN(f.year)                        AS first_year,
       MAX(f.year)                        AS last_year,
       COUNT(*)                           AS observations,
       COUNT(DISTINCT f.region_code)      AS regions,
       COUNT(f.real_value)                AS rows_with_real_value
FROM fact_economic f
JOIN dim_metric m ON f.metric_id = m.metric_id
GROUP BY m.metric_code, m.source, m.grain
ORDER BY m.source, MAX(f.year), m.metric_code;
