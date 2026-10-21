-- Q10 Repeat-purchase rate and average days between orders
-- Business question: How many customers buy again, and how long do they wait?
-- Approach: valid sales, customer = customer_unique_id. LEAD() gets each customer's next order time.
--   Days between = next purchase time - this purchase time (in days). Result is a metric / value list.
--   Orders made on the same day are included (days between close to 0); see same_day_share_pct.
-- Used later in: EDA notebook, report.

WITH orders_v AS (
    SELECT customer_unique_id, order_id, purchase_ts
    FROM fact_orders
    WHERE is_valid_sale
),
per_customer AS (
    SELECT customer_unique_id, COUNT(*) AS n_orders
    FROM orders_v
    GROUP BY customer_unique_id
),
gaps AS (
    SELECT EXTRACT(EPOCH FROM (LEAD(purchase_ts) OVER (PARTITION BY customer_unique_id ORDER BY purchase_ts, order_id)
                               - purchase_ts)) / 86400.0 AS days_to_next
    FROM orders_v
),
gap_stats AS (
    SELECT COUNT(*)                                                  AS n_gaps,
           AVG(days_to_next)                                         AS avg_days,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_to_next) AS median_days,
           AVG((days_to_next < 1)::int)                              AS same_day_share
    FROM gaps
    WHERE days_to_next IS NOT NULL
),
customer_stats AS (
    SELECT COUNT(*)                                AS customers,
           COUNT(*) FILTER (WHERE n_orders >= 2)   AS repeat_customers,
           COUNT(*) FILTER (WHERE n_orders = 1)    AS orders_1,
           COUNT(*) FILTER (WHERE n_orders = 2)    AS orders_2,
           COUNT(*) FILTER (WHERE n_orders = 3)    AS orders_3,
           COUNT(*) FILTER (WHERE n_orders >= 4)   AS orders_4_plus
    FROM per_customer
)
SELECT 'customers' AS metric, customers::numeric AS value FROM customer_stats
UNION ALL SELECT 'repeat_customers', repeat_customers FROM customer_stats
UNION ALL SELECT 'repeat_purchase_rate_pct', ROUND(100.0 * repeat_customers / customers, 2) FROM customer_stats
UNION ALL SELECT 'customers_with_1_order', orders_1 FROM customer_stats
UNION ALL SELECT 'customers_with_2_orders', orders_2 FROM customer_stats
UNION ALL SELECT 'customers_with_3_orders', orders_3 FROM customer_stats
UNION ALL SELECT 'customers_with_4_plus_orders', orders_4_plus FROM customer_stats
UNION ALL SELECT 'order_gaps_counted', n_gaps FROM gap_stats
UNION ALL SELECT 'avg_days_between_orders', ROUND(avg_days::numeric, 1) FROM gap_stats
UNION ALL SELECT 'median_days_between_orders', ROUND(median_days::numeric, 1) FROM gap_stats
UNION ALL SELECT 'same_day_share_pct', ROUND(100 * same_day_share::numeric, 2) FROM gap_stats;
