-- ==============================================================================
-- Query 01: Executive Scorecard & Year-over-Year (YoY) Financial KPIs
-- Purpose: Delivers enterprise-wide top-line metrics, margins, and operational health.
-- Techniques: CTEs, Conditional Aggregations, Window Functions, YoY Growth Rates.
-- ==============================================================================

WITH yearly_metrics AS (
    SELECT
        d.calendar_year,
        COUNT(DISTINCT fo.order_id) AS total_orders_placed,
        COUNT(DISTINCT CASE WHEN fo.order_status = 'Completed' THEN fo.order_id END) AS completed_orders,
        COUNT(DISTINCT CASE WHEN fo.order_status = 'Returned' THEN fo.order_id END) AS returned_orders,
        COUNT(DISTINCT CASE WHEN fo.order_status = 'Cancelled' THEN fo.order_id END) AS cancelled_orders,
        COUNT(DISTINCT fo.customer_key) AS active_purchasers,
        SUM(fo.gross_amount) AS gross_merchandise_value,
        SUM(fo.discount_amount) AS total_discounts_granted,
        SUM(CASE WHEN fo.order_status = 'Completed' THEN fo.net_amount ELSE 0 END) AS realized_net_revenue,
        SUM(CASE WHEN fo.order_status = 'Completed' THEN fo.cogs_amount ELSE 0 END) AS realized_cogs,
        SUM(CASE WHEN fo.order_status = 'Completed' THEN fo.gross_margin ELSE 0 END) AS realized_gross_profit,
        SUM(fo.item_count) AS total_units_ordered,
        AVG(CASE WHEN fo.order_status = 'Completed' THEN fo.net_amount END) AS average_order_value,
        AVG(CASE WHEN fo.order_status = 'Completed' THEN fo.delivery_days END) AS avg_delivery_days
    FROM fact_orders fo
    JOIN dim_date d ON fo.date_key = d.date_key
    GROUP BY d.calendar_year
),
summary_with_kpis AS (
    SELECT
        calendar_year,
        total_orders_placed,
        completed_orders,
        returned_orders,
        cancelled_orders,
        active_purchasers,
        ROUND(gross_merchandise_value, 2) AS gross_merchandise_value,
        ROUND(total_discounts_granted, 2) AS total_discounts,
        ROUND(realized_net_revenue, 2) AS net_revenue,
        ROUND(realized_cogs, 2) AS cogs,
        ROUND(realized_gross_profit, 2) AS gross_profit,
        ROUND((realized_gross_profit * 100.0) / NULLIF(realized_net_revenue, 0), 2) AS gross_margin_pct,
        ROUND(average_order_value, 2) AS aov,
        ROUND((realized_net_revenue * 1.0) / NULLIF(active_purchasers, 0), 2) AS arpu,
        ROUND((returned_orders * 100.0) / NULLIF(total_orders_placed, 0), 2) AS return_rate_pct,
        ROUND((cancelled_orders * 100.0) / NULLIF(total_orders_placed, 0), 2) AS cancellation_rate_pct,
        ROUND(avg_delivery_days, 1) AS avg_delivery_days
    FROM yearly_metrics
)
SELECT
    calendar_year,
    net_revenue,
    gross_profit,
    gross_margin_pct,
    completed_orders,
    active_purchasers,
    aov,
    arpu,
    return_rate_pct,
    ROUND(
        (net_revenue - LAG(net_revenue) OVER (ORDER BY calendar_year)) * 100.0 /
        NULLIF(LAG(net_revenue) OVER (ORDER BY calendar_year), 0),
        2
    ) AS yoy_net_revenue_growth_pct,
    ROUND(
        (completed_orders - LAG(completed_orders) OVER (ORDER BY calendar_year)) * 100.0 /
        NULLIF(LAG(completed_orders) OVER (ORDER BY calendar_year), 0),
        2
    ) AS yoy_order_volume_growth_pct
FROM summary_with_kpis
ORDER BY calendar_year;
