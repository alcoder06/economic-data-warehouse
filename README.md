📊 Economic Data Pipeline & Star Schema Warehouse
📌 Project Overview

This project builds a complete data pipeline and star schema warehouse for regional economic data of Uzbekistan.

The goal is to transform multiple wide-format economic datasets (e.g., active enterprises, income per capita, etc.) into a clean, scalable, analysis-ready data warehouse that can be used in:

🐍 Python (Pandas / analysis / feature engineering)

🗄 SQL

📊 Power BI

📈 Future ML models

This project demonstrates:

Data modeling (Star Schema)

Data transformation (wide → long format)

ETL pipeline structure

Dimensional design

Scalable economic time-series architecture

🗂 Dataset Structure (Raw Data)

The raw data consists of separate Excel files for each economic metric, structured in wide format:

Classification	2010	2011	2012	...
Andijan	...	...	...	
Bukhara	...	...	...	

Each file represents one metric:

Active enterprises

Income per capita

(Future metrics can be added)

This format is not analysis-ready and must be transformed.

🏗 Project Architecture
economic-data-pipeline/
│
├── data/
│   ├── raw/          # Original Excel files (wide format)
│   ├── staging/      # Melted & cleaned intermediate files
│   └── warehouse/    # Final fact & dimension tables
│
├── scripts/
│   ├── extract.py
│   ├── transform.py
│   └── load.py
│
├── notebooks/
│   analysis.ipynb
│
├── powerbi/
│   dashboard.pbix
│
├── README.md
└── requirements.txt

🔄 ETL Pipeline
1️⃣ Extract

Load raw Excel files

Standardize column names

Validate data types

2️⃣ Transform
Step A: Convert Wide → Long Format

Each dataset is melted using Pandas:

df_long = df.melt(
    id_vars=["Classification"],
    var_name="year",
    value_name="value"
)


This converts:

Wide format:

Region | 2010 | 2011


Into:

Region | year | value

Step B: Add Metric Identifier

Each dataset is tagged with its metric name:

region | year | value | metric_name

Step C: Combine All Metrics

All melted datasets are concatenated into one unified table.

Step D: Create Dimension Tables

The following dimension tables are generated:

📌 dim_region

| region_id | region_name |

📌 dim_metric

| metric_id | metric_name | unit |

📌 dim_year (optional but scalable)

| year | decade | is_post_covid |

⭐ Final Star Schema
fact_economic

| region_id | year | metric_id | value |

This structure allows:

Unlimited metric expansion

Efficient Power BI relationships

Clean SQL aggregation

Scalable economic analysis

🎯 Why Star Schema?

Instead of keeping separate fact tables for each metric, this project uses:

(region, year, metric, value)


Advantages:

Scalable to new indicators

Clean joins

Consistent grain (region-year level)

Enterprise-style modeling

Single source of truth

📊 Power BI Integration

The star schema is imported into Power BI with relationships:

fact_economic → dim_region

fact_economic → dim_metric

fact_economic → dim_year

This enables:

Time intelligence

Cross-metric comparisons

Regional performance analysis

Clean DAX modeling

🐍 Python Analysis

In Python, the fact table can be merged with dimensions when needed:

df = fact.merge(dim_region, on="region_id")


This allows:

Feature engineering

Growth rate calculations

Rolling averages

ML modeling

📈 Future Improvements

Add automated data validation checks

Add logging system

Move warehouse to PostgreSQL

Automate ETL process

Add unit tests

Deploy pipeline

🧠 Key Concepts Demonstrated

Data normalization

Dimensional modeling

Wide-to-long transformation

Surrogate keys

Time-series data design

Scalable warehouse architecture

🚀 Project Purpose

This project was upgraded from a simple analytical task into a structured data engineering project to demonstrate:

Professional data modeling

ETL pipeline thinking

Clean architecture design

Reusable analytical structure
