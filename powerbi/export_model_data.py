"""Export model-ready CSV files for the Power BI project to powerbi/data/.

Sources (nothing is invented here):
  data/processed/*.parquet   cleaned star schema from notebook 01
  sql/outputs/q08, q11, q12, q13   results of the SQL queries
Only valid sales are exported (not canceled or unavailable). Text ids are replaced by integer keys to keep the files small.

Run from the project root:  .venv\\Scripts\\python powerbi\\export_model_data.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.helpers import STATE_TO_REGION  # noqa: E402

PROC = ROOT / "data" / "processed"
SQL_OUT = ROOT / "sql" / "outputs"
OUT = ROOT / "powerbi" / "data"

STATE_NAMES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapa", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceara", "DF": "Distrito Federal",
    "ES": "Espirito Santo", "GO": "Goias", "MA": "Maranhao", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais", "PA": "Para", "PB": "Paraiba", "PR": "Parana", "PE": "Pernambuco", "PI": "Piaui",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondonia", "RR": "Roraima",
    "SC": "Santa Catarina", "SP": "Sao Paulo", "SE": "Sergipe", "TO": "Tocantins",
}
SEGMENT_ORDER = {"Champions": 1, "Loyal": 2, "New Customers": 3, "Needs Attention": 4, "About to Sleep": 5, "At Risk": 6, "Lost": 7}
FIRST_MONTH, LAST_MONTH = "2017-01", "2018-08"     # full months (notebook 01, decision 11)

# Delay buckets: the same rule as SQL query Q14
BUCKETS = [(1, "Early by 7+ days"), (2, "On time (0-7 days early)"), (3, "Late 0-3 days"), (4, "Late 3-7 days"),
           (5, "Late more than 7 days"), (6, "Not delivered")]


def q(prefix):
    return pd.read_csv(next(SQL_OUT.glob(f"{prefix}_*.csv")))


def delay_bucket(delay_days):
    out = pd.Series(6, index=delay_days.index)
    ok = delay_days.notna()
    d = delay_days[ok]
    out[ok] = np.select([d <= -7, d <= 0, d <= 3, d <= 7], [1, 2, 3, 4], default=5)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    orders = pd.read_parquet(PROC / "fact_orders.parquet")
    items = pd.read_parquet(PROC / "fact_order_items.parquet")
    products = pd.read_parquet(PROC / "dim_product.parquet")
    valid = orders[orders.is_valid_sale].sort_values("order_id").reset_index(drop=True)

    # ---------- keys ----------
    rfm = q("q12").sort_values("customer_unique_id").reset_index(drop=True)
    rfm["customer_key"] = np.arange(1, len(rfm) + 1)
    cust_key = dict(zip(rfm.customer_unique_id, rfm.customer_key))
    valid["order_key"] = np.arange(1, len(valid) + 1)
    order_key = dict(zip(valid.order_id, valid.order_key))
    products = products.sort_values("product_id").reset_index(drop=True)
    products["product_key"] = np.arange(1, len(products) + 1)
    prod_key = dict(zip(products.product_id, products.product_key))

    # ---------- dim_date: complete calendar years, so time intelligence (YTD, previous month) works ----------
    d = pd.date_range("2016-01-01", "2018-12-31", freq="D")
    dim_date = pd.DataFrame({"date": d.strftime("%Y-%m-%d")})
    dim_date["year"] = d.year
    dim_date["quarter"] = d.quarter
    dim_date["month"] = d.month
    dim_date["month_name"] = d.month_name()
    dim_date["year_month"] = d.strftime("%Y-%m")
    dim_date["month_start"] = d.to_period("M").to_timestamp().strftime("%Y-%m-%d")
    dim_date["day_of_week"] = d.dayofweek + 1
    dim_date["day_name"] = d.day_name()
    dim_date["is_weekend"] = np.where(d.dayofweek >= 5, "Weekend", "Weekday")
    dim_date["analysis_flag"] = ((dim_date.year_month >= FIRST_MONTH) & (dim_date.year_month <= LAST_MONTH)).astype(int)
    dim_date["period_type"] = np.where(dim_date.analysis_flag == 1, "Full month", "Incomplete month")

    # ---------- dim_customer (valid-sale customers, with RFM from Q12) ----------
    first_month = (valid.assign(m=valid.purchase_ts.dt.to_period("M").dt.to_timestamp())
                   .groupby("customer_unique_id").m.min().dt.strftime("%Y-%m-%d"))
    dim_customer = pd.DataFrame({
        "customer_key": rfm.customer_key,
        "state": rfm.customer_state,
        "first_order_month": rfm.customer_unique_id.map(first_month),
        "order_count": rfm.frequency,
        "revenue": rfm.monetary.round(2),
        "recency_days": rfm.recency_days,
        "r_score": rfm.r_score, "f_score": rfm.f_score, "m_score": rfm.m_score,
        "rfm_score": rfm.rfm_score.astype(str),
        "segment": rfm.segment,
        "segment_order": rfm.segment.map(SEGMENT_ORDER),
    })

    # ---------- dim_state (small geography table: names for the map, regions) ----------
    states = sorted(STATE_NAMES)
    dim_state = pd.DataFrame({"state": states, "state_name": [STATE_NAMES[x] for x in states],
                              "region": [STATE_TO_REGION[x] for x in states], "country": "Brazil"})
    assert set(dim_customer.state) <= set(states)

    # ---------- dim_product ----------
    dim_product = pd.DataFrame({"product_key": products.product_key, "product_id": products.product_id,
                                "category": products.category_en, "weight_g": products.weight_g})

    # ---------- fact_orders (valid sales) ----------
    bucket = delay_bucket(valid.delay_days)
    names = dict(BUCKETS)
    fact_orders = pd.DataFrame({
        "order_key": valid.order_key,
        "customer_key": valid.customer_unique_id.map(cust_key),
        "purchase_date": valid.purchase_ts.dt.strftime("%Y-%m-%d"),
        "purchase_hour": valid.purchase_ts.dt.hour,
        "order_status": valid.order_status,
        "payment_type": valid.main_payment_type.fillna("unknown"),
        "items_value": valid.items_value.astype(float).round(2),
        "freight_value": valid.freight_value.astype(float).round(2),
        "review_score": valid.review_score.astype("Int64"),
        "delivery_days": valid.delivery_days.astype(float).round(2),
        "delay_days": valid.delay_days.astype(float).round(2),
        "late_flag": valid.is_late.astype("float64").astype("Int64"),
        "low_review_flag": (valid.review_score.astype("float64") <= 2).astype("float64").where(valid.review_score.notna()).astype("Int64"),
        "delay_bucket": bucket.map(names),
        "delay_bucket_order": bucket,
    })
    assert fact_orders.customer_key.notna().all()

    # ---------- fact_order_items (items of valid orders) ----------
    it = items[items.order_id.isin(order_key)]
    fact_items = pd.DataFrame({
        "order_key": it.order_id.map(order_key), "product_key": it.product_id.map(prod_key),
        "price": it.price.astype(float).round(2), "freight_value": it.freight_value.astype(float).round(2),
    }).sort_values(["order_key", "product_key"]).reset_index(drop=True)

    # ---------- small tables from SQL results ----------
    q11 = q("q11")
    cohort = q11[["cohort_month", "month_index", "cohort_size", "active_customers", "retention_pct"]]
    q13 = q("q13")
    top_customers = pd.DataFrame({
        "customer_key": q13.customer_unique_id.map(cust_key), "customer_unique_id": q13.customer_unique_id,
        "revenue_rank": q13.revenue_rank, "orders": q13.orders,
        "clv_revenue": q13.clv_revenue, "avg_order_value": q13.avg_order_value, "first_order_date": q13.first_order_date,
        "last_order_date": q13.last_order_date, "active_days": q13.active_days,
        "cumulative_revenue_share_pct": q13.cumulative_revenue_share_pct,
    })
    assert top_customers.customer_key.notna().all()
    q8 = q("q08")
    low_perf = pd.DataFrame({"product_key": q8.product_id.map(prod_key), "reviewed_orders": q8.reviewed_orders,
                             "avg_rating": q8.avg_rating, "low_score_pct": q8.low_score_pct,
                             "overall_avg_rating": q8.overall_avg_rating})
    assert low_perf.product_key.notna().all()

    tables = {"dim_date": dim_date, "dim_state": dim_state, "dim_customer": dim_customer, "dim_product": dim_product, "fact_orders": fact_orders,
              "fact_order_items": fact_items, "cohort_retention": cohort, "top_customers": top_customers, "low_performers": low_perf}
    for name, df in tables.items():
        df.to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8", lineterminator="\n")
        print(f"{name:18s} {len(df):>8,} rows  {(OUT / f'{name}.csv').stat().st_size / 1e6:6.2f} MB")

    # ---------- control numbers (to compare with the DAX measures in Power BI) ----------
    total_rev = float(fact_items.price.sum())
    print("\nControl numbers for the DAX check:")
    print(f"  Total Revenue      {total_rev:,.2f}")
    print(f"  Total Orders       {fact_items.order_key.nunique():,}")
    print(f"  AOV                {total_rev / fact_items.order_key.nunique():,.2f}")
    print(f"  Average review     {fact_orders.review_score.astype(float).mean():.4f}")
    print(f"  Late delivery rate {fact_orders.late_flag.astype(float).mean():.4f}")
    print(f"  Customers          {len(dim_customer):,}  repeat customers {(dim_customer.order_count >= 2).sum():,}"
          f"  repeat % {100 * (dim_customer.order_count >= 2).mean():.2f}")


if __name__ == "__main__":
    main()
