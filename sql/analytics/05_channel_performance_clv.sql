-- ==============================================================================
-- Query 05: Acquisition Channel Unit Economics & Customer Lifetime Value (CLV)
-- Purpose: Evaluates customer acquisition efficiency and long-term channel value.
-- Techniques: CTEs, Multi-table Joins, Ratio of Repeat Purchasers, CLV aggregation.
-- ==============================================================================

WITH customer_orders AS (
    SELECT
        c.customer_key,
        c.customer_id,
        c.acquisition_channel,
        c.acquisition_date,
        COUNT(DISTINCT fo.order_id) AS total_orders,
        SUM(CASE WHEN fo.order_status = 'Completed' THEN fo.net_amount ELSE 0 END) AS total_spend,
        SUM(CASE WHEN fo.order_status = 'Completed' THEN fo.gross_margin ELSE 0 END) AS total_margin,
        MIN(fo.order_timestamp) AS first_order_timestamp
    FROM dim_customer c
    LEFT JOIN fact_orders fo ON c.customer_key = fo.customer_key
    GROUP BY c.customer_key, c.customer_id, c.acquisition_channel, c.acquisition_date
),
first_order_values AS (
    SELECT
        co.customer_key,
        fo.net_amount AS first_order_net_amount
    FROM customer_orders co
    JOIN fact_orders fo ON co.customer_key = fo.customer_key
        AND fo.order_timestamp = co.first_order_timestamp
    WHERE fo.order_status = 'Completed'
),
channel_summary AS (
    SELECT
        co.acquisition_channel,
        COUNT(DISTINCT co.customer_key) AS acquired_customers,
        COUNT(DISTINCT CASE WHEN co.total_orders >= 1 THEN co.customer_key END) AS converting_customers,
        COUNT(DISTINCT CASE WHEN co.total_orders >= 2 THEN co.customer_key END) AS repeat_customers,
        SUM(co.total_spend) AS channel_total_revenue,
        SUM(co.total_margin) AS channel_total_gross_profit,
        AVG(fov.first_order_net_amount) AS avg_first_order_value,
        AVG(co.total_spend) AS avg_customer_lifetime_revenue,
        AVG(co.total_margin) AS avg_customer_lifetime_profit
    FROM customer_orders co
    LEFT JOIN first_order_values fov ON co.customer_key = fov.customer_key
    GROUP BY co.acquisition_channel
)
SELECT
    acquisition_channel,
    acquired_customers,
    converting_customers,
    ROUND((converting_customers * 100.0) / acquired_customers, 2) AS conversion_rate_pct,
    repeat_customers,
    ROUND((repeat_customers * 100.0) / NULLIF(converting_customers, 0), 2) AS repeat_purchase_rate_pct,
    ROUND(channel_total_revenue, 2) AS total_revenue,
    ROUND(channel_total_gross_profit, 2) AS total_gross_profit,
    ROUND(avg_first_order_value, 2) AS avg_first_order_value,
    ROUND(avg_customer_lifetime_revenue, 2) AS avg_clv_revenue,
    ROUND(avg_customer_lifetime_profit, 2) AS avg_clv_profit,
    ROUND((channel_total_gross_profit * 100.0) / NULLIF(channel_total_revenue, 0), 2) AS channel_margin_rate_pct
FROM channel_summary
ORDER BY total_revenue DESC;
