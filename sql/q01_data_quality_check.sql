-- Q01 Data quality check
-- Business question: Is the data in the star schema complete and consistent (nulls, duplicates, orphan records)?
-- Approach: one long result (table_name, check_name, column_name, value).
--   row_count, duplicate_keys (COUNT vs COUNT DISTINCT), null counts per column (jsonb_each),
--   orphan records (LEFT JOIN ... IS NULL), and a few business checks.
-- Used later in: data cleaning check (sql/check_sql_vs_pandas.py compares this output with the pandas summary).

WITH row_counts AS (
    SELECT 'dim_date' AS table_name, 'row_count' AS check_name, NULL::text AS column_name, COUNT(*) AS value FROM dim_date
    UNION ALL SELECT 'dim_customer', 'row_count', NULL, COUNT(*) FROM dim_customer
    UNION ALL SELECT 'dim_product', 'row_count', NULL, COUNT(*) FROM dim_product
    UNION ALL SELECT 'dim_seller', 'row_count', NULL, COUNT(*) FROM dim_seller
    UNION ALL SELECT 'fact_orders', 'row_count', NULL, COUNT(*) FROM fact_orders
    UNION ALL SELECT 'fact_order_items', 'row_count', NULL, COUNT(*) FROM fact_order_items
    UNION ALL SELECT 'fact_payments', 'row_count', NULL, COUNT(*) FROM fact_payments
    UNION ALL SELECT 'fact_reviews', 'row_count', NULL, COUNT(*) FROM fact_reviews
),
duplicate_keys AS (
    SELECT 'dim_date' AS table_name, 'duplicate_keys' AS check_name, NULL::text AS column_name, COUNT(*) - COUNT(DISTINCT date_key) AS value FROM dim_date
    UNION ALL SELECT 'dim_customer', 'duplicate_keys', NULL, COUNT(*) - COUNT(DISTINCT customer_unique_id) FROM dim_customer
    UNION ALL SELECT 'dim_product', 'duplicate_keys', NULL, COUNT(*) - COUNT(DISTINCT product_id) FROM dim_product
    UNION ALL SELECT 'dim_seller', 'duplicate_keys', NULL, COUNT(*) - COUNT(DISTINCT seller_id) FROM dim_seller
    UNION ALL SELECT 'fact_orders', 'duplicate_keys', NULL, COUNT(*) - COUNT(DISTINCT order_id) FROM fact_orders
    UNION ALL SELECT 'fact_order_items', 'duplicate_keys', NULL, COUNT(*) - COUNT(DISTINCT (order_id, order_item_id)) FROM fact_order_items
    UNION ALL SELECT 'fact_payments', 'duplicate_keys', NULL, COUNT(*) - COUNT(DISTINCT (order_id, payment_sequential)) FROM fact_payments
    UNION ALL SELECT 'fact_reviews', 'duplicate_keys', NULL, COUNT(*) - COUNT(DISTINCT order_id) FROM fact_reviews
),
null_counts AS (
    SELECT 'dim_date' AS table_name, 'null_count' AS check_name, e.key AS column_name, COUNT(*) FILTER (WHERE e.value = 'null'::jsonb) AS value FROM dim_date t, jsonb_each(to_jsonb(t)) e GROUP BY e.key
    UNION ALL SELECT 'dim_customer', 'null_count', e.key, COUNT(*) FILTER (WHERE e.value = 'null'::jsonb) FROM dim_customer t, jsonb_each(to_jsonb(t)) e GROUP BY e.key
    UNION ALL SELECT 'dim_product', 'null_count', e.key, COUNT(*) FILTER (WHERE e.value = 'null'::jsonb) FROM dim_product t, jsonb_each(to_jsonb(t)) e GROUP BY e.key
    UNION ALL SELECT 'dim_seller', 'null_count', e.key, COUNT(*) FILTER (WHERE e.value = 'null'::jsonb) FROM dim_seller t, jsonb_each(to_jsonb(t)) e GROUP BY e.key
    UNION ALL SELECT 'fact_orders', 'null_count', e.key, COUNT(*) FILTER (WHERE e.value = 'null'::jsonb) FROM fact_orders t, jsonb_each(to_jsonb(t)) e GROUP BY e.key
    UNION ALL SELECT 'fact_order_items', 'null_count', e.key, COUNT(*) FILTER (WHERE e.value = 'null'::jsonb) FROM fact_order_items t, jsonb_each(to_jsonb(t)) e GROUP BY e.key
    UNION ALL SELECT 'fact_payments', 'null_count', e.key, COUNT(*) FILTER (WHERE e.value = 'null'::jsonb) FROM fact_payments t, jsonb_each(to_jsonb(t)) e GROUP BY e.key
    UNION ALL SELECT 'fact_reviews', 'null_count', e.key, COUNT(*) FILTER (WHERE e.value = 'null'::jsonb) FROM fact_reviews t, jsonb_each(to_jsonb(t)) e GROUP BY e.key
),
orphans AS (
    SELECT 'fact_order_items' AS table_name, 'orphan_order' AS check_name, NULL::text AS column_name, COUNT(*) AS value
        FROM fact_order_items i LEFT JOIN fact_orders o USING (order_id) WHERE o.order_id IS NULL
    UNION ALL SELECT 'fact_order_items', 'orphan_product', NULL, COUNT(*)
        FROM fact_order_items i LEFT JOIN dim_product p USING (product_id) WHERE p.product_id IS NULL
    UNION ALL SELECT 'fact_order_items', 'orphan_seller', NULL, COUNT(*)
        FROM fact_order_items i LEFT JOIN dim_seller s USING (seller_id) WHERE s.seller_id IS NULL
    UNION ALL SELECT 'fact_orders', 'orphan_customer', NULL, COUNT(*)
        FROM fact_orders o LEFT JOIN dim_customer c USING (customer_unique_id) WHERE c.customer_unique_id IS NULL
    UNION ALL SELECT 'fact_orders', 'orphan_date', NULL, COUNT(*)
        FROM fact_orders o LEFT JOIN dim_date d ON d.date_key = o.purchase_date_key WHERE d.date_key IS NULL
    UNION ALL SELECT 'fact_payments', 'orphan_order', NULL, COUNT(*)
        FROM fact_payments p LEFT JOIN fact_orders o USING (order_id) WHERE o.order_id IS NULL
    UNION ALL SELECT 'fact_reviews', 'orphan_order', NULL, COUNT(*)
        FROM fact_reviews r LEFT JOIN fact_orders o USING (order_id) WHERE o.order_id IS NULL
),
business_checks AS (
    SELECT 'fact_orders' AS table_name, 'orders_without_items' AS check_name, NULL::text AS column_name, COUNT(*) AS value
        FROM fact_orders o LEFT JOIN fact_order_items i USING (order_id) WHERE i.order_id IS NULL
    UNION ALL SELECT 'fact_orders', 'orders_without_payment', NULL, COUNT(*)
        FROM fact_orders o LEFT JOIN fact_payments p USING (order_id) WHERE p.order_id IS NULL
    UNION ALL SELECT 'fact_orders', 'orders_without_review', NULL, COUNT(*)
        FROM fact_orders o LEFT JOIN fact_reviews r USING (order_id) WHERE r.order_id IS NULL
    UNION ALL SELECT 'fact_orders', 'delivered_without_delivery_date', NULL, COUNT(*)
        FROM fact_orders WHERE order_status = 'delivered' AND delivered_ts IS NULL
    UNION ALL SELECT 'fact_orders', 'delivered_before_purchase', NULL, COUNT(*)
        FROM fact_orders WHERE delivered_ts < purchase_ts
    UNION ALL SELECT 'fact_order_items', 'price_not_positive', NULL, COUNT(*)
        FROM fact_order_items WHERE price <= 0
    UNION ALL SELECT 'fact_reviews', 'score_outside_1_to_5', NULL, COUNT(*)
        FROM fact_reviews WHERE review_score NOT BETWEEN 1 AND 5
)
SELECT * FROM row_counts
UNION ALL SELECT * FROM duplicate_keys
UNION ALL SELECT * FROM null_counts
UNION ALL SELECT * FROM orphans
UNION ALL SELECT * FROM business_checks
ORDER BY check_name, table_name, column_name;
