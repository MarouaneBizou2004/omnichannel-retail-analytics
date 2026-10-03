# Enterprise Power BI Dashboard Specification & DAX Architecture
**Project:** Omnichannel Retail Analytics & Customer Intelligence Platform  
**Target Organization:** Aura Retail Group  
**Audience:** Chief Commercial Officer (CCO), VP of E-Commerce, Head of Merchandising, Retention Marketing Leads  

---

## 1. Relational Data Model (Kimball Star Schema)

The Power BI data model is structured as a strict Kimball Star Schema with 1-to-many relationships and single-direction cross-filtering to guarantee optimal VertiPaq engine compression and avoid ambiguous relationship paths.

```
       +-------------------+       +-------------------+
       |    dim_customer   |       |    dim_channel    |
       +-------------------+       +-------------------+
       | PK customer_key   |       | PK channel_key    |
       +---------+---------+       +---------+---------+
                 |                           |
                 | 1                         | 1
                 |                           |
                 | *                         | *
       +---------+---------------------------+---------+
       |                  fact_orders                  |
       +-----------------------------------------------+
       | PK order_key                                  |
       | FK customer_key                               |
       | FK date_key                                   |
       | FK channel_key                                |
       | gross_amount, net_amount, gross_margin, etc.  |
       +---------+-------------------+-----------------+
                 |                   |
                 | 1                 | *
                 |                   |
                 | *                 | 1
       +---------+---------+       +-+-----------------+
       | fact_order_items  |       |     dim_date      |
       +-------------------+       +-------------------+
       | PK item_key       |       | PK date_key       |
       | FK order_key      |       +-------------------+
       | FK product_key    |                 | 1
       +---------+---------+                 |
                 | *                         |
                 |                           |
                 | 1                         | *
       +---------+---------+                 |
       |    dim_product    |-----------------+
       +-------------------+
       | PK product_key    |
       +-------------------+
```

### Relationship Topology & Cardinality
| From Table | From Column | To Table | To Column | Cardinality | Cross-Filter Direction | Active |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `fact_orders` | `customer_key` | `dim_customer` | `customer_key` | Many-to-One (*:1) | Single (`dim_customer` filters `fact_orders`) | Yes |
| `fact_orders` | `channel_key` | `dim_channel` | `channel_key` | Many-to-One (*:1) | Single (`dim_channel` filters `fact_orders`) | Yes |
| `fact_orders` | `date_key` | `dim_date` | `date_key` | Many-to-One (*:1) | Single (`dim_date` filters `fact_orders`) | Yes |
| `fact_order_items` | `order_key` | `fact_orders` | `order_key` | Many-to-One (*:1) | Single (`fact_orders` filters `fact_order_items`) | Yes |
| `fact_order_items` | `product_key` | `dim_product` | `product_key` | Many-to-One (*:1) | Single (`dim_product` filters `fact_order_items`) | Yes |
| `fact_order_items` | `date_key` | `dim_date` | `date_key` | Many-to-One (*:1) | Inactive (Role-Playing Date) | No |

---

## 2. Production DAX Measure Library

All measures are organized into dedicated display folders within an empty calculated table `_DAX_Measures`.

### 2.1 Core Revenue & Profitability
```dax
-- Total Gross Revenue
Total Gross Revenue = 
SUM(fact_orders[gross_amount])

-- Total Discounts Granted
Total Discounts = 
SUM(fact_orders[discount_amount])

-- Net Realized Revenue (Completed Orders only)
Net Revenue = 
CALCULATE(
    SUM(fact_orders[net_amount]),
    fact_orders[order_status] = "Completed"
)

-- Cost of Goods Sold (COGS)
Total COGS = 
CALCULATE(
    SUM(fact_orders[cogs_amount]),
    fact_orders[order_status] = "Completed"
)

-- Gross Profit
Gross Profit = 
[Net Revenue] - [Total COGS]

-- Realized Gross Profit Margin %
Gross Margin % = 
DIVIDE([Gross Profit], [Net Revenue], 0)

-- Overall Discount Rate %
Effective Discount % = 
DIVIDE([Total Discounts], [Total Gross Revenue], 0)
```

### 2.2 Order & Operational Health
```dax
-- Total Placed Orders
Total Orders = 
DISTINCTCOUNT(fact_orders[order_id])

-- Completed Orders
Completed Orders = 
CALCULATE(
    DISTINCTCOUNT(fact_orders[order_id]),
    fact_orders[order_status] = "Completed"
)

-- Returned Orders
Returned Orders = 
CALCULATE(
    DISTINCTCOUNT(fact_orders[order_id]),
    fact_orders[is_returned] = 1
)

-- Order Return Rate %
Return Rate % = 
DIVIDE([Returned Orders], [Total Orders], 0)

-- Average Order Value (AOV)
Average Order Value = 
DIVIDE([Net Revenue], [Completed Orders], 0)

-- Average Fulfillment Days
Avg Delivery Days = 
AVERAGEX(
    FILTER(fact_orders, fact_orders[order_status] = "Completed"),
    fact_orders[delivery_days]
)
```

### 2.3 Customer Lifetime Value & Behavioral Dynamics
```dax
-- Total Active Customers
Active Customers = 
CALCULATE(
    DISTINCTCOUNT(fact_orders[customer_key]),
    fact_orders[order_status] = "Completed"
)

-- Average Revenue per User (ARPU)
ARPU = 
DIVIDE([Net Revenue], [Active Customers], 0)

-- Repeat Customers (Customers with 2+ completed orders in selection)
Repeat Customers = 
COUNTROWS(
    FILTER(
        VALUES(dim_customer[customer_key]),
        CALCULATE(DISTINCTCOUNT(fact_orders[order_id]), fact_orders[order_status] = "Completed") >= 2
    )
)

-- Repeat Customer Rate %
Repeat Customer Rate % = 
DIVIDE([Repeat Customers], [Active Customers], 0)

-- Customer Lifetime Value (CLV - Average Historical Spend)
CLV Historical = 
AVERAGEX(
    VALUES(dim_customer[customer_key]),
    CALCULATE([Net Revenue])
)
```

### 2.4 Time Intelligence (YoY, MoM, Rolling Windows)
```dax
-- Prior Year Net Revenue
Net Revenue PY = 
CALCULATE(
    [Net Revenue],
    SAMEPERIODLASTYEAR(dim_date[full_date])
)

-- Year-over-Year (YoY) Net Revenue Growth %
YoY Revenue Growth % = 
DIVIDE([Net Revenue] - [Net Revenue PY], [Net Revenue PY], 0)

-- Month-over-Month (MoM) Net Revenue Growth %
MoM Revenue Growth % = 
VAR CurrentMonthRev = [Net Revenue]
VAR PrevMonthRev = 
    CALCULATE(
        [Net Revenue],
        PREVIOUSMONTH(dim_date[full_date])
    )
RETURN
    DIVIDE(CurrentMonthRev - PrevMonthRev, PrevMonthRev, 0)

-- Rolling 90-Day Net Revenue
Rolling 90D Revenue = 
CALCULATE(
    [Net Revenue],
    DATESINPERIOD(dim_date[full_date], MAX(dim_date[full_date]), -90, DAY)
)
```

### 2.5 Machine Learning Retention & Churn Measures
```dax
-- Total Customers Evaluated by Churn Pipeline
ML Customers Evaluated = 
COUNTROWS(scored_customers_retention)

-- Predicted Critical & High Risk Customers
At-Risk Customers Count = 
CALCULATE(
    COUNTROWS(scored_customers_retention),
    scored_customers_retention[risk_tier] IN {"Critical Risk", "High Risk"}
)

-- At-Risk Customer Ratio %
At-Risk Customer Ratio % = 
DIVIDE([At-Risk Customers Count], [ML Customers Evaluated], 0)

-- Potential Recoverable Margin (Net ROI of Targeted Intervention)
Expected Recoverable Margin = 
VAR AtRiskCusts = [At-Risk Customers Count]
VAR SuccessRate = 0.35
VAR MarginPerCust = 120.0
VAR CostPerOutreach = 15.0
RETURN
    (AtRiskCusts * SuccessRate * MarginPerCust) - (AtRiskCusts * CostPerOutreach)
```

---

## 3. Four-Page Executive Dashboard Layout Specification

### Page 1: Executive C-Suite Overview & Financial Pulse
* **Header / Filter Bar:**
  - Date Range Slicer (Relative Date / Calendar Slider)
  - Sales Channel Multi-Select (`Web`, `Mobile App`, `In-Store`)
  - Loyalty Tier Slicer (`Bronze`, `Silver`, `Gold`, `Platinum`)
  - Geographic Region Slicer (`Northeast`, `Midwest`, `West`, `South`, `UK & Europe`)
* **Top Metric Cards (KPI Ribbons):**
  - **Card 1:** `[Net Revenue]` + Target vs Prior Year (`[YoY Revenue Growth %]`)
  - **Card 2:** `[Gross Profit]` + `[Gross Margin %]`
  - **Card 3:** `[Completed Orders]` + `[AOV]`
  - **Card 4:** `[Active Customers]` + `[Repeat Customer Rate %]`
  - **Card 5:** `[Return Rate %]` (Conditional formatting: Green < 6%, Red > 9%)
* **Visual 1 (Area & Clustered Column Chart):**
  - X-Axis: `dim_date[year_month]`
  - Column 1: `[Net Revenue]`
  - Column 2: `[Gross Profit]`
  - Line: `[Gross Margin %]`
* **Visual 2 (Donut Chart):**
  - Legend: `dim_channel[channel_name]`
  - Values: `[Net Revenue]`
* **Visual 3 (Decomposition Tree):**
  - Root: `[Net Revenue]`
  - Explain By: `dim_product[category]` -> `dim_customer[region]` -> `dim_channel[channel_name]`

---

### Page 2: Customer Retention, Cohorts & Churn Risk
* **Visual 1 (Matrix - Cohort Retention Heatmap):**
  - Rows: `Acquisition Cohort (Year-Month)`
  - Columns: `Cohort Period Index (Month 0 to Month 12)`
  - Values: `[Cohort Retention Rate %]`
  - Conditional Formatting: Background color gradient from light yellow (0%) to deep navy blue (100%).
* **Visual 2 (Gauge / Donut):**
  - Value: `[At-Risk Customer Ratio %]`
  - Callout: `[At-Risk Customers Count]`
* **Visual 3 (Clustered Bar Chart):**
  - Y-Axis: `scored_customers_retention[prescribed_action]`
  - X-Axis: `Count of Customers`, Tooltip: `Total At-Risk Revenue ($)`
* **Visual 4 (Scatter Plot - Retention Opportunity):**
  - X-Axis: `recency_days`
  - Y-Axis: `churn_probability`
  - Bubble Size: `total_net_spend`
  - Color: `risk_tier`

---

### Page 3: RFM Customer Segmentation & Campaign Activation
* **Visual 1 (Treemap):**
  - Group: `customer_segment` (`Champions`, `Loyal Customers`, `At Risk`, `Hibernating`, etc.)
  - Size: `[Net Revenue]`
  - Color Intensity: `[Average Order Value]`
* **Visual 2 (Clustered Column Chart):**
  - X-Axis: `customer_segment`
  - Metric 1: `% of Customer Base`
  - Metric 2: `% of Total Revenue`
* **Visual 3 (Interactive Data Table / Drill-Through List):**
  - Columns: `customer_id`, `customer_name`, `email`, `loyalty_tier`, `recency_days`, `frequency`, `monetary_value`, `risk_tier`, `prescribed_action`
  - Actions: Export to CSV button for direct upload into HubSpot / Salesforce Marketing Cloud.

---

### Page 4: Merchandising & Margin Optimization Deep Dive
* **Visual 1 (Pareto Chart - Combo):**
  - X-Axis: `dim_product[product_name]` (Sorted by Net Revenue descending)
  - Bar: `[Net Revenue]`
  - Line: `[Cumulative Revenue Share %]` with 80% benchmark reference line.
* **Visual 2 (Scatter Matrix - Profitability Elasticity):**
  - X-Axis: `[Effective Discount %]`
  - Y-Axis: `[Gross Margin %]`
  - Size: `[Total Orders]`
  - Color: `dim_product[category]`
* **Visual 3 (Table - Margin Leakage Alert):**
  - Columns: `product_id`, `product_name`, `category`, `Standard Margin Rate %`, `Realized Margin %`, `Margin Erosion (pts)`, `Return Rate %`
  - Highlights SKUs with > 500 basis points of discount erosion.

---

## 4. Implementation Checklist for BI Engineers
1. Ingest clean parquet files (`dim_customers.parquet`, `dim_products.parquet`, `fact_orders.parquet`, `scored_customers_retention.parquet`) using Power BI native Parquet connector or DirectQuery on SQLite/PostgreSQL warehouse.
2. Verify all data types (Surrogate keys as Whole Number, Dates as Date, Revenue as Decimal Number).
3. Paste the DAX Measures from Section 2 into `_DAX_Measures`.
4. Configure Drill-Through filters from Page 1 into Page 3 and Page 4 on `customer_id` and `product_id`.
5. Set up scheduled dataset refresh (daily at 02:00 AM UTC).
