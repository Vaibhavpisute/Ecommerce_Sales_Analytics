-- Q08 Low performers: many orders but low rating
-- Business question: Which products sell often but disappoint customers?
-- Approach: CTE with one row per (order, product), JOIN to the order's review, group by product.
--   HAVING keeps products with at least 30 reviewed orders AND an average rating at least
--   0.5 points below the overall average rating (shown in the output). Valid sales only.
-- Used later in: Power BI Products page, recommendations in the report.

WITH overall AS (
    SELECT AVG(review_score) AS avg_rating FROM fact_reviews
),
order_products AS (
    SELECT DISTINCT i.order_id, i.product_id
    FROM fact_order_items i
    JOIN fact_orders o ON o.order_id = i.order_id
    WHERE o.is_valid_sale
),
product_stats AS (
    SELECT op.product_id,
           p.category_en,
           COUNT(*)                         AS reviewed_orders,
           AVG(r.review_score)              AS avg_rating,
           AVG((r.review_score <= 2)::int)  AS low_score_share
    FROM order_products op
    JOIN fact_reviews r ON r.order_id = op.order_id
    JOIN dim_product p  ON p.product_id = op.product_id
    GROUP BY op.product_id, p.category_en
    HAVING COUNT(*) >= 30
       AND AVG(r.review_score) < (SELECT avg_rating - 0.5 FROM overall)
)
SELECT ps.product_id,
       ps.category_en,
       ps.reviewed_orders,
       ROUND(ps.avg_rating, 2)               AS avg_rating,
       ROUND(100 * ps.low_score_share, 1)    AS low_score_pct,
       ROUND((SELECT avg_rating FROM overall), 2) AS overall_avg_rating
FROM product_stats ps
ORDER BY ps.avg_rating, ps.reviewed_orders DESC, ps.product_id;
