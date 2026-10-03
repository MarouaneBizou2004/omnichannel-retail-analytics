-- ==============================================================================
-- Query 02: Monthly Customer Cohort Retention Analysis
-- Purpose: Evaluates retention elasticity across acquisition vintages.
-- Techniques: Multi-level CTEs, MIN() OVER (PARTITION BY), Window Functions,
--             Integer month-index arithmetic, Retention Percentage formatting.
-- ==============================================================================

WITH customer_first_orders AS (
    -- Identify the acquisition cohort (first completed order month) for each customer
    SELECT
        fo.customer_key,
        MIN(d.year_month) AS cohort_month,
        MIN(d.calendar_year * 12 + d.month_number) AS cohort_month_index
    FROM fact_orders fo
    JOIN dim_date d ON fo.date_key = d.date_key
    WHERE fo.order_status = 'Completed'
    GROUP BY fo.customer_key
),
customer_monthly_activity AS (
    -- Identify all subsequent active completed order months for each customer
    SELECT DISTINCT
        fo.customer_key,
        d.year_month AS activity_month,
        (d.calendar_year * 12 + d.month_number) AS activity_month_index
    FROM fact_orders fo
    JOIN dim_date d ON fo.date_key = d.date_key
    WHERE fo.order_status = 'Completed'
),
cohort_progression AS (
    -- Calculate the month lag index (0 = acquisition month, 1 = month + 1, etc.)
    SELECT
        cfo.cohort_month,
        cfo.customer_key,
        (cma.activity_month_index - cfo.cohort_month_index) AS period_index
    FROM customer_first_orders cfo
    JOIN customer_monthly_activity cma ON cfo.customer_key = cma.customer_key
),
cohort_sizes AS (
    -- Base cohort size at period 0
    SELECT
        cohort_month,
        COUNT(DISTINCT customer_key) AS initial_cohort_size
    FROM customer_first_orders
    GROUP BY cohort_month
),
retention_counts AS (
    -- Retained customer count per cohort and lag period
    SELECT
        cp.cohort_month,
        cp.period_index,
        COUNT(DISTINCT cp.customer_key) AS active_customers
    FROM cohort_progression cp
    GROUP BY cp.cohort_month, cp.period_index
)
SELECT
    rc.cohort_month,
    cs.initial_cohort_size,
    rc.period_index AS month_number,
    rc.active_customers,
    ROUND((rc.active_customers * 100.0) / cs.initial_cohort_size, 2) AS retention_rate_pct
FROM retention_counts rc
JOIN cohort_sizes cs ON rc.cohort_month = cs.cohort_month
WHERE rc.period_index <= 12
ORDER BY rc.cohort_month ASC, rc.period_index ASC;
