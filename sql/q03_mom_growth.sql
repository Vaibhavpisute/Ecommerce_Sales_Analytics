-- Q03 Month-over-month (MoM) revenue growth %
-- Business question: By how many percent did revenue grow or fall compared with the month before?
-- Approach: monthly revenue (valid sales, full months only), then LAG() to get the previous month.
--   growth % = (revenue - previous) / previous * 100. The first month has no previous month (empty).
-- Used later in: EDA notebook, Power BI (the DAX MoM Growth % measure must match this), report.

WITH monthly AS (
    SELECT d.year_month, SUM(o.items_value) AS revenue
    FROM fact_orders o
    JOIN dim_date d ON d.date_key = o.purchase_date_key
    WHERE o.is_valid_sale AND d.in_analysis_period
    GROUP BY d.year_month
)
SELECT year_month,
       ROUND(revenue, 2)                                                                 AS revenue,
       ROUND(LAG(revenue) OVER w, 2)                                                     AS previous_month_revenue,
       ROUND(100 * (revenue - LAG(revenue) OVER w) / NULLIF(LAG(revenue) OVER w, 0), 2)  AS mom_growth_pct
FROM monthly
WINDOW w AS (ORDER BY year_month)
ORDER BY year_month;
