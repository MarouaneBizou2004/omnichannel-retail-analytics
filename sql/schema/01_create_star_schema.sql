-- ==============================================================================
-- Dimensional Data Warehouse Schema (Star Schema)
-- Target: SQLite & ANSI SQL Compatible
-- Project: Omnichannel Retail Analytics Platform (Aura Retail Group)
-- ==============================================================================

-- Drop tables in reverse foreign-key dependency order
DROP TABLE IF EXISTS fact_order_items;
DROP TABLE IF EXISTS fact_orders;
DROP TABLE IF EXISTS dim_channel;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_customer;

-- ==============================================================================
-- DIMENSION: dim_customer
-- ==============================================================================
CREATE TABLE dim_customer (
    customer_key INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id VARCHAR(20) NOT NULL UNIQUE,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    age INTEGER,
    age_group VARCHAR(20),
    income_bracket VARCHAR(30),
    region VARCHAR(50) NOT NULL,
    acquisition_channel VARCHAR(50) NOT NULL,
    acquisition_date DATE NOT NULL,
    loyalty_tier VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dim_customer_id ON dim_customer(customer_id);
CREATE INDEX idx_dim_customer_region ON dim_customer(region);
CREATE INDEX idx_dim_customer_loyalty ON dim_customer(loyalty_tier);

-- ==============================================================================
-- DIMENSION: dim_product
-- ==============================================================================
CREATE TABLE dim_product (
    product_key INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id VARCHAR(20) NOT NULL UNIQUE,
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50) NOT NULL,
    unit_cost DECIMAL(10, 2) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    standard_margin_rate DECIMAL(6, 4) NOT NULL,
    supplier_lead_time_days INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dim_product_id ON dim_product(product_id);
CREATE INDEX idx_dim_product_category ON dim_product(category, subcategory);

-- ==============================================================================
-- DIMENSION: dim_channel
-- ==============================================================================
CREATE TABLE dim_channel (
    channel_key INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_name VARCHAR(30) NOT NULL UNIQUE,
    platform_type VARCHAR(30) NOT NULL
);

-- ==============================================================================
-- DIMENSION: dim_date
-- ==============================================================================
CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,           -- Formatted as YYYYMMDD (e.g. 20240115)
    full_date DATE NOT NULL UNIQUE,
    day_of_week INTEGER NOT NULL,           -- 1 = Monday, 7 = Sunday
    day_name VARCHAR(15) NOT NULL,
    day_of_month INTEGER NOT NULL,
    month_number INTEGER NOT NULL,
    month_name VARCHAR(15) NOT NULL,
    calendar_quarter INTEGER NOT NULL,
    calendar_year INTEGER NOT NULL,
    year_month VARCHAR(7) NOT NULL,         -- Format YYYY-MM
    is_weekend BOOLEAN NOT NULL,
    is_holiday_season BOOLEAN NOT NULL      -- Q4 peak indicator (Nov 15 - Dec 31)
);

CREATE INDEX idx_dim_date_full ON dim_date(full_date);
CREATE INDEX idx_dim_date_ym ON dim_date(year_month);

-- ==============================================================================
-- FACT: fact_orders (Order-Grain Fact Table)
-- ==============================================================================
CREATE TABLE fact_orders (
    order_key INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id VARCHAR(30) NOT NULL UNIQUE,
    customer_key INTEGER NOT NULL,
    date_key INTEGER NOT NULL,
    channel_key INTEGER NOT NULL,
    order_timestamp TIMESTAMP NOT NULL,
    order_status VARCHAR(20) NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    is_returned BOOLEAN NOT NULL DEFAULT 0,
    gross_amount DECIMAL(10, 2) NOT NULL,
    discount_amount DECIMAL(10, 2) NOT NULL,
    net_amount DECIMAL(10, 2) NOT NULL,
    cogs_amount DECIMAL(10, 2) NOT NULL,
    gross_margin DECIMAL(10, 2) NOT NULL,
    item_count INTEGER NOT NULL,
    shipping_cost DECIMAL(10, 2) NOT NULL,
    delivery_days INTEGER NOT NULL,
    FOREIGN KEY (customer_key) REFERENCES dim_customer(customer_key),
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (channel_key) REFERENCES dim_channel(channel_key)
);

CREATE INDEX idx_fact_orders_cust ON fact_orders(customer_key);
CREATE INDEX idx_fact_orders_date ON fact_orders(date_key);
CREATE INDEX idx_fact_orders_channel ON fact_orders(channel_key);
CREATE INDEX idx_fact_orders_status ON fact_orders(order_status);

-- ==============================================================================
-- FACT: fact_order_items (Line-Item Grain Fact Table)
-- ==============================================================================
CREATE TABLE fact_order_items (
    item_key INTEGER PRIMARY KEY AUTOINCREMENT,
    order_key INTEGER NOT NULL,
    order_id VARCHAR(30) NOT NULL,
    customer_key INTEGER NOT NULL,
    product_key INTEGER NOT NULL,
    date_key INTEGER NOT NULL,
    channel_key INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    unit_cost DECIMAL(10, 2) NOT NULL,
    discount_percent DECIMAL(5, 4) NOT NULL,
    gross_revenue DECIMAL(10, 2) NOT NULL,
    discount_amount DECIMAL(10, 2) NOT NULL,
    net_revenue DECIMAL(10, 2) NOT NULL,
    cogs DECIMAL(10, 2) NOT NULL,
    gross_profit DECIMAL(10, 2) NOT NULL,
    order_status VARCHAR(20) NOT NULL,
    is_returned BOOLEAN NOT NULL DEFAULT 0,
    FOREIGN KEY (order_key) REFERENCES fact_orders(order_key),
    FOREIGN KEY (customer_key) REFERENCES dim_customer(customer_key),
    FOREIGN KEY (product_key) REFERENCES dim_product(product_key),
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
    FOREIGN KEY (channel_key) REFERENCES dim_channel(channel_key)
);

CREATE INDEX idx_fact_items_product ON fact_order_items(product_key);
CREATE INDEX idx_fact_items_order ON fact_order_items(order_key);
CREATE INDEX idx_fact_items_cust ON fact_order_items(customer_key);
CREATE INDEX idx_fact_items_date ON fact_order_items(date_key);
