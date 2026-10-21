-- Q07 Category revenue share and Pareto 80/20
-- Business question: How much revenue does each category bring, and how many categories make 80% of it?
-- Approach: revenue per category (item price, valid sales). SUM() OVER () for the total,
--   running SUM() OVER (ORDER BY revenue DESC) for the cumulative share.
--   in_top_80pct = the category is needed to reach 80% of revenue.
-- Used later in: EDA notebook Pareto chart, Power BI, report.

WITH category_revenue AS (
    SELECT p.category_en, SUM(i.price) AS revenue
    FROM fact_order_items i
    JOIN fact_orders o ON o.order_id = i.order_id
    JOIN dim_product p ON p.product_id = i.product_id
    WHERE o.is_valid_sale
    GROUP BY p.category_en
),
shares AS (
    SELECT category_en,
           revenue,
           SUM(revenue) OVER ()                                     AS total_revenue,
           SUM(revenue) OVER (ORDER BY revenue DESC, category_en)   AS running_revenue,
           ROW_NUMBER() OVER (ORDER BY revenue DESC, category_en)   AS category_rank
    FROM category_revenue
)
SELECT category_rank,
       category_en,
       ROUND(revenue, 2)                                   AS revenue,
       ROUND(100 * revenue / total_revenue, 2)             AS revenue_share_pct,
       ROUND(100 * running_revenue / total_revenue, 2)     AS cumulative_share_pct,
       (running_revenue - revenue) / total_revenue < 0.80  AS in_top_80pct
FROM shares
ORDER BY category_rank;
