"""
Unit Tests for Relational Star Schema Database & Analytical Queries
"""

import sys
from pathlib import Path
import pytest
import sqlite3
import pandas as pd

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import DATABASE_PATH, SQL_DIR
from src.utils.database import WarehouseManager

@pytest.fixture
def warehouse():
    manager = WarehouseManager(DATABASE_PATH)
    return manager

def test_database_tables_exist(warehouse):
    query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    tables_df = warehouse.run_query(query)
    table_names = set(tables_df["name"])
    
    expected_tables = {
        "dim_customer",
        "dim_product",
        "dim_date",
        "dim_channel",
        "fact_orders",
        "fact_order_items"
    }
    assert expected_tables.issubset(table_names), f"Missing tables in warehouse! Found: {table_names}"

def test_table_row_counts(warehouse):
    cust_count = warehouse.run_query("SELECT COUNT(*) AS n FROM dim_customer")["n"].iloc[0]
    prod_count = warehouse.run_query("SELECT COUNT(*) AS n FROM dim_product")["n"].iloc[0]
    date_count = warehouse.run_query("SELECT COUNT(*) AS n FROM dim_date")["n"].iloc[0]
    order_count = warehouse.run_query("SELECT COUNT(*) AS n FROM fact_orders")["n"].iloc[0]
    item_count = warehouse.run_query("SELECT COUNT(*) AS n FROM fact_order_items")["n"].iloc[0]
    
    assert cust_count > 4000, f"Unexpected customer count: {cust_count}"
    assert prod_count >= 100, f"Unexpected product count: {prod_count}"
    assert date_count == 731, f"Unexpected date dimension days: {date_count}"
    assert order_count > 10000, f"Unexpected order count: {order_count}"
    assert item_count >= order_count, f"Item count should be >= order count: {item_count} vs {order_count}"

def test_sql_analytical_queries_execute(warehouse):
    analytics_dir = SQL_DIR / "analytics"
    sql_files = list(analytics_dir.glob("*.sql"))
    assert len(sql_files) >= 5, "Fewer than 5 analytical SQL queries found!"
    
    for f in sql_files:
        df = warehouse.run_query_file(f)
        assert not df.empty, f"Analytical query {f.name} returned empty results!"
        assert len(df.columns) > 1, f"Analytical query {f.name} has no columns!"
