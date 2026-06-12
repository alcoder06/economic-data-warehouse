-- Warehouse schema for Uzbekistan economic indicators

CREATE TABLE IF NOT EXISTS dim_region (
    region_code VARCHAR(16) PRIMARY KEY,
    region_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_metric (
    metric_id INTEGER PRIMARY KEY,
    metric_code TEXT NOT NULL UNIQUE,
    metric_name TEXT NOT NULL,
    unit TEXT
);

CREATE TABLE IF NOT EXISTS fact_economic (
    region_code VARCHAR(16) NOT NULL,
    year INTEGER NOT NULL,
    metric_id INTEGER NOT NULL,
    value NUMERIC,
    PRIMARY KEY (region_code, year, metric_id),
    FOREIGN KEY (region_code) REFERENCES dim_region(region_code),
    FOREIGN KEY (metric_id) REFERENCES dim_metric(metric_id)
);

CREATE INDEX IF NOT EXISTS idx_fact_economic_year ON fact_economic(year);
CREATE INDEX IF NOT EXISTS idx_fact_economic_metric ON fact_economic(metric_id);
