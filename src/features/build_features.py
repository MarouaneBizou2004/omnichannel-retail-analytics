"""
Feature Engineering Pipeline
Constructs behavioral, RFM, temporal velocity, profitability, and categorical features
with strict observation-window cutoff filtering to guarantee ZERO future data leakage.
"""

import sys
from pathlib import Path
import logging
from typing import Tuple
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    PROCESSED_DATA_DIR,
    OBSERVATION_CUTOFF_DATE,
    CHURN_EVALUATION_DAYS
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FeatureEngineering")

class FeatureBuilder:
    def __init__(self, cutoff_date: str = OBSERVATION_CUTOFF_DATE, eval_days: int = CHURN_EVALUATION_DAYS):
        self.cutoff_date = pd.to_datetime(cutoff_date)
        self.eval_end_date = self.cutoff_date + pd.Timedelta(days=eval_days)
        
    def load_clean_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Loads cleaned normalized datasets."""
        logger.info("Loading cleaned tables for feature construction...")
        df_customers = pd.read_parquet(PROCESSED_DATA_DIR / "dim_customers.parquet")
        df_orders = pd.read_parquet(PROCESSED_DATA_DIR / "fact_orders.parquet")
        df_products = pd.read_parquet(PROCESSED_DATA_DIR / "dim_products.parquet")
        
        df_orders["order_timestamp"] = pd.to_datetime(df_orders["order_timestamp"])
        df_customers["acquisition_date"] = pd.to_datetime(df_customers["acquisition_date"])
        return df_customers, df_orders, df_products

    def construct_features_and_target(self) -> pd.DataFrame:
        """
        Builds feature matrix from history <= cutoff_date,
        and derives target label from activity between cutoff_date and eval_end_date.
        """
        df_customers, df_orders, df_products = self.load_clean_data()
        
        # 1. Filter historical orders strictly before or on cutoff date (LEAKAGE PREVENTION)
        hist_orders = df_orders[df_orders["order_timestamp"] <= self.cutoff_date].copy()
        
        # 2. Customers eligible for modeling: acquired before cutoff and placed at least 1 order
        eligible_custs = hist_orders["customer_id"].unique()
        logger.info(f"Identified {len(eligible_custs):,} active customers with history on or before {self.cutoff_date.date()}.")
        
        # 3. Future evaluation orders strictly in (cutoff_date, eval_end_date]
        future_orders = df_orders[
            (df_orders["order_timestamp"] > self.cutoff_date) &
            (df_orders["order_timestamp"] <= self.eval_end_date) &
            (df_orders["order_status"] == "Completed")
        ].copy()
        
        retained_customers = set(future_orders["customer_id"].unique())
        
        # Target: 1 if Churned (0 orders in future 90 days), 0 if Retained
        logger.info(f"Target calculation: {len(retained_customers):,} customers retained in 90-day post-cutoff window.")
        
        # 4. Compute Historical RFM and Behavioral Metrics
        # Aggregate completed orders
        completed_hist = hist_orders[hist_orders["order_status"] == "Completed"].copy()
        
        # Recency: days between latest order and cutoff
        latest_orders = completed_hist.groupby("customer_id")["order_timestamp"].max()
        recency_days = (self.cutoff_date - latest_orders).dt.total_seconds() / 86400.0
        
        # Order Frequency & Monetary Aggregates
        order_stats = completed_hist.groupby("customer_id").agg(
            frequency=("order_id", "nunique"),
            total_net_spend=("net_revenue", "sum"),
            avg_order_value=("net_revenue", "mean"),
            max_order_value=("net_revenue", "max"),
            total_gross_profit=("realized_gross_margin", "sum"),
            total_items=("quantity", "sum"),
            avg_items_per_order=("quantity", "mean"),
            avg_discount_received=("discount_percent", "mean")
        )
        
        # All orders (including returned/cancelled) to compute friction rates
        friction_stats = hist_orders.groupby("customer_id").agg(
            total_orders_logged=("order_id", "nunique"),
            return_orders_count=("is_return", "sum"),
            cancelled_orders_count=("order_status", lambda x: (x == "Cancelled").sum())
        )
        friction_stats["return_rate"] = friction_stats["return_orders_count"] / friction_stats["total_orders_logged"]
        friction_stats["cancellation_rate"] = friction_stats["cancelled_orders_count"] / friction_stats["total_orders_logged"]
        
        # Velocity Features: Activity in last 30 days and last 90 days before cutoff
        cutoff_minus_30 = self.cutoff_date - pd.Timedelta(days=30)
        cutoff_minus_90 = self.cutoff_date - pd.Timedelta(days=90)
        
        orders_30d = completed_hist[completed_hist["order_timestamp"] >= cutoff_minus_30].groupby("customer_id")["order_id"].nunique()
        orders_90d = completed_hist[completed_hist["order_timestamp"] >= cutoff_minus_90].groupby("customer_id")["order_id"].nunique()
        
        # Channel & Payment Preferences (mode)
        primary_channel = hist_orders.groupby("customer_id")["channel"].agg(lambda x: x.mode()[0] if len(x.mode()) > 0 else "Web")
        primary_payment = hist_orders.groupby("customer_id")["payment_method"].agg(lambda x: x.mode()[0] if len(x.mode()) > 0 else "Credit Card")
        
        # Catalog Breadth: Distinct Categories Purchased
        merged_line_prods = hist_orders.merge(df_products[["product_id", "category"]], on="product_id", how="left")
        distinct_categories = merged_line_prods.groupby("customer_id")["category"].nunique()
        
        # Assemble Master Feature Table
        features = pd.DataFrame({"customer_id": eligible_custs})
        features = features.merge(df_customers[[
            "customer_id", "age", "income_bracket", "region", "acquisition_channel", "acquisition_date", "loyalty_tier"
        ]], on="customer_id", how="left")
        
        # Customer tenure (days from acquisition to cutoff)
        features["tenure_days"] = (self.cutoff_date - features["acquisition_date"]).dt.days
        
        # Merge computed behavioral metrics
        features["recency_days"] = features["customer_id"].map(recency_days).fillna(features["tenure_days"])
        features = features.merge(order_stats, on="customer_id", how="left")
        features = features.merge(friction_stats[["return_rate", "cancellation_rate"]], on="customer_id", how="left")
        
        features["orders_last_30d"] = features["customer_id"].map(orders_30d).fillna(0).astype(int)
        features["orders_last_90d"] = features["customer_id"].map(orders_90d).fillna(0).astype(int)
        
        # Velocity ratio: recent order intensity relative to 90-day baseline
        features["order_velocity_ratio"] = features["orders_last_30d"] / ((features["orders_last_90d"] / 3.0) + 0.1)
        
        features["primary_channel"] = features["customer_id"].map(primary_channel).fillna("Web")
        features["primary_payment"] = features["customer_id"].map(primary_payment).fillna("Credit Card")
        features["distinct_categories"] = features["customer_id"].map(distinct_categories).fillna(1).astype(int)
        
        # Fill missing numeric values
        features["frequency"] = features["frequency"].fillna(1).astype(int)
        features["total_net_spend"] = features["total_net_spend"].fillna(0.0)
        features["avg_order_value"] = features["avg_order_value"].fillna(0.0)
        features["max_order_value"] = features["max_order_value"].fillna(0.0)
        features["total_gross_profit"] = features["total_gross_profit"].fillna(0.0)
        features["total_items"] = features["total_items"].fillna(1).astype(int)
        features["avg_items_per_order"] = features["avg_items_per_order"].fillna(1.0)
        features["avg_discount_received"] = features["avg_discount_received"].fillna(0.0)
        features["return_rate"] = features["return_rate"].fillna(0.0)
        features["cancellation_rate"] = features["cancellation_rate"].fillna(0.0)
        
        # Margin ratio
        features["gross_margin_ratio"] = np.where(
            features["total_net_spend"] > 0,
            features["total_gross_profit"] / features["total_net_spend"],
            0.0
        )
        
        # Target Formulation: 1 if Churned (did NOT purchase in future 90 days), 0 if Retained
        features["churn_90d"] = features["customer_id"].apply(
            lambda cid: 0 if cid in retained_customers else 1
        )
        
        churn_rate = features["churn_90d"].mean() * 100.0
        logger.info(f"Engineered feature set: {len(features):,} customers with {len(features.columns)} attributes.")
        logger.info(f"Target Distribution: {features['churn_90d'].sum():,} churned ({churn_rate:.2f}%), {(1 - features['churn_90d']).sum():,} retained.")
        
        return features

    def run(self) -> pd.DataFrame:
        print("=" * 60)
        print("Executing Feature Engineering Pipeline (Zero-Leakage Guard)")
        print("=" * 60)
        df_features = self.construct_features_and_target()
        
        output_parquet = PROCESSED_DATA_DIR / "customer_features_churn.parquet"
        output_csv = PROCESSED_DATA_DIR / "customer_features_churn.csv"
        
        df_features.to_parquet(output_parquet, index=False)
        df_features.to_csv(output_csv, index=False)
        logger.info(f"Features and labels successfully saved to {output_parquet}")
        print("=" * 60)
        print("Feature Engineering Completed Successfully!")
        print("=" * 60)
        return df_features

if __name__ == "__main__":
    builder = FeatureBuilder()
    builder.run()
