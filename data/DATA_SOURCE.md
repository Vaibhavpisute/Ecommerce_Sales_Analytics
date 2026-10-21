# Data source

## Dataset
**Brazilian E-Commerce Public Dataset by Olist** (Kaggle: `olistbr/brazilian-ecommerce`).
About 100k real, anonymised orders from a Brazilian marketplace, 2016 to 2018.
Credit: Olist, who released the dataset. Licence: CC BY-NC-SA 4.0 (non-commercial use, share alike, give credit). See the file NOTICE in the repository root.
Link: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

## How the data got here
1. Downloaded with the official Kaggle API on 2026-10-21 (raw files in `data/raw/olist/`, not committed).
2. Loaded into PostgreSQL `olist_db` (all columns as text) with `pipeline_ingest/01_load_olist_to_postgres.py`.
3. PySpark job `pipeline_ingest/02_olist_spark_job.py` (run in the Airflow container of my pipeline) read the tables
   over JDBC, cast types, removed duplicates, joined them, wrote Parquet to MinIO and created Hive tables in database `olist`.
4. Exported from MinIO to `data/raw/pipeline_output/` with `pipeline_ingest/03_export_from_minio.py` (not committed).

Pipeline repo: https://github.com/Vaibhavpisute/Enterprise_Data_Analysis

## Export date and row counts (export on 2026-10-21)

Source tables in `olist_db`:

| Table | Rows |
|---|---|
| customers | 99,441 |
| geolocation (not used later) | 1,000,163 |
| orders | 99,441 |
| order_items | 112,650 |
| order_payments | 103,886 |
| order_reviews | 99,224 |
| products | 32,951 |
| sellers | 3,095 |
| product_category_name_translation | 71 |

Curated Parquet tables (`data/raw/pipeline_output/`):

| Table | Rows |
|---|---|
| orders | 99,441 |
| order_items | 112,650 |
| payments | 103,886 |
| reviews | 99,224 |
| customers | 99,441 |
| products | 32,951 |
| sellers | 3,095 |

The Spark job removed no duplicate rows at this stage: curated counts equal source counts.
Deeper cleaning (missing values, invalid dates, outliers) happens in `notebooks/01_data_cleaning.ipynb`.
