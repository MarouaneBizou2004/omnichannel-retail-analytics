# Executive Summary: Omnichannel Retail Analytics & Customer Intelligence
**Author:** Senior Analytics Engineer & Data Scientist  
**Organization:** Aura Retail Group  
**Date:** Q1 2026  

---

## 1. Executive Context & Problem Statement

Over the 2024–2025 operating cycle, Aura Retail Group generated **$3.72M in realized net revenue** and **$1.42M in gross profit** across 15,380 completed orders. While top-line scale remained strong, management noted an underlying retention challenge: **active purchasing customers declined 38.5% YoY (from 3,400 to 2,092)**, and customer cohort repeat purchase rates exhibited a sharp drop-off between Month 1 and Month 3.

To reverse customer attrition and protect operating margins, this project delivered an end-to-end data intelligence architecture combining a **Kimball Star Schema relational warehouse**, **in-depth exploratory business intelligence**, and a **leakage-proof machine learning churn prevention system**.

---

## 2. Key Business Insights & Analytical Findings

### 2.1 The "90-Day Churn Cliff"
- Monthly cohort tracking revealed that **64% of first-time buyers never make a second purchase within their first 12 months**.
- Customer engagement drops most precipitously between **Day 30 and Day 90** following their first order.
- **Strategic Implication:** The historical marketing strategy of sending "win-back" emails at Day 120+ is ineffective. Automated re-engagement must occur between Day 35 and Day 50 to intercept fading interest.

### 2.2 Promotional Margin Erosion & Elasticity
- Full-price items deliver an average **44.8% gross margin rate** with a low **4.2% return rate**.
- Aggressive promotional discounting (>20% to 35% during Q4 Black Friday) compressed realized gross margins down to **16.1%**, while simultaneously spiking product return rates to **11.4%**.
- **Financial Leak:** Transactions in the highest discount band (>30%) failed to generate enough basket volume to cover product cost and fulfillment, destroying unit economics.

### 2.3 RFM Customer Value Concentration
- **Champions & Loyalists** represent just **18.4% of total customers**, yet generate **51.2% of total net revenue ($1.90M)**.
- **At-Risk High-Value Customers** (previously frequent shoppers who have gone silent over 90+ days) account for **$540k in historical spend**. Preventing even 20% of their attrition represents over $100k in protected gross profit.

### 2.4 Acquisition Channel Economics
- **Organic Search & Direct** channels yielded the highest 12-month Customer Lifetime Value ($865 and $842 average spend per customer) with a 38.2% repeat order rate.
- **Paid Social** acquired the highest volume of entry-level customers, but suffered the lowest 12-month retention (21.4%), indicating high acquisition CAC with low long-term customer payback.

---

## 3. Predictive Machine Learning Retention Engine

### 3.1 Model Formulation & Leakage-Proof Design
To avoid target leakage (a common failure mode in portfolio projects), features were computed strictly up to an **October 1, 2025 observation cutoff**. The objective was predicting customer churn during the subsequent **90-day window (Q4 2025)**.

### 3.2 Benchmark & Performance Results
| Model Candidate | Cross-Validation ROC-AUC | Holdout PR-AUC | Holdout Recall | Brier Score | Decision Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Stratified Dummy Baseline** | 0.5052 | 0.8837 | 0.8800 | 0.2104 | Baseline floor |
| **Balanced Logistic Regression** | 0.9487 | 0.9929 | 0.8650 | 0.0520 | Benchmark linear model |
| **Random Forest Classifier** | 0.9419 | 0.9918 | 0.8920 | 0.0482 | Non-linear ensemble |
| **Tuned HistGradientBoosting** | **0.9491** | **0.9930** | **0.8791** | **0.0391** | **Champion Model** |

### 3.3 Financial Decision Threshold Optimization
Standard machine learning models use an arbitrary classification threshold ($t = 0.50$). In commercial retention marketing, the cost of an outreach voucher ($15.00) is far lower than the lost gross margin of an attrited customer ($120.00).

By modeling the financial profit curve across thresholds $t \in [0.05, 0.95]$:
- Optimal Decision Threshold: **$t^* = 0.13$**
- **Test Cohort Net Profit:** **$20,004**
- **Annual Enterprise Protected Gross Margin:** **$100,020** (a **+$22,400 lift** over the default 0.50 threshold).

---

## 4. Strategic Executive Recommendations

1. **Deploy Automated Day-45 CRM Interventions:**
   - Integrate the batch scoring pipeline with the CRM system (Braze / Klaviyo / HubSpot).
   - Automatically trigger tailored re-engagement incentives to customers exceeding $p(\text{churn}) \ge 0.13$ before they cross the 90-day inactivity mark.

2. **Cap Holiday Promo Discounts at 20%:**
   - Eliminate clearance codes >30%.
   - Shift marketing budgets from deep price cuts to value-added perks (e.g., Free Express Shipping for Loyalty Members, bundled gift accessories).

3. **Reallocate Paid Marketing Budget to Retention:**
   - Shift 15% of Paid Social acquisition spend into VIP retention perks and Mobile App onboarding incentives, which demonstrate 1.8x higher lifetime ROI.

---

## 5. Technology Stack & Deliverables
- **Data Engineering:** Python (`pandas`, `numpy`, `pyarrow`), Great Expectations style validation checks.
- **Relational Warehousing:** SQLite & ANSI SQL Kimball Star Schema (`dim_customer`, `dim_product`, `dim_date`, `dim_channel`, `fact_orders`, `fact_order_items`).
- **Machine Learning:** `scikit-learn` Pipeline with ColumnTransformers, HistGradientBoosting, Hyperparameter GridSearch, Permutation Importance, and ROI Threshold curves.
- **Business Intelligence:** Interactive Streamlit Application and 4-page Power BI Architecture Specification with 25+ DAX Measures.
- **Quality Assurance:** 13 automated unit tests with 100% pass rate (`pytest`).
