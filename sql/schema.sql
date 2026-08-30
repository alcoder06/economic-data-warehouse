-- Warehouse schema for the Uzbekistan economic indicators star.
--
-- One fact table, three dimensions. Two things in here are worth reading rather
-- than skimming, because both are places the data will mislead a query that
-- assumes the obvious.
--
-- 1. dim_region.is_national. region_code 1700 is the Republic total and it sits in
--    the same column as the fourteen regions that compose it. SUM(value) over the
--    region dimension double-counts the entire country. Every regional query below
--    filters on is_national = FALSE.
--
-- 2. fact_economic.value vs real_value. Nine series are published at current prices.
--    Between 2010 and 2024 the price level rose 7.2x while nominal GDP rose 17.4x,
--    so a query that compares `value` across years is mostly measuring inflation.
--    real_value holds constant 2010 soums and is NULL wherever deflation does not
--    apply, which is deliberate: a NULL is a question, a silently nominal number is
--    a wrong answer.

DROP TABLE IF EXISTS fact_economic;
DROP TABLE IF EXISTS dim_region;
DROP TABLE IF EXISTS dim_metric;
DROP TABLE IF EXISTS dim_year;

CREATE TABLE dim_region (
    region_code   INTEGER PRIMARY KEY,
    region_name   TEXT    NOT NULL,
    region_short  TEXT    NOT NULL,
    region_type   TEXT    NOT NULL,
    -- TRUE for the Republic total only. Filter it out of anything that aggregates
    -- across regions; keep it for national time series.
    is_national   BOOLEAN NOT NULL
);

CREATE TABLE dim_metric (
    metric_id            INTEGER PRIMARY KEY,
    metric_code          TEXT    NOT NULL UNIQUE,
    metric_name          TEXT    NOT NULL,
    metric_short         TEXT,
    -- The publisher's own identifier: a stat.uz code like 1.01.03.0001, or a World
    -- Bank series code like NY.GDP.DEFL.ZS. Keeps every row traceable to source.
    official_code        TEXT,
    unit                 TEXT,
    unit_raw             TEXT,
    -- 'current', 'constant' or 'not applicable', parsed from the publisher's own
    -- unit string ("at current prices, billion soums").
    price_basis          TEXT,
    is_deflatable        BOOLEAN NOT NULL DEFAULT FALSE,
    per_capita_meaningful BOOLEAN NOT NULL DEFAULT FALSE,
    source               TEXT    NOT NULL,
    source_id            TEXT,
    -- 'regional' (stat.uz, 14 regions + total, from 2010) or
    -- 'national'  (World Bank, Republic only, from 1987).
    grain                TEXT    NOT NULL,
    metric_group         TEXT,
    periodicity          TEXT,
    methodology_url      TEXT,
    notes                TEXT
);

CREATE TABLE dim_year (
    year                  INTEGER PRIMARY KEY,
    -- GDP deflator rebased so 2010 = 100, and the same figure as a ratio. Stored
    -- here rather than computed at query time: it is an attribute of the year.
    gdp_deflator          NUMERIC,
    cpi                   NUMERIC,
    deflator_ratio        NUMERIC,
    exchange_rate_uzs_usd NUMERIC,
    real_gdp_growth_pct   NUMERIC,
    -- The som was floated in September 2017. Any comparison spanning that year
    -- compares two currency regimes, so the boundary is labelled rather than left
    -- for the reader to spot.
    currency_era          TEXT,
    is_float_year         BOOLEAN,
    policy_era            TEXT,
    decade                TEXT,
    has_regional_data     BOOLEAN
);

CREATE TABLE fact_economic (
    region_code           INTEGER NOT NULL REFERENCES dim_region(region_code),
    year                  INTEGER NOT NULL REFERENCES dim_year(year),
    metric_id             INTEGER NOT NULL REFERENCES dim_metric(metric_id),
    -- As published. For the nine current-price series this is a nominal soum figure
    -- and is not comparable across years.
    value                 NUMERIC NOT NULL,
    -- Constant 2010 soums. NULL where deflation does not apply.
    real_value            NUMERIC,
    value_per_capita      NUMERIC,
    real_value_per_capita NUMERIC,
    PRIMARY KEY (region_code, year, metric_id)
);

CREATE INDEX idx_fact_year   ON fact_economic(year);
CREATE INDEX idx_fact_metric ON fact_economic(metric_id);
CREATE INDEX idx_fact_region ON fact_economic(region_code);

-- Guard rail. The reconciliation that matters is that the deflated national GDP
-- series reproduces the World Bank's independently published real growth rate. If
-- a future refresh breaks the deflator join, this view stops returning near-zero
-- gaps and the failure is visible instead of silent.
CREATE OR REPLACE VIEW v_deflation_check AS
WITH national_gdp AS (
    SELECT f.year,
           f.real_value,
           LAG(f.real_value) OVER (ORDER BY f.year) AS prev_real
    FROM fact_economic f
    JOIN dim_metric m ON f.metric_id = m.metric_id
    JOIN dim_region r ON f.region_code = r.region_code
    WHERE m.metric_code = 'regional_gdp'
      AND r.is_national
)
SELECT g.year,
       ROUND(100.0 * (g.real_value - g.prev_real) / NULLIF(g.prev_real, 0), 2) AS our_real_growth_pct,
       ROUND(y.real_gdp_growth_pct::numeric, 2)                                AS worldbank_real_growth_pct,
       ROUND(ABS(100.0 * (g.real_value - g.prev_real) / NULLIF(g.prev_real, 0)
                 - y.real_gdp_growth_pct)::numeric, 3)                         AS gap_pp
FROM national_gdp g
JOIN dim_year y ON g.year = y.year
WHERE g.prev_real IS NOT NULL
ORDER BY g.year;
