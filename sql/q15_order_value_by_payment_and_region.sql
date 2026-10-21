-- Q15 Order value by payment type and by state / region
-- Business question: Does order value differ by payment type, and which states and regions bring the most revenue?
-- Approach: valid sales. Order value = items_value (item price, no freight). Brazilian region is mapped from the
--   state with CASE WHEN. GROUP BY GROUPING SETS (ROLLUP (region, state), (payment_type), (region, payment_type))
--   gives all levels in one result. The column "level" names each level (GROUPING() tells which columns are rolled up).
--   Each row has n, total, mean and standard deviation (for the statistics notebook ANOVA description).
-- Used later in: statistics notebook ANOVA, Excel pivot, Power BI state map.

WITH base AS (
    SELECT CASE
               WHEN customer_state IN ('AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO')                    THEN 'North'
               WHEN customer_state IN ('AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE')        THEN 'Northeast'
               WHEN customer_state IN ('DF', 'GO', 'MT', 'MS')                                      THEN 'Central-West'
               WHEN customer_state IN ('ES', 'MG', 'RJ', 'SP')                                      THEN 'Southeast'
               WHEN customer_state IN ('PR', 'RS', 'SC')                                            THEN 'South'
               ELSE 'Unknown'
           END AS region,
           customer_state AS state,
           COALESCE(main_payment_type, 'unknown') AS payment_type,
           items_value
    FROM fact_orders
    WHERE is_valid_sale
),
grouped AS (
    SELECT region, state, payment_type,
           GROUPING(region) AS g_region, GROUPING(state) AS g_state, GROUPING(payment_type) AS g_payment,
           COUNT(*)                          AS orders,
           ROUND(SUM(items_value), 2)        AS revenue,
           ROUND(AVG(items_value), 2)        AS avg_order_value,
           ROUND(STDDEV_SAMP(items_value), 2) AS sd_order_value
    FROM base
    GROUP BY GROUPING SETS (ROLLUP (region, state), (payment_type), (region, payment_type))
)
SELECT CASE
           WHEN g_region = 1 AND g_state = 1 AND g_payment = 1 THEN 'All orders'
           WHEN g_region = 0 AND g_state = 1 AND g_payment = 1 THEN 'Region'
           WHEN g_region = 0 AND g_state = 0 AND g_payment = 1 THEN 'State'
           WHEN g_region = 1 AND g_state = 1 AND g_payment = 0 THEN 'Payment type'
           ELSE 'Region and payment type'
       END AS level,
       region, state, payment_type, orders, revenue, avg_order_value, sd_order_value
FROM grouped
ORDER BY CASE WHEN g_region = 1 AND g_state = 1 AND g_payment = 1 THEN 1
              WHEN g_region = 0 AND g_state = 1 AND g_payment = 1 THEN 2
              WHEN g_region = 0 AND g_state = 0 AND g_payment = 1 THEN 3
              WHEN g_region = 1 AND g_state = 1 AND g_payment = 0 THEN 4
              ELSE 5 END,
         region, state, payment_type;
