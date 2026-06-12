-- 1) GDP growth timeline
WITH national_region AS (
    SELECT region_code
    FROM dim_region
    WHERE region_name = 'Republic of Uzbekistan'
    LIMIT 1
),
national_gdp AS (
    SELECT f.year,
           f.value AS gdp
    FROM fact_economic f
    JOIN dim_metric m ON f.metric_id = m.metric_id
    WHERE m.metric_code = 'regional_gdp'
      AND f.region_code = (SELECT region_code FROM national_region)
)
SELECT
    year,
    gdp,
    ROUND(100.0 * (gdp - LAG(gdp) OVER (ORDER BY year)) / NULLIF(LAG(gdp) OVER (ORDER BY year), 0), 2) AS gdp_growth_pct,
    ROUND(AVG(gdp) OVER (ORDER BY year ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS gdp_3yr_avg
FROM national_gdp
ORDER BY year;

-- 2) top GDP regions now
WITH latest_year AS (
    SELECT MAX(year) AS year FROM fact_economic
),
gdp_by_region AS (
    SELECT r.region_name,
           f.year,
           f.value AS gdp
    FROM fact_economic f
    JOIN dim_region r ON f.region_code = r.region_code
    JOIN dim_metric m ON f.metric_id = m.metric_id
    WHERE m.metric_code = 'regional_gdp'
      AND f.year = (SELECT year FROM latest_year)
)
SELECT region_name, year, gdp
FROM gdp_by_region
ORDER BY gdp DESC
LIMIT 10;

-- 3) GDP vs investment
WITH national AS (
    SELECT f.year, m.metric_code, f.value
    FROM fact_economic f
    JOIN dim_metric m ON f.metric_id = m.metric_id
    JOIN dim_region r ON f.region_code = r.region_code
    WHERE r.region_name = 'Republic of Uzbekistan'
      AND m.metric_code IN ('regional_gdp', 'fixed_capital_investment')
),
pivoted AS (
    SELECT year,
           MAX(CASE WHEN metric_code = 'regional_gdp' THEN value END) AS gdp,
           MAX(CASE WHEN metric_code = 'fixed_capital_investment' THEN value END) AS investment
    FROM national
    GROUP BY year
),
growth AS (
    SELECT year,
           gdp,
           investment,
           100.0 * (gdp - LAG(gdp) OVER (ORDER BY year)) / NULLIF(LAG(gdp) OVER (ORDER BY year), 0) AS gdp_growth_pct,
           100.0 * (investment - LAG(investment) OVER (ORDER BY year)) / NULLIF(LAG(investment) OVER (ORDER BY year), 0) AS investment_growth_pct
    FROM pivoted
)
SELECT year, gdp_growth_pct, investment_growth_pct
FROM growth
WHERE gdp_growth_pct IS NOT NULL
  AND investment_growth_pct IS NOT NULL
ORDER BY year;

-- 4) metric coverage by year
WITH national AS (
    SELECT f.year, m.metric_code
    FROM fact_economic f
    JOIN dim_metric m ON f.metric_id = m.metric_id
    JOIN dim_region r ON f.region_code = r.region_code
    WHERE r.region_name = 'Republic of Uzbekistan'
)
SELECT year,
       COUNT(DISTINCT metric_code) AS metrics_available
FROM national
GROUP BY year
ORDER BY year;

-- 5) trade + employment trend
WITH national AS (
    SELECT f.year, m.metric_code, f.value
    FROM fact_economic f
    JOIN dim_metric m ON f.metric_id = m.metric_id
    JOIN dim_region r ON f.region_code = r.region_code
    WHERE r.region_name = 'Republic of Uzbekistan'
      AND m.metric_code IN ('external_trade_turnover', 'employment_rate')
),
pivoted AS (
    SELECT year,
           MAX(CASE WHEN metric_code = 'external_trade_turnover' THEN value END) AS external_trade_turnover,
           MAX(CASE WHEN metric_code = 'employment_rate' THEN value END) AS employment_rate
    FROM national
    GROUP BY year
)
SELECT year, external_trade_turnover, employment_rate
FROM pivoted
ORDER BY year;

-- 6) top region GDP growth since 2010
WITH gdp AS (
    SELECT r.region_name,
           f.year,
           f.value AS gdp,
           ROW_NUMBER() OVER (PARTITION BY r.region_name ORDER BY f.year ASC) AS row_start,
           ROW_NUMBER() OVER (PARTITION BY r.region_name ORDER BY f.year DESC) AS row_end
    FROM fact_economic f
    JOIN dim_region r ON f.region_code = r.region_code
    JOIN dim_metric m ON f.metric_id = m.metric_id
    WHERE m.metric_code = 'regional_gdp'
),
region_growth AS (
    SELECT
        region_name,
        MAX(CASE WHEN row_start = 1 THEN year END) AS start_year,
        MAX(CASE WHEN row_start = 1 THEN gdp END) AS gdp_start,
        MAX(CASE WHEN row_end = 1 THEN year END) AS end_year,
        MAX(CASE WHEN row_end = 1 THEN gdp END) AS gdp_end
    FROM gdp
    GROUP BY region_name
)
SELECT
    region_name,
    start_year,
    end_year,
    gdp_start,
    gdp_end,
    ROUND(100.0 * (gdp_end - gdp_start) / NULLIF(gdp_start, 0), 2) AS pct_growth
FROM region_growth
ORDER BY pct_growth DESC
LIMIT 10;

-- 7) regional GDP rank with yoy change
WITH latest_year AS (
    SELECT MAX(year) AS year FROM fact_economic
),
gdp_latest AS (
    SELECT r.region_name,
           f.year,
           f.value AS gdp,
           LAG(f.value) OVER (PARTITION BY r.region_name ORDER BY f.year) AS prev_gdp
    FROM fact_economic f
    JOIN dim_region r ON f.region_code = r.region_code
    JOIN dim_metric m ON f.metric_id = m.metric_id
    WHERE m.metric_code = 'regional_gdp'
)
SELECT
    region_name,
    year,
    gdp,
    ROUND(100.0 * (gdp - prev_gdp) / NULLIF(prev_gdp, 0), 2) AS yoy_change_pct
FROM gdp_latest
WHERE year = (SELECT year FROM latest_year)
ORDER BY gdp DESC
LIMIT 10;
