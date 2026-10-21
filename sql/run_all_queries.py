"""Run all SQL queries (sql/q*.sql) on analytics_db and save each result to sql/outputs/<query name>.csv.

Run from the project root (the Docker container with PostgreSQL must be running):
    .venv\\Scripts\\python sql\\run_all_queries.py
"""
import sys
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.db import get_engine  # noqa: E402

SQL_DIR = ROOT / "sql"
OUT_DIR = SQL_DIR / "outputs"


def main():
    OUT_DIR.mkdir(exist_ok=True)
    engine = get_engine()
    files = sorted(SQL_DIR.glob("q[0-9][0-9]_*.sql"))
    if len(files) != 15:
        raise SystemExit(f"Expected 15 query files, found {len(files)}")
    for path in files:
        start = time.time()
        sql = path.read_text(encoding="utf-8")
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            df = pd.DataFrame(result.fetchall(), columns=list(result.keys()))
        out = OUT_DIR / f"{path.stem}.csv"
        df.to_csv(out, index=False)
        print(f"{path.stem:50s} {len(df):>8,} rows  {time.time() - start:5.1f}s  -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
