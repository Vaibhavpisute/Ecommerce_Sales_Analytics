-- Q09 New vs repeat customers per month
-- Business question: Each month, how many buyers are new and how many came back?
-- Approach: valid sales, customer = customer_unique_id. MIN(month) OVER (PARTITION BY customer)
--   gives the customer's first purchase month over ALL data. In a month, a customer is "new" if
--   it is their first purchase month, and "repeat" if they first bought in an earlier month.
--   Full months only. A customer who buys twice in their first month is still "new" that month.
-- Used later in: EDA notebook, Power BI Customers page.

WITH customer_orders AS (
    SELECT o.customer_unique_id,
           o.order_id,
           o.items_value,
           d.year_month,
           d.in_analysis_period,
           DATE_TRUNC('month', o.purchase_ts)::date AS order_month
    FROM fact_orders o
    JOIN dim_date d ON d.date_key = o.purchase_date_key
    WHERE o.is_valid_sale
),
labeled AS (
    SELECT *, MIN(order_month) OVER (PARTITION BY customer_unique_id) AS first_month
    FROM customer_orders
)
SELECT year_month,
       COUNT(DISTINCT customer_unique_id) FILTER (WHERE order_month = first_month)  AS new_customers,
       COUNT(DISTINCT customer_unique_id) FILTER (WHERE order_month > first_month)  AS repeat_customers,
       COUNT(*) FILTER (WHERE order_month = first_month)                            AS orders_from_new,
       COUNT(*) FILTER (WHERE order_month > first_month)                            AS orders_from_repeat,
       ROUND(SUM(items_value) FILTER (WHERE order_month = first_month), 2)          AS revenue_from_new,
       ROUND(SUM(items_value) FILTER (WHERE order_month > first_month), 2)          AS revenue_from_repeat,
       ROUND(100.0 * COUNT(DISTINCT customer_unique_id) FILTER (WHERE order_month > first_month)
             / COUNT(DISTINCT customer_unique_id), 2)                               AS repeat_customer_pct
FROM labeled
WHERE in_analysis_period
GROUP BY year_month
ORDER BY year_month;
