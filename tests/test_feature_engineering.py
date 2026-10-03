"""
Unit Tests for Feature Engineering & Target Formulation
"""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import PROCESSED_DATA_DIR, OBSERVATION_CUTOFF_DATE

@pytest.fixture
def feature_dataset():
    path = PROCESSED_DATA_DIR / "customer_features_churn.parquet"
    return pd.read_parquet(path)

def test_feature_matrix_dimensions(feature_dataset):
    assert not feature_dataset.empty, "Feature dataset is empty!"
    assert len(feature_dataset) > 1000, "Too few customer feature rows generated!"
    assert "churn_90d" in feature_dataset.columns, "Target column churn_90d is missing!"

def test_target_integrity(feature_dataset):
    unique_targets = set(feature_dataset["churn_90d"].unique())
    assert unique_targets.issubset({0, 1}), f"Target contains invalid values: {unique_targets}"
    assert feature_dataset["churn_90d"].isna().sum() == 0, "Target column contains null values!"
    
    churn_rate = feature_dataset["churn_90d"].mean()
    assert 0.40 < churn_rate < 0.98, f"Unrealistic churn rate: {churn_rate:.2%}"

def test_rfm_values(feature_dataset):
    assert (feature_dataset["recency_days"] >= 0).all(), "Recency days cannot be negative!"
    assert (feature_dataset["frequency"] >= 1).all(), "Frequency for active customers must be >= 1!"
    assert (feature_dataset["total_net_spend"] >= 0).all(), "Total spend cannot be negative!"
    assert (feature_dataset["avg_order_value"] >= 0).all(), "Average order value cannot be negative!"

def test_velocity_metrics(feature_dataset):
    assert (feature_dataset["orders_last_30d"] >= 0).all(), "30-day order count cannot be negative!"
    assert (feature_dataset["orders_last_90d"] >= 0).all(), "90-day order count cannot be negative!"
    assert (feature_dataset["orders_last_30d"] <= feature_dataset["orders_last_90d"]).all(), "30d orders cannot exceed 90d orders!"
    assert not feature_dataset["order_velocity_ratio"].isna().any(), "Velocity ratio contains NaN values!"
    assert not np.isinf(feature_dataset["order_velocity_ratio"]).any(), "Velocity ratio contains infinity values!"
