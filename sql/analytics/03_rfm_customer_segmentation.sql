-- ==============================================================================
-- Query 03: RFM (Recency, Frequency, Monetary) Customer Segmentation
-- Purpose: Quantifies customer behavioral value and identifies high-value retention targets.
-- Techniques: CTEs, Window NTILE(5) scoring, JULIANDAY date math, CASE segmentation logic.
-- ==============================================================================

WITH customer_aggregates AS (
    SELECT
        c.customer_key,
        c.customer_id,
        c.region,
        c.loyalty_tier,
        -- Reference snapshot date: 2025-12-31
        ROUND(JULIANDAY('2025-12-31') - JULIANDAY(MAX(fo.order_timestamp))) AS recency_days,
        COUNT(DISTINCT fo.order_id) AS frequency,
        SUM(fo.net_amount) AS monetary_value,
        SUM(fo.gross_margin) AS total_gross_margin
    FROM dim_customer c
    JOIN fact_orders fo ON c.customer_key = fo.customer_key
    WHERE fo.order_status = 'Completed'
    GROUP BY c.customer_key, c.customer_id, c.region, c.loyalty_tier
),
rfm_scores AS (
    SELECT
        customer_key,
        customer_id,
        region,
        loyalty_tier,
        recency_days,
        frequency,
        monetary_value,
        total_gross_margin,
        -- Score 5 is best (most recent / highest frequency / highest spend)
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary_value ASC) AS m_score
    FROM customer_aggregates
),
segmented_customers AS (
    SELECT
        customer_key,
        customer_id,
        region,
        loyalty_tier,
        recency_days,
        frequency,
        monetary_value,
        total_gross_margin,
        r_score,
        f_score,
        m_score,
        (CAST(r_score AS VARCHAR) || CAST(f_score AS VARCHAR) || CAST(m_score AS VARCHAR)) AS rfm_combined,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2 THEN 'Recent Customers'
            WHEN r_score >= 3 AND f_score >= 2 AND m_score >= 2 THEN 'Potential Loyalists'
            WHEN r_score = 3 AND f_score <= 2 THEN 'Promising'
            WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN 'At Risk (High Value)'
            WHEN r_score <= 2 AND f_score >= 2 THEN 'Customers Needing Attention'
            WHEN r_score <= 2 AND f_score <= 2 AND m_score <= 2 THEN 'Hibernating'
            ELSE 'Lost / Inactive'
        END AS customer_segment
    FROM rfm_scores
)
-- Business Summary by Customer Segment
SELECT
    customer_segment,
    COUNT(customer_key) AS customer_count,
    ROUND(COUNT(customer_key) * 100.0 / (SELECT COUNT(*) FROM segmented_customers), 2) AS customer_share_pct,
    ROUND(SUM(monetary_value), 2) AS total_net_revenue,
    ROUND(SUM(monetary_value) * 100.0 / (SELECT SUM(monetary_value) FROM segmented_customers), 2) AS revenue_share_pct,
    ROUND(SUM(total_gross_margin), 2) AS total_gross_margin,
    ROUND(AVG(recency_days), 1) AS avg_recency_days,
    ROUND(AVG(frequency), 2) AS avg_orders_per_customer,
    ROUND(AVG(monetary_value), 2) AS avg_monetary_spend,
    ROUND(SUM(total_gross_margin) * 100.0 / NULLIF(SUM(monetary_value), 0), 2) AS segment_margin_rate_pct
FROM segmented_customers
GROUP BY customer_segment
ORDER BY total_net_revenue DESC;
