-- Q04 Running total and 3-month moving average of revenue
-- Business question: What is the cumulative revenue, and what is the smoothed trend?
-- Approach: monthly revenue (valid sales, full months only). SUM() OVER for the running total.
--   AVG() OVER (ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) for the moving average.
--   The moving average is empty for the first two months (not enough months).
-- Used later in: EDA notebook, forecast notebook baseline (must match).

WITH monthly AS (
    SELECT d.year_month, SUM(o.items_value) AS revenue
    FROM fact_orders o
    JOIN dim_date d ON d.date_key = o.purchase_date_key
    WHERE o.is_valid_sale AND d.in_analysis_period
    GROUP BY d.year_month
)
SELECT year_month,
       ROUND(revenue, 2)                                                       AS revenue,
       ROUND(SUM(revenue) OVER (ORDER BY year_month), 2)                       AS running_total,
       CASE WHEN COUNT(*) OVER w = 3 THEN ROUND(AVG(revenue) OVER w, 2) END    AS moving_avg_3m
FROM monthly
WINDOW w AS (ORDER BY year_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
ORDER BY year_month;
