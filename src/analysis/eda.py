"""
Exploratory Data Analysis & Business Intelligence Visualizer
Generates publication-quality charts answering specific strategic business questions:
1. Revenue & Gross Profit Trajectory (Seasonality & Growth)
2. Monthly Cohort Retention Heatmap (The 90-Day Churn Cliff)
3. RFM Customer Value Matrix (Concentration of Enterprise Value)
4. Product Category Profitability & Pareto Distribution
5. Promotional Discount Elasticity vs Margin Degradation
6. Acquisition Channel Economics & Long-Term Customer Value
"""

import sys
from pathlib import Path
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    PROCESSED_DATA_DIR,
    FIGURES_DIR,
    REPORTS_DIR
)
from src.utils.database import WarehouseManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("EDAEngine")

# Apply clean corporate aesthetic
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.labelweight": "semibold",
    "figure.titlesize": 15,
    "figure.titleweight": "bold",
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.dpi": 300
})

class EDAViewer:
    def __init__(self):
        self.manager = WarehouseManager()
        self.figures_dir = FIGURES_DIR
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        
    def plot_monthly_revenue_margin_trend(self) -> None:
        """
        Business Question:
        What is our monthly revenue trajectory, and how severely does promotional
        seasonality in Q4 impact gross margin %?
        """
        logger.info("Generating Monthly Revenue & Margin Trend figure...")
        query = """
        SELECT
            d.year_month,
            SUM(CASE WHEN fo.order_status = 'Completed' THEN fo.net_amount ELSE 0 END) AS net_revenue,
            SUM(CASE WHEN fo.order_status = 'Completed' THEN fo.gross_margin ELSE 0 END) AS gross_profit,
            ROUND(
                SUM(CASE WHEN fo.order_status = 'Completed' THEN fo.gross_margin ELSE 0 END) * 100.0 /
                NULLIF(SUM(CASE WHEN fo.order_status = 'Completed' THEN fo.net_amount ELSE 0 END), 0),
                2
            ) AS gross_margin_pct
        FROM fact_orders fo
        JOIN dim_date d ON fo.date_key = d.date_key
        GROUP BY d.year_month
        ORDER BY d.year_month ASC;
        """
        df = self.manager.run_query(query)
        
        fig, ax1 = plt.subplots(figsize=(14, 6))
        
        x = np.arange(len(df))
        width = 0.4
        
        # Bars for Revenue and Profit
        rects1 = ax1.bar(x - width/2, df["net_revenue"] / 1000, width, label="Net Revenue ($k)", color="#1E3A8A", alpha=0.9)
        rects2 = ax1.bar(x + width/2, df["gross_profit"] / 1000, width, label="Gross Profit ($k)", color="#0D9488", alpha=0.9)
        
        ax1.set_xlabel("Year-Month", fontweight="bold")
        ax1.set_ylabel("USD ($ in Thousands)", fontweight="bold")
        ax1.set_xticks(x)
        ax1.set_xticklabels(df["year_month"], rotation=45, ha="right")
        ax1.legend(loc="upper left")
        ax1.set_ylim(0, max(df["net_revenue"] / 1000) * 1.25)
        
        # Line for Margin % on twin axis
        ax2 = ax1.twinx()
        ax2.plot(x, df["gross_margin_pct"], color="#E11D48", marker="o", linewidth=2.5, label="Gross Margin %")
        ax2.set_ylabel("Gross Margin Rate (%)", color="#E11D48", fontweight="bold")
        ax2.tick_params(axis="y", labelcolor="#E11D48")
        ax2.set_ylim(25, 50)
        ax2.grid(False) # avoid visual clutter
        ax2.legend(loc="upper right")
        
        # Highlight Q4 Peaks
        q4_2024 = df[df["year_month"] == "2024-11"].index[0]
        q4_2025 = df[df["year_month"] == "2025-11"].index[0]
        ax1.annotate("Holiday / Black Friday Spike\n(High GMV, Promo Compression)",
                     xy=(q4_2024, df.loc[q4_2024, "net_revenue"] / 1000),
                     xytext=(q4_2024 - 1.5, (df.loc[q4_2024, "net_revenue"] / 1000) + 40),
                     arrowprops=dict(facecolor="#1E3A8A", shrink=0.08, width=1.5, headwidth=6),
                     fontsize=9, fontweight="bold", backgroundcolor="#F8FAFC")
        
        plt.title("Monthly Realized Net Revenue, Gross Profit, and Gross Margin % (2024 - 2025)", pad=15)
        fig.tight_layout()
        out_path = self.figures_dir / "01_monthly_revenue_margin_trend.png"
        plt.savefig(out_path)
        plt.close()
        logger.info(f"Saved: {out_path}")

    def plot_cohort_retention_heatmap(self) -> None:
        """
        Business Question:
        How quickly do customer cohorts decay, and when is the critical 'drop-off cliff'
        where retention marketing must intervene?
        """
        logger.info("Generating Cohort Retention Heatmap figure...")
        query = """
        WITH customer_first_orders AS (
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
            SELECT DISTINCT
                fo.customer_key,
                (d.calendar_year * 12 + d.month_number) AS activity_month_index
            FROM fact_orders fo
            JOIN dim_date d ON fo.date_key = d.date_key
            WHERE fo.order_status = 'Completed'
        ),
        cohort_progression AS (
            SELECT
                cfo.cohort_month,
                cfo.customer_key,
                (cma.activity_month_index - cfo.cohort_month_index) AS period_index
            FROM customer_first_orders cfo
            JOIN customer_monthly_activity cma ON cfo.customer_key = cma.customer_key
        ),
        cohort_sizes AS (
            SELECT cohort_month, COUNT(DISTINCT customer_key) AS initial_size
            FROM customer_first_orders
            GROUP BY cohort_month
        ),
        retention_matrix AS (
            SELECT
                cp.cohort_month,
                cs.initial_size,
                cp.period_index,
                COUNT(DISTINCT cp.customer_key) AS active_custs,
                ROUND(COUNT(DISTINCT cp.customer_key) * 100.0 / cs.initial_size, 1) AS retention_rate
            FROM cohort_progression cp
            JOIN cohort_sizes cs ON cp.cohort_month = cs.cohort_month
            WHERE cp.period_index <= 12
            GROUP BY cp.cohort_month, cs.initial_size, cp.period_index
        )
        SELECT cohort_month, initial_size, period_index, retention_rate
        FROM retention_matrix
        WHERE cohort_month <= '2025-06'
        ORDER BY cohort_month ASC, period_index ASC;
        """
        df = self.manager.run_query(query)
        
        # Pivot table
        cohort_pivot = df.pivot(index="cohort_month", columns="period_index", values="retention_rate")
        
        # Add initial cohort size to label
        size_map = df.drop_duplicates("cohort_month").set_index("cohort_month")["initial_size"].to_dict()
        new_index = [f"{idx} (n={size_map.get(idx, 0)})" for idx in cohort_pivot.index]
        cohort_pivot.index = new_index
        
        plt.figure(figsize=(13, 8))
        sns.heatmap(
            cohort_pivot,
            annot=True,
            fmt=".1f",
            cmap="YlGnBu",
            vmin=0,
            vmax=100,
            cbar_kws={"label": "Retention Rate (%)"},
            linewidths=0.5,
            linecolor="white"
        )
        plt.title("Monthly Customer Cohort Retention Rate (%) — Month 0 to Month 12", pad=15)
        plt.xlabel("Months Since Acquisition (Cohort Index)", fontweight="bold")
        plt.ylabel("Acquisition Cohort (Vintage)", fontweight="bold")
        plt.tight_layout()
        out_path = self.figures_dir / "02_cohort_retention_heatmap.png"
        plt.savefig(out_path)
        plt.close()
        logger.info(f"Saved: {out_path}")

    def plot_rfm_customer_segments(self) -> None:
        """
        Business Question:
        How heavily concentrated is revenue among Champions vs At-Risk segments,
        and what is the revenue upside of activating high-risk dormant accounts?
        """
        logger.info("Generating RFM Customer Segments figure...")
        query_path = Path(__file__).resolve().parent.parent.parent / "sql" / "analytics" / "03_rfm_customer_segmentation.sql"
        df = self.manager.run_query_file(query_path)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # 1. Customer Count vs Revenue Share Comparison
        segments = df["customer_segment"].tolist()
        y = np.arange(len(segments))
        height = 0.35
        
        ax1.barh(y - height/2, df["customer_share_pct"], height, label="% of Customers", color="#94A3B8")
        ax1.barh(y + height/2, df["revenue_share_pct"], height, label="% of Net Revenue", color="#0284C7")
        ax1.set_yticks(y)
        ax1.set_yticklabels(segments, fontweight="medium")
        ax1.invert_yaxis()
        ax1.set_xlabel("Percentage (%)", fontweight="bold")
        ax1.set_title("Customer Base Share vs Revenue Generation Share", pad=10)
        ax1.legend()
        
        # 2. Average Spend per Customer by Segment
        colors = ["#10B981" if "Champion" in s or "Loyal" in s else ("#EF4444" if "Risk" in s or "Lost" in s else "#3B82F6") for s in segments]
        ax2.barh(y, df["avg_monetary_spend"], height=0.6, color=colors, alpha=0.85)
        ax2.set_yticks(y)
        ax2.set_yticklabels([])
        ax2.invert_yaxis()
        ax2.set_xlabel("Average Spend per Customer ($)", fontweight="bold")
        ax2.set_title("Monetary Value per Customer by Segment", pad=10)
        
        for i, v in enumerate(df["avg_monetary_spend"]):
            ax2.text(v + 15, i, f"${v:,.0f}", va="center", fontweight="bold", fontsize=9)
            
        plt.suptitle("RFM Behavioral Customer Segmentation Analysis", y=1.02)
        fig.tight_layout()
        out_path = self.figures_dir / "03_rfm_customer_segments.png"
        plt.savefig(out_path)
        plt.close()
        logger.info(f"Saved: {out_path}")

    def plot_category_pareto_margin_curve(self) -> None:
        """
        Business Question:
        Which product categories and SKUs drive the 80/20 Pareto revenue distribution,
        and are our top-selling SKUs delivering healthy gross margins?
        """
        logger.info("Generating Product Category Pareto figure...")
        query = """
        SELECT
            p.product_id,
            p.category,
            SUM(foi.net_revenue) AS sku_net_revenue,
            SUM(foi.gross_profit) AS sku_gross_profit,
            ROUND(SUM(foi.gross_profit) * 100.0 / NULLIF(SUM(foi.net_revenue), 0), 2) AS sku_margin_pct
        FROM dim_product p
        JOIN fact_order_items foi ON p.product_key = foi.product_key
        WHERE foi.order_status = 'Completed'
        GROUP BY p.product_id, p.category
        ORDER BY sku_net_revenue DESC;
        """
        df = self.manager.run_query(query)
        
        df["cum_revenue"] = df["sku_net_revenue"].cumsum()
        df["cum_revenue_pct"] = (df["cum_revenue"] / df["sku_net_revenue"].sum()) * 100.0
        df["sku_rank"] = np.arange(1, len(df) + 1)
        df["sku_rank_pct"] = (df["sku_rank"] / len(df)) * 100.0
        
        fig, ax1 = plt.subplots(figsize=(12, 6))
        
        # Pareto Curve
        ax1.plot(df["sku_rank_pct"], df["cum_revenue_pct"], color="#2563EB", linewidth=3, label="Cumulative Revenue %")
        ax1.axhline(80, color="#DC2626", linestyle="--", linewidth=1.5, label="80% Revenue Cutoff")
        
        # 80/20 intersection
        pareto_sku_idx = df[df["cum_revenue_pct"] >= 80].iloc[0]
        ax1.axvline(pareto_sku_idx["sku_rank_pct"], color="#DC2626", linestyle="--", linewidth=1.5)
        
        ax1.set_xlabel("Cumulative Percentage of SKUs (%)", fontweight="bold")
        ax1.set_ylabel("Cumulative Percentage of Net Revenue (%)", color="#2563EB", fontweight="bold")
        ax1.set_xlim(0, 100)
        ax1.set_ylim(0, 105)
        
        ax1.annotate(f"Pareto Threshold:\nTop {pareto_sku_idx['sku_rank_pct']:.1f}% of SKUs ({int(pareto_sku_idx['sku_rank'])} items)\ngenerate 80% of total revenue",
                     xy=(pareto_sku_idx["sku_rank_pct"], 80),
                     xytext=(pareto_sku_idx["sku_rank_pct"] + 8, 55),
                     arrowprops=dict(facecolor="#DC2626", shrink=0.08, width=1.5, headwidth=6),
                     fontsize=9, fontweight="bold", backgroundcolor="#FEF2F2")
        
        ax1.legend(loc="lower right")
        plt.title("Product Portfolio Pareto Analysis (SKU Revenue Concentration)", pad=15)
        fig.tight_layout()
        out_path = self.figures_dir / "04_category_pareto_margin_curve.png"
        plt.savefig(out_path)
        plt.close()
        logger.info(f"Saved: {out_path}")

    def plot_discount_elasticity_and_margin_drag(self) -> None:
        """
        Business Question:
        At what discount depth does promotional discounting destroy unit profitability
        and spike product return rates?
        """
        logger.info("Generating Discount Elasticity & Margin Drag figure...")
        query_path = Path(__file__).resolve().parent.parent.parent / "sql" / "analytics" / "06_discount_elasticity_profitability.sql"
        df = self.manager.run_query_file(query_path)
        
        fig, ax1 = plt.subplots(figsize=(11, 5.5))
        
        x = np.arange(len(df))
        width = 0.35
        
        # Bars for Realized Margin %
        rects1 = ax1.bar(x - width/2, df["realized_margin_pct"], width, label="Realized Margin Rate (%)", color="#059669")
        ax1.set_xlabel("Promotional Discount Band", fontweight="bold")
        ax1.set_ylabel("Gross Margin Rate (%)", color="#059669", fontweight="bold")
        ax1.tick_params(axis="y", labelcolor="#059669")
        ax1.set_xticks(x)
        ax1.set_xticklabels(df["discount_depth_band"], rotation=15, ha="right")
        ax1.set_ylim(0, 60)
        
        # Return Rate % on Twin Axis
        ax2 = ax1.twinx()
        rects2 = ax2.bar(x + width/2, df["return_rate_pct"], width, label="Return Rate (%)", color="#E11D48", alpha=0.85)
        ax2.set_ylabel("Product Return Rate (%)", color="#E11D48", fontweight="bold")
        ax2.tick_params(axis="y", labelcolor="#E11D48")
        ax2.set_ylim(0, 20)
        ax2.grid(False)
        
        # Value labels
        for rect in rects1:
            h = rect.get_height()
            ax1.text(rect.get_x() + rect.get_width()/2., h + 1, f"{h:.1f}%", ha="center", va="bottom", fontsize=9, fontweight="bold", color="#059669")
        for rect in rects2:
            h = rect.get_height()
            ax2.text(rect.get_x() + rect.get_width()/2., h + 0.4, f"{h:.1f}%", ha="center", va="bottom", fontsize=9, fontweight="bold", color="#E11D48")
            
        plt.title("Promotional Discount Depth vs Gross Margin & Product Return Rate", pad=15)
        fig.tight_layout()
        out_path = self.figures_dir / "05_discount_depth_vs_margin_elasticity.png"
        plt.savefig(out_path)
        plt.close()
        logger.info(f"Saved: {out_path}")

    def plot_channel_cac_ltv_comparison(self) -> None:
        """
        Business Question:
        Which customer acquisition channels deliver superior long-term Customer Lifetime
        Value (CLV) and repeat purchase loyalty?
        """
        logger.info("Generating Channel CAC and LTV figure...")
        query_path = Path(__file__).resolve().parent.parent.parent / "sql" / "analytics" / "05_channel_performance_clv.sql"
        df = self.manager.run_query_file(query_path)
        
        fig, ax1 = plt.subplots(figsize=(11, 5.5))
        
        x = np.arange(len(df))
        width = 0.35
        
        rects1 = ax1.bar(x - width/2, df["avg_clv_revenue"], width, label="Avg 12M CLV ($ Spend)", color="#4338CA")
        rects2 = ax1.bar(x + width/2, df["avg_clv_profit"], width, label="Avg 12M CLV ($ Profit)", color="#0EA5E9")
        
        ax1.set_xlabel("Customer Acquisition Channel", fontweight="bold")
        ax1.set_ylabel("USD ($ per Acquired Customer)", fontweight="bold")
        ax1.set_xticks(x)
        ax1.set_xticklabels(df["acquisition_channel"])
        ax1.set_ylim(0, max(df["avg_clv_revenue"]) * 1.3)
        ax1.legend(loc="upper right")
        
        for rect in rects1:
            h = rect.get_height()
            ax1.text(rect.get_x() + rect.get_width()/2., h + 15, f"${h:,.0f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
        for rect in rects2:
            h = rect.get_height()
            ax1.text(rect.get_x() + rect.get_width()/2., h + 15, f"${h:,.0f}", ha="center", va="bottom", fontsize=9, fontweight="bold", color="#0EA5E9")
            
        plt.title("Customer Lifetime Value (Gross Revenue vs Net Profit) by Acquisition Channel", pad=15)
        fig.tight_layout()
        out_path = self.figures_dir / "06_channel_cac_ltv_comparison.png"
        plt.savefig(out_path)
        plt.close()
        logger.info(f"Saved: {out_path}")

    def run_all(self) -> None:
        print("=" * 60)
        print("Executing Exploratory Business Analysis & Visualization Engine")
        print("=" * 60)
        self.plot_monthly_revenue_margin_trend()
        self.plot_cohort_retention_heatmap()
        self.plot_rfm_customer_segments()
        self.plot_category_pareto_margin_curve()
        self.plot_discount_elasticity_and_margin_drag()
        self.plot_channel_cac_ltv_comparison()
        print("=" * 60)
        print("All 6 Publication-Quality Figures Generated Successfully!")
        print("=" * 60)

if __name__ == "__main__":
    viewer = EDAViewer()
    viewer.run_all()
