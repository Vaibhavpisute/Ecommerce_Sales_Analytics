# pipeline_ingest: Olist data through the pipeline

Flow (same stack as my pipeline repo
[Enterprise_Data_Analysis](https://github.com/Vaibhavpisute/Enterprise_Data_Analysis)):

```
Olist CSV files -> PostgreSQL (olist_db) -> PySpark (JDBC) -> Parquet in MinIO + Hive tables (database "olist") -> export to data/raw/pipeline_output/
```

No file in the pipeline repo is changed. We only use its running Docker containers.

## Steps to repeat everything

Run from the project root. Use the Python virtual environment (`.venv`).

1. Start the pipeline containers:
   ```
   cd D:\projects\git\Enterprise_Data_Analysis\local_demo
   docker compose up -d
   ```
2. Download the data (needs `C:\Users\<you>\.kaggle\kaggle.json`):
   ```
   .venv\Scripts\kaggle datasets download -d olistbr/brazilian-ecommerce -p data\raw\olist
   ```
   Unzip it into `data\raw\olist\`.
3. Load the 9 CSV files into PostgreSQL (`olist_db`, all columns as TEXT):
   ```
   .venv\Scripts\python pipeline_ingest\01_load_olist_to_postgres.py
   ```
4. Run the Spark job inside the Airflow container (Git Bash needs `MSYS_NO_PATHCONV=1`):
   ```
   docker cp pipeline_ingest/02_olist_spark_job.py sales-demo-airflow-1:/tmp/02_olist_spark_job.py
   docker exec sales-demo-airflow-1 bash /opt/airflow/scripts/run_spark.sh /tmp/02_olist_spark_job.py
   ```
   The job casts types, removes duplicates and joins the tables. It writes Parquet to
   `s3a://<bucket>/olist/curated/<table>/` and creates Hive tables in database `olist`.
5. Export the Parquet files from MinIO:
   ```
   .venv\Scripts\python pipeline_ingest\03_export_from_minio.py
   ```
6. Stop the containers: `docker compose stop` (in the `local_demo` folder).

## What the Spark job creates

| Table | Level | Notes |
|---|---|---|
| orders | one row per order | status, timestamps, item count, items value, freight, payment value, main payment type, review score, delivery days, delay days, customer city/state |
| order_items | one row per item sold | category (English), price, freight, seller, customer ids |
| payments | one row per payment | type, installments, value |
| reviews | one row per review | score, dates |
| customers, products, sellers | dimensions | cleaned names, English category |

The geolocation file (1M rows) is loaded into `olist_db` but not used later.
