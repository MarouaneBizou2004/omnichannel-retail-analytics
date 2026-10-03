# Enterprise Data Dictionary & Schema Specification
**Platform:** Omnichannel Retail Analytics Platform  
**Target Enterprise:** Aura Retail Group  

---

## 1. Dimensional Warehouse Tables

### 1.1 `dim_customer`
*Granularity: One record per registered customer account.*

| Column Name | Data Type | Constraint | Description | Example / Allowed Values |
| :--- | :--- | :--- | :--- | :--- |
| `customer_key` | INTEGER | PRIMARY KEY | Surrogate integer key for dimension | `101` |
| `customer_id` | VARCHAR(20) | UNIQUE, NOT NULL | Business natural key | `CUST-00142` |
| `first_name` | VARCHAR(50) | NOT NULL | Customer first name | `Sophia` |
| `last_name` | VARCHAR(50) | NOT NULL | Customer last name | `Davis` |
| `email` | VARCHAR(100) | NOT NULL | Normalized lowercase customer email address | `sophia.davis@gmail.com` |
| `age` | INTEGER | NULLABLE | Customer age in years (imputed with median) | `34` |
| `age_group` | VARCHAR(20) | NOT NULL | Demographic bracket | `18-25`, `26-35`, `36-50`, `51-65`, `65+` |
| `income_bracket` | VARCHAR(30) | NOT NULL | Household income range | `< $35k`, `$35k-$65k`, `$65k-$100k`, `Unknown` |
| `region` | VARCHAR(50) | NOT NULL | Geographic operational sales territory | `Northeast`, `Midwest`, `West`, `South`, `UK & Europe` |
| `acquisition_channel` | VARCHAR(50) | NOT NULL | First marketing attribution touchpoint | `Organic Search`, `Paid Social`, `Affiliate`, `Direct`, `Email/CRM` |
| `acquisition_date` | DATE | NOT NULL | Date customer profile was created | `2024-03-15` |
| `loyalty_tier` | VARCHAR(20) | NOT NULL | Customer loyalty status | `Bronze`, `Silver`, `Gold`, `Platinum` |

---

### 1.2 `dim_product`
*Granularity: One record per catalog Stock Keeping Unit (SKU).*

| Column Name | Data Type | Constraint | Description | Example / Allowed Values |
| :--- | :--- | :--- | :--- | :--- |
| `product_key` | INTEGER | PRIMARY KEY | Surrogate integer key | `45` |
| `product_id` | VARCHAR(20) | UNIQUE, NOT NULL | Natural SKU code | `PRD-1045` |
| `product_name` | VARCHAR(100) | NOT NULL | Merchandising catalog name | `Eco Furniture 32` |
| `category` | VARCHAR(50) | NOT NULL | Top-level merchandise division | `Home & Living`, `Apparel & Footwear`, `Consumer Electronics`, `Beauty & Wellness`, `Outdoor & Fitness` |
| `subcategory` | VARCHAR(50) | NOT NULL | Granular merchandising taxonomy | `Furniture`, `Cookware`, `Outerwear`, `Audio`, etc. |
| `unit_cost` | DECIMAL(10,2) | NOT NULL | Standard unit Cost of Goods Sold (COGS) in USD | `42.50` |
| `unit_price` | DECIMAL(10,2) | NOT NULL | Baseline retail list price in USD | `95.00` |
| `standard_margin_rate` | DECIMAL(6,4) | NOT NULL | Baseline target gross margin % `(price - cost) / price` | `0.5526` (55.3%) |
| `supplier_lead_time_days` | INTEGER | NOT NULL | Warehouse replenishment lead time in days | `5` |

---

### 1.3 `dim_date`
*Granularity: One record per calendar day (2024-01-01 to 2025-12-31).*

| Column Name | Data Type | Constraint | Description | Example / Allowed Values |
| :--- | :--- | :--- | :--- | :--- |
| `date_key` | INTEGER | PRIMARY KEY | Smart integer date key `YYYYMMDD` | `20241129` |
| `full_date` | DATE | UNIQUE, NOT NULL | ISO standard date | `2024-11-29` |
| `day_of_week` | INTEGER | NOT NULL | Day number (1 = Monday, 7 = Sunday) | `5` |
| `day_name` | VARCHAR(15) | NOT NULL | Day name string | `Friday` |
| `day_of_month` | INTEGER | NOT NULL | Day of month | `29` |
| `month_number` | INTEGER | NOT NULL | Calendar month integer (1 to 12) | `11` |
| `month_name` | VARCHAR(15) | NOT NULL | Month name string | `November` |
| `calendar_quarter` | INTEGER | NOT NULL | Calendar quarter (1 to 4) | `4` |
| `calendar_year` | INTEGER | NOT NULL | 4-digit calendar year | `2024` |
| `year_month` | VARCHAR(7) | NOT NULL | Formatted year-month string | `2024-11` |
| `is_weekend` | BOOLEAN | NOT NULL | Flag for Saturday or Sunday (0 or 1) | `0` |
| `is_holiday_season` | BOOLEAN | NOT NULL | Flag for peak Q4 period (Nov 15 - Dec 31) | `1` |

---

### 1.4 `fact_orders`
*Granularity: One record per transaction order header.*

| Column Name | Data Type | Constraint | Description | Example / Allowed Values |
| :--- | :--- | :--- | :--- | :--- |
| `order_key` | INTEGER | PRIMARY KEY | Surrogate order key | `1501` |
| `order_id` | VARCHAR(30) | UNIQUE, NOT NULL | Natural order transaction code | `ORD-2024-011245` |
| `customer_key` | INTEGER | FK -> `dim_customer` | Foreign key referencing purchasing customer | `101` |
| `date_key` | INTEGER | FK -> `dim_date` | Foreign key referencing order placement date | `20241129` |
| `channel_key` | INTEGER | FK -> `dim_channel` | Foreign key referencing sales channel | `1` |
| `order_timestamp` | TIMESTAMP | NOT NULL | Exact order placement timestamp | `2024-11-29 18:24:12` |
| `order_status` | VARCHAR(20) | NOT NULL | Order fulfillment disposition | `Completed`, `Returned`, `Cancelled` |
| `payment_method` | VARCHAR(30) | NOT NULL | Payment tender type | `Credit Card`, `PayPal`, `Apple Pay`, `Buy Now Pay Later` |
| `is_returned` | BOOLEAN | NOT NULL | Flag indicating post-fulfillment product return (0 or 1) | `0` |
| `gross_amount` | DECIMAL(10,2) | NOT NULL | Gross merchandise value before discounts | `240.00` |
| `discount_amount` | DECIMAL(10,2) | NOT NULL | Total promotional discount deducted | `36.00` |
| `net_amount` | DECIMAL(10,2) | NOT NULL | Realized net merchandise sales | `204.00` |
| `cogs_amount` | DECIMAL(10,2) | NOT NULL | Aggregated cost of goods sold | `112.50` |
| `gross_margin` | DECIMAL(10,2) | NOT NULL | Realized gross margin `(net_amount - cogs_amount)` | `91.50` |
| `item_count` | INTEGER | NOT NULL | Total units in basket | `2` |
| `shipping_cost` | DECIMAL(10,2) | NOT NULL | Shipping fee collected from customer | `0.00` |
| `delivery_days` | INTEGER | NOT NULL | Fulfillment lead time from order to delivery | `3` |

---

## 2. Machine Learning Feature & Scoring Datasets

### 2.1 `customer_features_churn` & `scored_customers_retention`
*Granularity: One record per active customer evaluated for 90-day churn.*

| Feature Name | Data Type | Source / Logic | Business Context |
| :--- | :--- | :--- | :--- |
| `recency_days` | FLOAT | `2025-10-01 - MAX(order_timestamp)` | Days since latest completed purchase |
| `frequency` | INTEGER | `COUNT(DISTINCT order_id)` | Total completed historical orders |
| `total_net_spend` | FLOAT | `SUM(net_revenue)` | Cumulative net lifetime spend up to cutoff |
| `avg_order_value` | FLOAT | `total_net_spend / frequency` | Average basket net dollar spend |
| `order_velocity_ratio` | FLOAT | `orders_30d / ((orders_90d / 3) + 0.1)` | Short-term order momentum vs 90d baseline |
| `return_rate` | FLOAT | `return_lines / total_lines` | Ratio of purchased items returned |
| `churn_90d` | INTEGER | Target label (1 if 0 orders in 90d post-cutoff; 0 otherwise) | Model objective target |
| `churn_probability` | FLOAT | Model predicted probability `P(churn = 1)` | Continuously calibrated risk metric |
| `risk_tier` | VARCHAR | Rule thresholding on `churn_probability` | `Critical Risk`, `High Risk`, `Moderate Risk`, `Low Risk (Healthy)` |
| `prescribed_action` | VARCHAR | Business decision matrix | Tailored CRM voucher, concierge outreach, or nurture |
