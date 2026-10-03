# Data Cleaning & Quality Audit Report

## Ingestion & Quality Summary

| Entity | Raw Rows | Cleaned Rows | Deduplicated Rows | Key Actions |
| :--- | :--- | :--- | :--- | :--- |
| **Products** | 120 | 120 | 0 | Title-cased categories, imputed supplier lead times |
| **Customers** | 4536 | 4500 | 36 | Imputed missing ages (189), normalized emails & regions |
| **Orders / Lines** | 25800 | 25672 | 128 | Standardized channels, timestamps, verified financial metrics |

### Order Status Breakdown

- **Completed Lines:** 23,328
- **Returned Lines:** 1,818
- **Cancelled Lines:** 526

### Referential Integrity Verification

- All `customer_id` keys in orders map 100% to customer master records.
- All `product_id` keys in orders map 100% to product catalog records.
- No negative net revenues or invalid discount ranges detected.
