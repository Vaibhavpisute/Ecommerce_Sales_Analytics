"""Step 3: download the curated Parquet files from MinIO to data/raw/pipeline_output/<table>/.

Run from the project root:  .venv\\Scripts\\python pipeline_ingest\\03_export_from_minio.py
"""
import os
import sys
from pathlib import Path

import boto3
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import db  # noqa: E402,F401  (loads .env)

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "pipeline_output"
PREFIX = "olist/curated/"


def main():
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT_URL"],
        aws_access_key_id=os.environ["MINIO_USER"],
        aws_secret_access_key=os.environ["MINIO_PASSWORD"],
        region_name="us-east-1",
    )
    bucket = os.environ["MINIO_BUCKET"]
    keys = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=PREFIX):
        keys += [o["Key"] for o in page.get("Contents", []) if o["Key"].endswith(".parquet")]
    if not keys:
        raise SystemExit(f"No Parquet files found under s3://{bucket}/{PREFIX}. Run the Spark job first.")
    for key in keys:
        target = OUT_DIR / key[len(PREFIX):]
        target.parent.mkdir(parents=True, exist_ok=True)
        s3.download_file(bucket, key, str(target))
    for table_dir in sorted(p for p in OUT_DIR.iterdir() if p.is_dir()):
        n = sum(pq.ParquetFile(f).metadata.num_rows for f in table_dir.glob("*.parquet"))
        print(f"{table_dir.name:15s} {n:>9,} rows  ({len(list(table_dir.glob('*.parquet')))} files)")


if __name__ == "__main__":
    main()
