"""
Unit Tests for Data Ingestion, Cleaning & Transformation Pipeline
"""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import PROCESSED_DATA_DIR

@pytest.fixture
def processed_tables():
    products = pd.read_parquet(PROCESSED_DATA_DIR / "dim_products.parquet")
    customers = pd.read_parquet(PROCESSED_DATA_DIR / "dim_customers.parquet")
    orders = pd.read_parquet(PROCESSED_DATA_DIR / "fact_orders.parquet")
    return products, customers, orders

def test_product_data_integrity(processed_tables):
    products, _, _ = processed_tables
    assert not products.empty, "Product catalog is empty!"
    assert products["product_id"].is_unique, "Product IDs are not unique!"
    assert (products["unit_price"] > 0).all(), "Unit prices must be strictly positive!"
    assert (products["unit_cost"] > 0).all(), "Unit costs must be strictly positive!"
    assert (products["unit_price"] >= products["unit_cost"]).all(), "Baseline margins must be non-negative!"
    assert products["category"].str.istitle().all(), "Product categories must be properly title-cased!"

def test_customer_data_integrity(processed_tables):
    _, customers, _ = processed_tables
    assert not customers.empty, "Customer table is empty!"
    assert customers["customer_id"].is_unique, "Customer IDs are not unique!"
    assert customers["email"].str.contains("@").all(), "All customer emails must contain valid domain separator!"
    assert (customers["age"] >= 18).all() and (customers["age"] <= 100).all(), "Ages must fall within [18, 100]!"
    assert not customers["region"].isna().any(), "Regions must not contain null values!"

def test_order_financial_math(processed_tables):
    _, _, orders = processed_tables
    assert not orders.empty, "Order table is empty!"
    
    # Financial line-item formulas
    expected_gross = np.round(orders["quantity"] * orders["unit_price"], 2)
    assert np.allclose(orders["gross_revenue"], expected_gross, atol=0.02), "Gross revenue calculation mismatch!"
    
    expected_discount = np.round(orders["gross_revenue"] * orders["discount_percent"], 2)
    assert np.allclose(orders["discount_amount"], expected_discount, atol=0.02), "Discount amount calculation mismatch!"
    
    expected_net = np.round(orders["gross_revenue"] - orders["discount_amount"], 2)
    assert np.allclose(orders["net_revenue"], expected_net, atol=0.02), "Net revenue calculation mismatch!"
    
    assert (orders["net_revenue"] >= 0).all(), "Net revenue cannot be negative!"

def test_referential_integrity(processed_tables):
    products, customers, orders = processed_tables
    valid_customers = set(customers["customer_id"])
    valid_products = set(products["product_id"])
    
    assert set(orders["customer_id"]).issubset(valid_customers), "Foreign key violation: orphan customer_id in orders!"
    assert set(orders["product_id"]).issubset(valid_products), "Foreign key violation: orphan product_id in orders!"
