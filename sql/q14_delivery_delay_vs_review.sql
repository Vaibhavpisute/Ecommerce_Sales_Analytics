-- Q14 Delivery delay vs review score
-- Business question: Do late deliveries get worse reviews?
-- Approach: delivered orders with a delivery date and a review. delay_days = delivered date minus the
--   estimated date (below 0 = early, above 0 = late). CASE WHEN puts each order in a delay bucket.
--   Two result levels: 'bucket' (5 delay buckets) and 'late_vs_on_time' (is_late true or false).
--   Each row has n, mean, standard deviation, so the statistics notebook Welch t-test can use them.
--   low_score_pct = share of reviews with score 1 or 2.
-- Used later in: EDA notebook, statistics notebook t-test and probability (P(low review | late)).

WITH base AS (
    SELECT o.delay_days, o.delivery_days, o.is_late, r.review_score
    FROM fact_orders o
    JOIN fact_reviews r ON r.order_id = o.order_id
    WHERE o.order_status = 'delivered' AND o.delay_days IS NOT NULL
),
bucketed AS (
    SELECT *,
           CASE WHEN delay_days <= -7 THEN 1
                WHEN delay_days <= 0  THEN 2
                WHEN delay_days <= 3  THEN 3
                WHEN delay_days <= 7  THEN 4
                ELSE 5 END AS bucket_order,
           CASE WHEN delay_days <= -7 THEN 'Early by 7+ days'
                WHEN delay_days <= 0  THEN 'On time (0-7 days early)'
                WHEN delay_days <= 3  THEN 'Late 0-3 days'
                WHEN delay_days <= 7  THEN 'Late 3-7 days'
                ELSE 'Late more than 7 days' END AS group_name
    FROM base
)
SELECT 'bucket' AS level, bucket_order, group_name,
       COUNT(*)                                     AS orders,
       ROUND(AVG(review_score), 4)                  AS avg_review_score,
       ROUND(STDDEV_SAMP(review_score), 4)          AS sd_review_score,
       ROUND(100 * AVG((review_score <= 2)::int), 2) AS low_score_pct,
       ROUND(AVG(delivery_days), 2)                 AS avg_delivery_days
FROM bucketed
GROUP BY bucket_order, group_name
UNION ALL
SELECT 'late_vs_on_time', CASE WHEN is_late THEN 2 ELSE 1 END,
       CASE WHEN is_late THEN 'Late' ELSE 'On time or early' END,
       COUNT(*),
       ROUND(AVG(review_score), 4),
       ROUND(STDDEV_SAMP(review_score), 4),
       ROUND(100 * AVG((review_score <= 2)::int), 2),
       ROUND(AVG(delivery_days), 2)
FROM bucketed
GROUP BY is_late
ORDER BY level, bucket_order;
