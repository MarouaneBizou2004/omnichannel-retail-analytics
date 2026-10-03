-- ==============================================================================
-- Query 06: Discount Elasticity, Return Propensity, and Margin Leakage Analysis
-- Purpose: Quantifies margin destruction across promotional discount bands.
-- Techniques: CASE bucketing, conditional aggregations, unit economics breakdown.
-- ==============================================================================

WITH line_discount_bands AS (
    SELECT
        foi.item_key,
        foi.order_id,
        foi.product_key,
        foi.quantity,
        foi.unit_price,
        foi.gross_revenue,
        foi.discount_percent,
        foi.discount_amount,
        foi.net_revenue,
        foi.cogs,
        foi.gross_profit,
        foi.order_status,
        foi.is_returned,
        CASE
            WHEN foi.discount_percent = 0.00 THEN '1. Full Price (0%)'
            WHEN foi.discount_percent <= 0.10 THEN '2. Light Discount (1-10%)'
            WHEN foi.discount_percent <= 0.20 THEN '3. Moderate Discount (11-20%)'
            WHEN foi.discount_percent <= 0.30 THEN '4. Deep Promo (21-30%)'
            ELSE '5. Clearance (> 30%)'
        END AS discount_depth_band
    FROM fact_order_items foi
),
band_aggregates AS (
    SELECT
        discount_depth_band,
        COUNT(item_key) AS total_line_items,
        COUNT(CASE WHEN order_status = 'Completed' THEN item_key END) AS completed_items,
        COUNT(CASE WHEN is_returned = 1 THEN item_key END) AS returned_items,
        SUM(gross_revenue) AS total_gross_revenue,
        SUM(discount_amount) AS total_discount_dollars,
        SUM(CASE WHEN order_status = 'Completed' THEN net_revenue ELSE 0 END) AS realized_net_revenue,
        SUM(CASE WHEN order_status = 'Completed' THEN cogs ELSE 0 END) AS realized_cogs,
        SUM(CASE WHEN order_status = 'Completed' THEN gross_profit ELSE 0 END) AS realized_gross_profit,
        AVG(quantity) AS avg_units_per_line
    FROM line_discount_bands
    GROUP BY discount_depth_band
)
SELECT
    discount_depth_band,
    total_line_items,
    ROUND(total_gross_revenue, 2) AS gross_revenue,
    ROUND(total_discount_dollars, 2) AS discounts_granted,
    ROUND(realized_net_revenue, 2) AS realized_net_revenue,
    ROUND(realized_gross_profit, 2) AS realized_gross_profit,
    ROUND((realized_gross_profit * 100.0) / NULLIF(realized_net_revenue, 0), 2) AS realized_margin_pct,
    ROUND((returned_items * 100.0) / NULLIF(total_line_items, 0), 2) AS return_rate_pct,
    ROUND(avg_units_per_line, 2) AS avg_units_per_line
FROM band_aggregates
ORDER BY discount_depth_band ASC;
