-- Q05 Revenue by day of week and hour
-- Business question: When do customers buy? Which weekday and hour bring the most orders and revenue?
-- Approach: valid sales in the full-month period. EXTRACT(HOUR) from the purchase time,
--   weekday from dim_date (1 = Monday ... 7 = Sunday). One row per weekday and hour.
-- Used later in: EDA notebook heatmap.

SELECT d.day_of_week,
       d.day_name,
       EXTRACT(HOUR FROM o.purchase_ts)::int  AS hour_of_day,
       COUNT(*)                               AS orders,
       ROUND(SUM(o.items_value), 2)           AS revenue
FROM fact_orders o
JOIN dim_date d ON d.date_key = o.purchase_date_key
WHERE o.is_valid_sale AND d.in_analysis_period
GROUP BY d.day_of_week, d.day_name, EXTRACT(HOUR FROM o.purchase_ts)
ORDER BY d.day_of_week, hour_of_day;
