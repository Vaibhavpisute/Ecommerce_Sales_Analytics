"""Step 2: PySpark job for the Olist data (same style as the sales pipeline).

PostgreSQL (olist_db, JDBC) -> cast types, remove duplicates, join
-> Parquet files in MinIO (s3a://<bucket>/olist/curated/<table>/)
-> Hive tables in the database `olist`.

It runs inside the pipeline's Airflow container with run_spark.sh (see pipeline_ingest/README.md).
Connection settings come from the container environment variables (the pipeline .env).
"""
import os

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

spark = SparkSession.builder.appName("Olist_to_curated").enableHiveSupport().getOrCreate()
spark.sparkContext.setLogLevel("WARN")

OLIST_DB = os.environ.get("OLIST_DB", "olist_db")
JDBC_URL = f"jdbc:postgresql://{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{OLIST_DB}"
BUCKET = os.environ["MINIO_BUCKET"]
CURATED = f"s3a://{BUCKET}/olist/curated"
HIVE_DB = "olist"


def read_table(name):
    """Read one source table from PostgreSQL over JDBC (all columns are TEXT)."""
    return (
        spark.read.format("jdbc")
        .option("url", JDBC_URL)
        .option("user", os.environ["POSTGRES_USER"])
        .option("password", os.environ["POSTGRES_PASSWORD"])
        .option("driver", "org.postgresql.Driver")
        .option("dbtable", name)
        .load()
    )


def ts(col):
    return F.to_timestamp(F.col(col))


# ---------- 1. read ----------
customers = read_table("customers")
orders = read_table("orders")
items = read_table("order_items")
payments = read_table("order_payments")
reviews = read_table("order_reviews")
products = read_table("products")
sellers = read_table("sellers")
translation = read_table("product_category_name_translation")

# ---------- 2. cast types and remove duplicates ----------
customers = customers.dropDuplicates(["customer_id"]).select(
    "customer_id",
    "customer_unique_id",
    F.col("customer_zip_code_prefix").alias("zip_code_prefix"),
    F.initcap("customer_city").alias("city"),
    F.upper("customer_state").alias("state"),
)

orders = orders.dropDuplicates(["order_id"]).select(
    "order_id",
    "customer_id",
    "order_status",
    ts("order_purchase_timestamp").alias("purchase_ts"),
    ts("order_approved_at").alias("approved_ts"),
    ts("order_delivered_carrier_date").alias("carrier_ts"),
    ts("order_delivered_customer_date").alias("delivered_ts"),
    ts("order_estimated_delivery_date").alias("estimated_delivery_ts"),
)

items = items.dropDuplicates(["order_id", "order_item_id"]).select(
    "order_id",
    F.col("order_item_id").cast("int").alias("order_item_id"),
    "product_id",
    "seller_id",
    ts("shipping_limit_date").alias("shipping_limit_ts"),
    F.col("price").cast("double").alias("price"),
    F.col("freight_value").cast("double").alias("freight_value"),
)

payments = payments.dropDuplicates().select(
    "order_id",
    F.col("payment_sequential").cast("int").alias("payment_sequential"),
    "payment_type",
    F.col("payment_installments").cast("int").alias("payment_installments"),
    F.col("payment_value").cast("double").alias("payment_value"),
)

# A review_id can appear for more than one order and an order can have more than one review.
# Keep one row per (review_id, order_id): the one answered last.
rev_window = Window.partitionBy("review_id", "order_id").orderBy(F.col("answer_ts").desc_nulls_last())
reviews = (
    reviews.select(
        "review_id",
        "order_id",
        F.col("review_score").cast("int").alias("review_score"),
        ts("review_creation_date").alias("creation_ts"),
        ts("review_answer_timestamp").alias("answer_ts"),
    )
    .withColumn("rn", F.row_number().over(rev_window))
    .filter("rn = 1")
    .drop("rn")
)

products = (
    products.dropDuplicates(["product_id"])
    .join(translation, "product_category_name", "left")
    .select(
        "product_id",
        F.col("product_category_name").alias("category_pt"),
        F.coalesce("product_category_name_english", F.col("product_category_name"), F.lit("unknown")).alias("category_en"),
        F.col("product_weight_g").cast("double").alias("weight_g"),
        F.col("product_photos_qty").cast("int").alias("photos_qty"),
    )
)

sellers = sellers.dropDuplicates(["seller_id"]).select(
    "seller_id", F.initcap("seller_city").alias("city"), F.upper("seller_state").alias("state")
)

# ---------- 3. joins ----------
# Order-item level table: one row per item sold
order_items_curated = (
    items.join(orders, "order_id", "inner")
    .join(customers.select("customer_id", "customer_unique_id", F.col("state").alias("customer_state")), "customer_id", "left")
    .join(products.select("product_id", "category_en"), "product_id", "left")
    .select(
        "order_id", "order_item_id", "product_id", "seller_id", "customer_id", "customer_unique_id",
        "customer_state", "category_en", "order_status", "purchase_ts", "price", "freight_value",
    )
)

# Order level table: one row per order
item_agg = items.groupBy("order_id").agg(
    F.count("*").alias("item_count"),
    F.round(F.sum("price"), 2).alias("items_value"),
    F.round(F.sum("freight_value"), 2).alias("freight_value"),
)

pay_agg = payments.groupBy("order_id").agg(
    F.round(F.sum("payment_value"), 2).alias("payment_value"),
    F.max("payment_installments").alias("max_installments"),
)
main_pay_window = Window.partitionBy("order_id").orderBy(F.col("payment_value").desc(), "payment_sequential")
main_pay = (
    payments.withColumn("rn", F.row_number().over(main_pay_window)).filter("rn = 1")
    .select("order_id", F.col("payment_type").alias("main_payment_type"))
)

# One score per order: the average of its reviews
rev_agg = reviews.groupBy("order_id").agg(F.round(F.avg("review_score"), 2).alias("review_score"))

orders_curated = (
    orders.join(customers.select("customer_id", "customer_unique_id", "city", "state"), "customer_id", "left")
    .join(item_agg, "order_id", "left")
    .join(pay_agg, "order_id", "left")
    .join(main_pay, "order_id", "left")
    .join(rev_agg, "order_id", "left")
    .withColumn("delivery_days", F.round((F.unix_timestamp("delivered_ts") - F.unix_timestamp("purchase_ts")) / 86400, 2))
    .withColumn("delay_days", F.round((F.unix_timestamp("delivered_ts") - F.unix_timestamp("estimated_delivery_ts")) / 86400, 2))
)

outputs = {
    "orders": orders_curated,
    "order_items": order_items_curated,
    "payments": payments,
    "reviews": reviews,
    "customers": customers,
    "products": products,
    "sellers": sellers,
}

# ---------- 4. write Parquet to MinIO and create Hive tables ----------
spark.sql(f"CREATE DATABASE IF NOT EXISTS {HIVE_DB}")
for name, df in outputs.items():
    path = f"{CURATED}/{name}"
    df.write.mode("overwrite").parquet(path)
    spark.sql(f"DROP TABLE IF EXISTS {HIVE_DB}.{name}")
    spark.sql(f"CREATE TABLE {HIVE_DB}.{name} USING parquet LOCATION '{path}'")
    print(f"Wrote {name}: {spark.table(f'{HIVE_DB}.{name}').count()} rows -> {path}")

print("olist spark job finished successfully")
