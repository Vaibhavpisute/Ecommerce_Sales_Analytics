-- Q06 Top 10 products per category
-- Business question: Which products earn the most inside each category?
-- Approach: revenue per product (item price, valid sales), then DENSE_RANK() OVER (PARTITION BY category).
--   Keep rank 1 to 10. Olist has no product names, so the product_id is shown.
-- Used later in: Power BI Products page, Excel.

WITH product_revenue AS (
    SELECT p.category_en,
           i.product_id,
           COUNT(DISTINCT i.order_id) AS orders,
           COUNT(*)                   AS units,
           SUM(i.price)               AS revenue
    FROM fact_order_items i
    JOIN fact_orders o ON o.order_id = i.order_id
    JOIN dim_product p ON p.product_id = i.product_id
    WHERE o.is_valid_sale
    GROUP BY p.category_en, i.product_id
),
ranked AS (
    SELECT *, DENSE_RANK() OVER (PARTITION BY category_en ORDER BY revenue DESC) AS rank_in_category
    FROM product_revenue
)
SELECT category_en, rank_in_category, product_id, orders, units, ROUND(revenue, 2) AS revenue
FROM ranked
WHERE rank_in_category <= 10
ORDER BY category_en, rank_in_category, product_id;
