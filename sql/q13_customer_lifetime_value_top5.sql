-- Q13 Customer lifetime value (CLV) and the top 5% of customers
-- Business question: How much revenue do our best customers bring, and how much of the total is it?
-- Approach: valid sales, one row per customer_unique_id. CLV here is the HISTORICAL revenue
--   (sum of item prices) in the data period. It is not a prediction.
--   PERCENT_RANK() OVER (ORDER BY revenue) marks the top 5% (>= 0.95).
--   Running SUM() OVER gives the cumulative share of total revenue. Only the top 5% are returned.
-- Used later in: Power BI Customers page (top customers), recommendations in the report.

WITH customer AS (
    SELECT customer_unique_id,
           COUNT(*)              AS orders,
           SUM(items_value)      AS clv_revenue,
           MIN(purchase_date)    AS first_order_date,
           MAX(purchase_date)    AS last_order_date
    FROM fact_orders
    WHERE is_valid_sale
    GROUP BY customer_unique_id
),
ranked AS (
    SELECT *,
           PERCENT_RANK() OVER (ORDER BY clv_revenue, customer_unique_id)            AS percent_rank,
           ROW_NUMBER()   OVER (ORDER BY clv_revenue DESC, customer_unique_id)       AS revenue_rank,
           SUM(clv_revenue) OVER (ORDER BY clv_revenue DESC, customer_unique_id)     AS running_revenue,
           SUM(clv_revenue) OVER ()                                                  AS total_revenue
    FROM customer
)
SELECT r.revenue_rank,
       r.customer_unique_id,
       dc.state                                         AS customer_state,
       r.orders,
       ROUND(r.clv_revenue, 2)                          AS clv_revenue,
       ROUND(r.clv_revenue / r.orders, 2)               AS avg_order_value,
       r.first_order_date,
       r.last_order_date,
       r.last_order_date - r.first_order_date           AS active_days,
       ROUND(r.percent_rank::numeric, 4)                AS percent_rank,
       ROUND(100 * r.running_revenue / r.total_revenue, 2) AS cumulative_revenue_share_pct
FROM ranked r
JOIN dim_customer dc USING (customer_unique_id)
WHERE r.percent_rank >= 0.95
ORDER BY r.revenue_rank;
