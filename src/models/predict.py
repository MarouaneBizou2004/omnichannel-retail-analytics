"""
Production Batch Scoring & Retention Action Recommender
Loads trained churn pipeline, computes predicted churn risk probabilities for customers,
assigns risk tiers, and generates targeted intervention recommendations.
"""

import sys
from pathlib import Path
import logging
from typing import Optional
import pandas as pd
import numpy as np
import joblib

# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    PROCESSED_DATA_DIR,
    MODELS_DIR
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ChurnPredictor")

class BatchChurnPredictor:
    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or (MODELS_DIR / "churn_pipeline.joblib")
        logger.info(f"Loading serialized model pipeline from {self.model_path}...")
        self.pipeline = joblib.load(self.model_path)
        
    def score_customers(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """Scores customer feature records and prescribes business retention actions."""
        logger.info(f"Generating churn probabilities for {len(features_df):,} customers...")
        
        # Isolate features
        feature_cols = [
            "age", "tenure_days", "recency_days", "frequency",
            "total_net_spend", "avg_order_value", "max_order_value",
            "total_gross_profit", "total_items", "avg_items_per_order",
            "avg_discount_received", "return_rate", "cancellation_rate",
            "orders_last_30d", "orders_last_90d", "order_velocity_ratio",
            "distinct_categories", "gross_margin_ratio",
            "region", "acquisition_channel", "loyalty_tier",
            "primary_channel", "primary_payment", "income_bracket"
        ]
        
        X = features_df[feature_cols].copy()
        churn_probabilities = self.pipeline.predict_proba(X)[:, 1]
        
        scored_df = features_df.copy()
        scored_df["churn_probability"] = np.round(churn_probabilities, 4)
        
        # Risk Tiers
        conditions = [
            (scored_df["churn_probability"] >= 0.80),
            (scored_df["churn_probability"] >= 0.50),
            (scored_df["churn_probability"] >= 0.25),
        ]
        tier_choices = ["Critical Risk", "High Risk", "Moderate Risk"]
        scored_df["risk_tier"] = np.select(conditions, tier_choices, default="Low Risk (Healthy)")
        
        # Business Intervention Logic
        def assign_action(row):
            tier = row["risk_tier"]
            spend = row["total_net_spend"]
            loyalty = row["loyalty_tier"]
            
            if tier == "Critical Risk":
                if spend > 800 or loyalty in ["Gold", "Platinum"]:
                    return "VIP Concierge Outreach + Personalized Re-engagement Gift"
                else:
                    return "Automated Win-Back 20% Discount Voucher"
            elif tier == "High Risk":
                if spend > 500:
                    return "Targeted Product Recommendation + Free Shipping Perk"
                else:
                    return "Dynamic Cart Abandonment / Catalog Push"
            elif tier == "Moderate Risk":
                return "Category Exploration Newsletter + Loyalty Point Bonus"
            else:
                return "Standard Marketing Cadence / Cross-Sell"
                
        scored_df["prescribed_action"] = scored_df.apply(assign_action, axis=1)
        
        return scored_df

    def run(self) -> pd.DataFrame:
        print("=" * 60)
        print("Executing Batch Retention Scoring Pipeline")
        print("=" * 60)
        
        features_path = PROCESSED_DATA_DIR / "customer_features_churn.parquet"
        df_features = pd.read_parquet(features_path)
        
        scored_df = self.score_customers(df_features)
        
        out_parquet = PROCESSED_DATA_DIR / "scored_customers_retention.parquet"
        out_csv = PROCESSED_DATA_DIR / "scored_customers_retention.csv"
        
        scored_df.to_parquet(out_parquet, index=False)
        scored_df.to_csv(out_csv, index=False)
        
        logger.info(f"Saved scored customer dataset to: {out_parquet}")
        
        tier_counts = scored_df["risk_tier"].value_counts()
        print("\nPredicted Customer Risk Tier Distribution:")
        for tier, count in tier_counts.items():
            print(f" - {tier:20s}: {count:,} ({count/len(scored_df)*100:.1f}%)")
            
        print("=" * 60)
        print("Batch Scoring Pipeline Completed Successfully!")
        print("=" * 60)
        return scored_df

if __name__ == "__main__":
    predictor = BatchChurnPredictor()
    predictor.run()
