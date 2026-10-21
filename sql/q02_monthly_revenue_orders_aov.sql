-- Q02 Monthly revenue, orders and average order value (AOV)
-- Business question: How do revenue, number of orders and AOV change month by month?
-- Approach: valid sales only (is_valid_sale). Revenue = item price without freight (items_value).
--   AOV = revenue / orders. Join dim_date for the month. All months are shown;
--   in_analysis_period marks the full months (2017-01 to 2018-08) that later analysis uses.
-- Used later in: EDA notebook, forecast notebook input, Power BI Sales page, Excel KPIs.

SELECT d.year_month,
       BOOL_OR(d.in_analysis_period)               AS in_analysis_period,
       COUNT(*)                                    AS orders,
       ROUND(SUM(o.items_value), 2)                AS revenue,
       ROUND(SUM(o.freight_value), 2)              AS freight,
       ROUND(SUM(o.items_value) / COUNT(*), 2)     AS aov
FROM fact_orders o
JOIN dim_date d ON d.date_key = o.purchase_date_key
WHERE o.is_valid_sale
GROUP BY d.year_month
ORDER BY d.year_month;
