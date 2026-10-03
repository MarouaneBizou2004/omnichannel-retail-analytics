"""
Unit Tests for Machine Learning Pipeline & Model Inference
"""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np
import joblib

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import MODELS_DIR, PROCESSED_DATA_DIR

@pytest.fixture
def trained_pipeline():
    model_path = MODELS_DIR / "churn_pipeline.joblib"
    assert model_path.exists(), f"Model artifact not found at {model_path}!"
    return joblib.load(model_path)

@pytest.fixture
def sample_features():
    path = PROCESSED_DATA_DIR / "customer_features_churn.parquet"
    df = pd.read_parquet(path)
    return df.head(20)

def test_model_pipeline_predict_proba(trained_pipeline, sample_features):
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
    X_sample = sample_features[feature_cols]
    probabilities = trained_pipeline.predict_proba(X_sample)
    
    assert probabilities.shape == (20, 2), "Inference probabilities shape is incorrect!"
    assert (probabilities >= 0.0).all() and (probabilities <= 1.0).all(), "Probabilities outside [0, 1]!"
    assert np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-5), "Class probabilities must sum to 1.0!"

def test_unseen_customer_prediction(trained_pipeline):
    # Synthetic edge-case customer
    synthetic_cust = pd.DataFrame([{
        "age": 34,
        "tenure_days": 180,
        "recency_days": 15,
        "frequency": 4,
        "total_net_spend": 550.0,
        "avg_order_value": 137.5,
        "max_order_value": 210.0,
        "total_gross_profit": 220.0,
        "total_items": 7,
        "avg_items_per_order": 1.75,
        "avg_discount_received": 0.05,
        "return_rate": 0.0,
        "cancellation_rate": 0.0,
        "orders_last_30d": 2,
        "orders_last_90d": 3,
        "order_velocity_ratio": 2.0,
        "distinct_categories": 3,
        "gross_margin_ratio": 0.40,
        "region": "West",
        "acquisition_channel": "Organic Search",
        "loyalty_tier": "Gold",
        "primary_channel": "Mobile App",
        "primary_payment": "Apple Pay",
        "income_bracket": "$65k-$100k"
    }])
    
    prob = trained_pipeline.predict_proba(synthetic_cust)[0, 1]
    assert 0.0 <= prob <= 1.0, f"Unseen customer probability invalid: {prob}"
