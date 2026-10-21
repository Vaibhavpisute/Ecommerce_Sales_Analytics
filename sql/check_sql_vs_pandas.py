"""Check the SQL results against pandas (run after sql/run_all_queries.py).

1. Q01 (data quality) vs the pandas summary of notebook 01 (reports/data_quality_summary.csv).
2. Spot checks: Q02, Q03, Q10, Q12, Q14 recalculated in pandas from data/processed/*.parquet.

Saves sql/outputs/check_q01_vs_pandas.csv and sql/outputs/check_spot_checks.csv.
Exit code 1 if anything does not match.

    .venv\\Scripts\\python sql\\check_sql_vs_pandas.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sql" / "outputs"
PROC = ROOT / "data" / "processed"


def q(name):
    return pd.read_csv(next(OUT.glob(f"{name}_*.csv")))


# ---------- 1. Q01 vs the notebook summary ----------
q01 = q("q01")
summary = pd.read_csv(ROOT / "reports" / "data_quality_summary.csv")
rows = []
for _, r in summary.iterrows():
    t = r["clean table"]
    sql_rows = int(q01[(q01.table_name == t) & (q01.check_name == "row_count")].value.iloc[0])
    sql_dup = int(q01[(q01.table_name == t) & (q01.check_name == "duplicate_keys")].value.iloc[0])
    sql_null = int(q01[(q01.table_name == t) & (q01.check_name == "null_count")].value.sum())
    for check, pandas_value, sql_value in [
        ("row_count", r["rows after"], sql_rows),
        ("duplicate_keys", r["duplicate keys after"], sql_dup),
        ("missing_cells", r["missing cells after"], sql_null),
    ]:
        rows.append({"table": t, "check": check, "pandas": int(pandas_value), "sql": sql_value,
                     "match": int(pandas_value) == sql_value})
check_q01 = pd.DataFrame(rows)
check_q01.to_csv(OUT / "check_q01_vs_pandas.csv", index=False)
print("Q01 vs pandas:", int(check_q01.match.sum()), "of", len(check_q01), "checks match")

# ---------- 2. Spot checks ----------
orders = pd.read_parquet(PROC / "fact_orders.parquet")
reviews = pd.read_parquet(PROC / "fact_reviews.parquet")
valid = orders[orders.is_valid_sale].copy()
valid["year_month"] = pd.to_datetime(valid.purchase_ts).dt.strftime("%Y-%m")
spot = []


def add(name, pandas_value, sql_value, tol=0.011):
    ok = bool(np.isclose(float(pandas_value), float(sql_value), atol=tol, rtol=0))
    spot.append({"check": name, "pandas": round(float(pandas_value), 4), "sql": round(float(sql_value), 4), "match": ok})


# Q02: monthly revenue and orders
m = valid.groupby("year_month").agg(orders=("order_id", "count"), revenue=("items_value", "sum"))
q02 = q("q02").set_index("year_month")
add("Q02 total revenue", m.revenue.sum(), q02.revenue.sum())
add("Q02 total orders", m.orders.sum(), q02.orders.sum(), tol=0)
add("Q02 max abs monthly revenue difference", (m.revenue - q02.revenue).abs().max(), 0)

# Q03: MoM growth (full months only)
full = m.loc["2017-01":"2018-08"].revenue
mom = (full.pct_change() * 100)
q03 = q("q03").set_index("year_month")
add("Q03 max abs MoM growth difference (pct points)", (mom - q03.mom_growth_pct).abs().max(), 0)

# Q04: moving average = mean of the last 3 full months
ma = full.rolling(3).mean()
q04 = q("q04").set_index("year_month")
add("Q04 max abs moving average difference", (ma - q04.moving_avg_3m).abs().max(), 0)

# Q10: repeat customers
n = valid.groupby("customer_unique_id").size()
q10 = q("q10").set_index("metric").value
add("Q10 customers", len(n), q10["customers"], tol=0)
add("Q10 repeat customers", (n >= 2).sum(), q10["repeat_customers"], tol=0)

# Q12: one row per customer with a valid order
q12 = q("q12")
add("Q12 rows (customers)", len(n), len(q12), tol=0)
add("Q12 total monetary", valid.items_value.sum(), q12.monetary.sum(), tol=1.0)

# Q14: late vs on time (delivered orders with a review)
d = orders[(orders.order_status == "delivered") & orders.delay_days.notna()].drop(columns="review_score").merge(
    reviews[["order_id", "review_score"]], on="order_id")
q14 = q("q14")
q14 = q14[q14.level == "late_vs_on_time"].set_index("group_name")
add("Q14 late orders", (d.delay_days > 0).sum(), q14.loc["Late", "orders"], tol=0)
add("Q14 avg score, late", d.loc[d.delay_days > 0, "review_score"].mean(), q14.loc["Late", "avg_review_score"], tol=0.0001)
add("Q14 avg score, on time or early", d.loc[d.delay_days <= 0, "review_score"].mean(),
    q14.loc["On time or early", "avg_review_score"], tol=0.0001)

check_spot = pd.DataFrame(spot)
check_spot.to_csv(OUT / "check_spot_checks.csv", index=False)
print(check_spot.to_string(index=False))

if not (check_q01.match.all() and check_spot.match.all()):
    print("MISMATCH FOUND")
    sys.exit(1)
print("All checks match.")
