-- Q12 RFM scores and customer segments
-- Business question: Who are our best, average and lost customers?
-- Approach: valid sales, one row per customer_unique_id.
--   Recency  = days from the day after the last order in the data to the customer's last order.
--   Frequency = number of orders.  Monetary = sum of item prices (items_value).
--   R score = NTILE(5) by last order time (5 = most recent). M score = NTILE(5) by money (5 = highest).
--   F score is NOT an NTILE: about 97% of customers have one order, and NTILE would split identical
--   customers into different scores. So: 1 order = 1, 2 orders = 3, 3 or more orders = 5.
--   Ties inside NTILE are split by customer id, so the result is always the same.
--   Segments (CASE WHEN): Champions, Loyal, At Risk (repeat buyers), New Customers, Needs Attention,
--   About to Sleep, Lost (one-time buyers, by recency).
-- Used later in: Excel (XLOOKUP segment table), Power BI Customers page, statistics notebook chi-square test.

WITH ref AS (
    SELECT MAX(purchase_date) + 1 AS ref_date FROM fact_orders WHERE is_valid_sale
),
customer AS (
    SELECT customer_unique_id,
           MAX(purchase_ts)    AS last_order_ts,
           COUNT(*)            AS frequency,
           SUM(items_value)    AS monetary
    FROM fact_orders
    WHERE is_valid_sale
    GROUP BY customer_unique_id
),
scored AS (
    SELECT c.customer_unique_id,
           (r.ref_date - c.last_order_ts::date)                                   AS recency_days,
           c.frequency,
           c.monetary,
           NTILE(5) OVER (ORDER BY c.last_order_ts, c.customer_unique_id)         AS r_score,
           CASE WHEN c.frequency = 1 THEN 1 WHEN c.frequency = 2 THEN 3 ELSE 5 END AS f_score,
           NTILE(5) OVER (ORDER BY c.monetary, c.customer_unique_id)              AS m_score
    FROM customer c
    CROSS JOIN ref r
)
SELECT s.customer_unique_id,
       dc.state                                       AS customer_state,
       s.recency_days,
       s.frequency,
       ROUND(s.monetary, 2)                           AS monetary,
       s.r_score,
       s.f_score,
       s.m_score,
       s.r_score::text || s.f_score::text || s.m_score::text AS rfm_score,
       CASE
           WHEN s.r_score >= 4 AND s.f_score >= 3 AND s.m_score >= 4 THEN 'Champions'
           WHEN s.f_score >= 3 AND s.r_score >= 3                    THEN 'Loyal'
           WHEN s.f_score >= 3 AND s.r_score <= 2                    THEN 'At Risk'
           WHEN s.f_score = 1  AND s.r_score >= 4                    THEN 'New Customers'
           WHEN s.f_score = 1  AND s.r_score = 3                     THEN 'Needs Attention'
           WHEN s.f_score = 1  AND s.r_score = 2                     THEN 'About to Sleep'
           ELSE 'Lost'
       END AS segment
FROM scored s
JOIN dim_customer dc USING (customer_unique_id)
ORDER BY s.customer_unique_id;
