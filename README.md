# Ecommerce_Sales_Analytics

Data analyst portfolio project. Part 2 of my e-commerce data project:
the data comes through my pipeline [Enterprise_Data_Analysis](https://github.com/Vaibhavpisute/Enterprise_Data_Analysis)
(PostgreSQL -> PySpark -> MinIO/Hive), then it is cleaned, analysed with SQL, Python, Excel and Power BI.

Data: Olist Brazilian E-Commerce Public Dataset (about 100k real orders, 2016-2018). See `data/DATA_SOURCE.md`.


## SQL analysis: 15 queries

Each query file starts with the business question, the approach and where it is used later.
Results are saved in `sql/outputs/`. Run them all with `.venv\Scripts\python sql\run_all_queries.py`.
Revenue means item price without freight, for valid sales only (not canceled or unavailable).

| # | Query | Main SQL skill | Result |
|---|---|---|---|
| 1 | [Data quality check](sql/q01_data_quality_check.sql) | COUNT, LEFT JOIN ... IS NULL | [csv](sql/outputs/q01_data_quality_check.csv) |
| 2 | [Monthly revenue, orders and AOV](sql/q02_monthly_revenue_orders_aov.sql) | DATE / GROUP BY | [csv](sql/outputs/q02_monthly_revenue_orders_aov.csv) |
| 3 | [Month-over-month growth %](sql/q03_mom_growth.sql) | LAG() | [csv](sql/outputs/q03_mom_growth.csv) |
| 4 | [Running total and 3-month moving average](sql/q04_running_total_moving_avg.sql) | SUM() OVER, AVG() OVER (ROWS ...) | [csv](sql/outputs/q04_running_total_moving_avg.csv) |
| 5 | [Revenue by weekday and hour](sql/q05_revenue_by_weekday_hour.sql) | EXTRACT, GROUP BY | [csv](sql/outputs/q05_revenue_by_weekday_hour.csv) |
| 6 | [Top 10 products per category](sql/q06_top10_products_per_category.sql) | DENSE_RANK() OVER (PARTITION BY) | [csv](sql/outputs/q06_top10_products_per_category.csv) |
| 7 | [Category share and Pareto 80/20](sql/q07_category_share_pareto.sql) | SUM() OVER (), running % | [csv](sql/outputs/q07_category_share_pareto.csv) |
| 8 | [Low performers: many orders, low rating](sql/q08_low_performers.sql) | CTE, JOIN, HAVING | [csv](sql/outputs/q08_low_performers.csv) |
| 9 | [New vs repeat customers per month](sql/q09_new_vs_repeat_customers.sql) | CTE, MIN() OVER (PARTITION BY) | [csv](sql/outputs/q09_new_vs_repeat_customers.csv) |
| 10 | [Repeat-purchase rate and days between orders](sql/q10_repeat_rate_days_between.sql) | LEAD(), date difference | [csv](sql/outputs/q10_repeat_rate_days_between.csv) |
| 11 | [Monthly cohort retention](sql/q11_cohort_retention.sql) | multiple CTEs, cohort logic | [csv](sql/outputs/q11_cohort_retention.csv) |
| 12 | [RFM scores and segments](sql/q12_rfm_segments.sql) | NTILE(5), CASE WHEN | [csv](sql/outputs/q12_rfm_segments.csv) |
| 13 | [Customer lifetime value and top 5%](sql/q13_customer_lifetime_value_top5.sql) | PERCENT_RANK() | [csv](sql/outputs/q13_customer_lifetime_value_top5.csv) |
| 14 | [Delivery delay vs review score](sql/q14_delivery_delay_vs_review.sql) | CASE WHEN buckets, AVG | [csv](sql/outputs/q14_delivery_delay_vs_review.csv) |
| 15 | [Order value by payment type and region](sql/q15_order_value_by_payment_and_region.sql) | GROUPING SETS / ROLLUP | [csv](sql/outputs/q15_order_value_by_payment_and_region.csv) |

Checks: `.venv\Scripts\python sql\check_sql_vs_pandas.py` compares Q1 and 5 other queries with pandas
(results in `sql/outputs/check_*.csv`).
