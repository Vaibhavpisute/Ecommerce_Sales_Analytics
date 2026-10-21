-- Q11 Monthly cohort retention table
-- Business question: Of the customers who first bought in a given month, how many buy again in the next months?
-- Approach: several CTEs. cohort = month of the customer's first valid order (customer_unique_id).
--   activity = months in which the customer ordered. month_index = months since the cohort month (0 = first month).
--   retention % = active customers / cohort size. Cohorts 2017-01 to 2018-08, activity up to 2018-08, index 0 to 12.
--   Late cohorts have fewer months, so their later cells do not exist (the data ends).
-- Used later in: EDA notebook heatmap, Power BI Customers page (cohort matrix).

WITH first_orders AS (
    SELECT customer_unique_id,
           DATE_TRUNC('month', MIN(purchase_ts))::date AS cohort_month
    FROM fact_orders
    WHERE is_valid_sale
    GROUP BY customer_unique_id
),
activity AS (
    SELECT DISTINCT customer_unique_id,
           DATE_TRUNC('month', purchase_ts)::date AS activity_month
    FROM fact_orders
    WHERE is_valid_sale
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM first_orders
    GROUP BY cohort_month
),
retention AS (
    SELECT f.cohort_month,
           (EXTRACT(YEAR FROM a.activity_month) * 12 + EXTRACT(MONTH FROM a.activity_month))
         - (EXTRACT(YEAR FROM f.cohort_month)   * 12 + EXTRACT(MONTH FROM f.cohort_month)) AS month_index,
           COUNT(*) AS active_customers
    FROM first_orders f
    JOIN activity a USING (customer_unique_id)
    WHERE f.cohort_month BETWEEN DATE '2017-01-01' AND DATE '2018-08-01'
      AND a.activity_month <= DATE '2018-08-01'
    GROUP BY f.cohort_month, month_index
)
SELECT TO_CHAR(r.cohort_month, 'YYYY-MM')                        AS cohort_month,
       r.month_index::int                                        AS month_index,
       c.cohort_size,
       r.active_customers,
       ROUND(100.0 * r.active_customers / c.cohort_size, 2)      AS retention_pct
FROM retention r
JOIN cohort_size c USING (cohort_month)
WHERE r.month_index BETWEEN 0 AND 12
ORDER BY r.cohort_month, r.month_index;
