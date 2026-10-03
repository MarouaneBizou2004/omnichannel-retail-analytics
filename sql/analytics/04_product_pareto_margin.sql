-- ==============================================================================
-- Query 04: Product Portfolio Pareto (80/20) and ABC Profitability Classification
-- Purpose: Identifies revenue concentration, margin drag, and inventory performance.
-- Techniques: CTEs, Cumulative Window Aggregations (SUM() OVER (ORDER BY ROWS)),
--             Ratio-to-Report calculations, ABC classification CASE logic.
-- ==============================================================================

WITH product_performance AS (
    SELECT
        p.product_key,
        p.product_id,
        p.product_name,
        p.category,
        p.subcategory,
        p.unit_price,
        p.unit_cost,
        p.standard_margin_rate,
        SUM(foi.quantity) AS total_units_sold,
        SUM(foi.gross_revenue) AS gross_revenue,
        SUM(foi.discount_amount) AS total_discounts,
        SUM(foi.net_revenue) AS net_revenue,
        SUM(foi.cogs) AS total_cogs,
        SUM(foi.gross_profit) AS realized_gross_profit,
        ROUND(SUM(foi.gross_profit) * 100.0 / NULLIF(SUM(foi.net_revenue), 0), 2) AS realized_margin_pct
    FROM dim_product p
    JOIN fact_order_items foi ON p.product_key = foi.product_key
    WHERE foi.order_status = 'Completed'
    GROUP BY
        p.product_key, p.product_id, p.product_name, p.category,
        p.subcategory, p.unit_price, p.unit_cost, p.standard_margin_rate
),
cumulative_metrics AS (
    SELECT
        product_id,
        product_name,
        category,
        subcategory,
        total_units_sold,
        net_revenue,
        realized_gross_profit,
        realized_margin_pct,
        ROUND(standard_margin_rate * 100.0, 2) AS target_margin_pct,
        ROUND((realized_margin_pct - (standard_margin_rate * 100.0)), 2) AS margin_variance_pts,
        -- Running cumulative revenue sum
        SUM(net_revenue) OVER (ORDER BY net_revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_revenue,
        -- Total enterprise revenue for ratio-to-report
        SUM(net_revenue) OVER () AS total_enterprise_revenue,
        -- Running cumulative profit sum
        SUM(realized_gross_profit) OVER (ORDER BY realized_gross_profit DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_profit,
        SUM(realized_gross_profit) OVER () AS total_enterprise_profit
    FROM product_performance
),
pareto_classification AS (
    SELECT
        product_id,
        product_name,
        category,
        subcategory,
        total_units_sold,
        ROUND(net_revenue, 2) AS net_revenue,
        ROUND(realized_gross_profit, 2) AS realized_gross_profit,
        realized_margin_pct,
        target_margin_pct,
        margin_variance_pts,
        ROUND((cumulative_revenue * 100.0) / total_enterprise_revenue, 2) AS cumulative_revenue_pct,
        ROUND((cumulative_profit * 100.0) / total_enterprise_profit, 2) AS cumulative_profit_pct,
        CASE
            WHEN (cumulative_revenue * 100.0) / total_enterprise_revenue <= 80.0 THEN 'Class A (Top 80% Revenue)'
            WHEN (cumulative_revenue * 100.0) / total_enterprise_revenue <= 95.0 THEN 'Class B (Next 15% Revenue)'
            ELSE 'Class C (Long Tail 5%)'
        END AS abc_revenue_class
    FROM cumulative_metrics
)
SELECT
    abc_revenue_class,
    COUNT(product_id) AS sku_count,
    ROUND(SUM(net_revenue), 2) AS class_total_revenue,
    ROUND(SUM(net_revenue) * 100.0 / (SELECT SUM(net_revenue) FROM pareto_classification), 2) AS revenue_share_pct,
    ROUND(SUM(realized_gross_profit), 2) AS class_total_profit,
    ROUND(SUM(realized_gross_profit) * 100.0 / NULLIF(SUM(net_revenue), 0), 2) AS class_margin_rate_pct,
    ROUND(AVG(margin_variance_pts), 2) AS avg_margin_erosion_points
FROM pareto_classification
GROUP BY abc_revenue_class
ORDER BY class_total_revenue DESC;
