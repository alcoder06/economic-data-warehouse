# Uzbekistan Economic Data Warehouse

A production-ready data pipeline and analytical workspace for Uzbekistan's macroeconomic indicators. This repository is built to support reproducible data ingestion, transformation, quality validation, and exploratory analysis for both national and regional economic performance.

## Executive summary

This project captures Uzbekistan's economic transition between 2010 and 2024, with a focus on:
- national GDP dynamics and growth drivers
- fixed capital investment and external trade contributions
- employment trends and productivity evolution
- regional inequality, convergence, and structural divergence

The analysis highlights a strong capital- and productivity-driven expansion after 2016, resilient trade recovery after the COVID-19 shock, and widening regional divergence driven by productivity and industrial strength.

## What makes this project strong

- **Modular pipeline design**: bronze-silver-gold architecture for clean, traceable data transformations
- **Analytical depth**: national and regional analysis with complementing economic indicators
- **Story-driven outputs**: clear narrative from macroeconomic trends to regional structural shifts
- **Quality control**: validation scripts enforce completeness, uniqueness, and reference integrity
- **Reproducibility**: a fully documented setup and execution path for local replication

## Repository structure

- `config/` — source configuration and metadata definitions
- `data/bronze/` — raw downloaded files from official statistical sources
- `data/silver/` — cleaned, standardized intermediate datasets
- `data/gold/` — star-schema analytics-ready output
- `scripts/` — ETL, transformation, validation, and pipeline orchestration
- `notebooks/` — exploratory analysis and reporting
- `sql/` — data warehouse schema and example analytical queries
- `powerbi/` — placeholder for future dashboard artifacts

## Data architecture

The project uses a layered data warehouse approach:

1. **Bronze**: ingest raw source data into a stable raw layer
2. **Silver**: standardize region names, metric codes, and year coverage
3. **Gold**: build analytical tables in a star schema format, including `fact_economic` and dimension tables

This approach ensures that raw data is preserved while analytics are built on a clean, consistent foundation.

## How to run the project

### 1. Install environment

```bash
python -m pip install -r requirements.txt
```

### 2. Run the pipeline

```bash
python scripts/main_pipeline.py --steps all
```

### 3. Run individual pipeline stages

```bash
python scripts/main_pipeline.py --steps download
python scripts/main_pipeline.py --steps transform
python scripts/main_pipeline.py --steps gold
python scripts/main_pipeline.py --steps validate
```

### 4. Inspect results

- `data/gold/fact_economic.csv`
- `data/gold/dim_metric.csv`
- `data/gold/dim_region.csv`
- `notebooks/economical_analysis_clean.ipynb`

## Analysis notebook

The primary analysis notebook, `notebooks/economical_analysis_clean.ipynb`, is structured into:
- data preparation and cleaning
- national macro analysis (GDP, investment, trade, employment, productivity, sector structure)
- regional analysis (GDP shares, investment shares, trade shares, productivity, inequality, convergence)
- summary conclusions and policy-relevant insights

The notebook is designed for a data-savvy audience and provides interpretive commentary alongside visualizations.

## Validation and data quality

`scripts/validate_data.py` performs the following checks on gold-layer outputs:
- no duplicate `(region_code, year, metric_id)` records
- valid foreign-key relationships for regions and metrics
- no missing critical values in `year`, `metric_id`, or `region_code`
- completeness reporting for the selected year range and indicators

## Key findings

The project is built to support these headline findings:
- Uzbekistan's nominal GDP growth accelerated after 2016, driven by investment and trade expansion
- fixed capital investment has strong correlation with national GDP growth
- trade recovered strongly after the pandemic, reinforcing economic resilience
- employment recovery lagged but stabilized, suggesting growth is more productivity-driven than labor-intensive
- regional divergence increased over time, with stronger regions pulling ahead in productivity and industrial output

## Recommended next steps

- add a dedicated data dictionary for all metric codes and units
- document source provenance and download refresh procedures
- include real-term (inflation-adjusted) analysis if price indices are available
- add regression diagnostics and model validation for the forecasting sections
- create summary visuals and executive bullet points for non-technical stakeholders

## Notes

- All data originates from the official Uzbekistan Statistics Agency (stat.uz) open API
- No credentials or private data are stored in this repository
- The `powerbi/` folder is reserved for future dashboard development

## Reproducing the analysis (quick)

1. Create and activate a Python environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Launch the notebook from the repository root:

```powershell
jupyter lab notebooks/economical_analysis_clean.ipynb
```

The notebook uses `scripts/load_data.py` to centralize data loading and supports optional real-term adjustments when a deflator metric is present in the gold data. Regression diagnostic plots are saved to `outputs/diagnostics/` when those cells are run.
