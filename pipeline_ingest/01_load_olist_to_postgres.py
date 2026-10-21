"""Step 1: load the 9 Olist CSV files into PostgreSQL database `olist_db`.

This plays the role of the source database (like RDS in the original pipeline).
All columns are loaded as TEXT, exactly as in the files. Type casting is done later by Spark.

Run from the project root:  .venv\\Scripts\\python pipeline_ingest\\01_load_olist_to_postgres.py
"""
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.db import ensure_database, get_engine  # noqa: E402

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "olist"

# CSV file name -> table name in olist_db
TABLES = {
    "olist_customers_dataset.csv": "customers",
    "olist_geolocation_dataset.csv": "geolocation",
    "olist_orders_dataset.csv": "orders",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "product_category_name_translation",
}


def main():
    db = os.environ.get("OLIST_DB", "olist_db")
    ensure_database(db)
    engine = get_engine(db)
    raw = engine.raw_connection()
    try:
        cur = raw.cursor()
        for file_name, table in TABLES.items():
            path = RAW_DIR / file_name
            with open(path, newline="", encoding="utf-8-sig") as f:
                header = next(csv.reader(f))
            cols = ", ".join(f'"{c}" TEXT' for c in header)
            cur.execute(f'DROP TABLE IF EXISTS "{table}"')
            cur.execute(f'CREATE TABLE "{table}" ({cols})')
            with open(path, encoding="utf-8-sig") as f:
                cur.copy_expert(f'COPY "{table}" FROM STDIN WITH (FORMAT csv, HEADER true)', f)
            cur.execute(f'SELECT count(*) FROM "{table}"')
            print(f"{table:40s} {cur.fetchone()[0]:>10,} rows")
        raw.commit()
    finally:
        raw.close()


if __name__ == "__main__":
    main()
