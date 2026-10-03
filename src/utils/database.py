"""
Relational Warehouse Engine & ETL Loader
Initializes SQLite relational data warehouse, generates surrogate keys,
populates Kimball Star Schema dimensions and facts, and runs analytical SQL queries.
"""

import sys
from pathlib import Path
import sqlite3
import logging
from typing import Optional
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    DATABASE_PATH,
    SQL_DIR,
    PROCESSED_DATA_DIR
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("WarehouseETL")

class WarehouseManager:
    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path
        
    def get_connection(self) -> sqlite3.Connection:
        """Returns SQLite connection with foreign keys enabled."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def initialize_schema(self) -> None:
        """Executes DDL to create Star Schema tables and indexes."""
        ddl_file = SQL_DIR / "schema" / "01_create_star_schema.sql"
        logger.info(f"Applying schema DDL from {ddl_file}...")
        
        with open(ddl_file, "r", encoding="utf-8") as f:
            ddl_script = f.read()
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(ddl_script)
            conn.commit()
            
        logger.info("Star Schema relational database initialized successfully.")

    def populate_date_dimension(self, start_date: str = "2024-01-01", end_date: str = "2025-12-31") -> None:
        """Generates comprehensive calendar dimension dim_date."""
        logger.info(f"Populating dim_date from {start_date} to {end_date}...")
        dates = pd.date_range(start=start_date, end=end_date, freq="D")
        
        date_records = []
        for d in dates:
            date_key = int(d.strftime("%Y%m%d"))
            full_date = d.strftime("%Y-%m-%d")
            day_of_week = d.isoweekday() # 1 = Mon, 7 = Sun
            day_name = d.strftime("%A")
            day_of_month = d.day
            month_num = d.month
            month_name = d.strftime("%B")
            quarter = (d.month - 1) // 3 + 1
            year = d.year
            year_month = d.strftime("%Y-%m")
            is_weekend = 1 if day_of_week in [6, 7] else 0
            
            # Holiday season: mid-November to year-end
            is_holiday_season = 1 if (month_num == 11 and day_of_month >= 15) or (month_num == 12) else 0
            
            date_records.append({
                "date_key": date_key,
                "full_date": full_date,
                "day_of_week": day_of_week,
                "day_name": day_name,
                "day_of_month": day_of_month,
                "month_number": month_num,
                "month_name": month_name,
                "calendar_quarter": quarter,
                "calendar_year": year,
                "year_month": year_month,
                "is_weekend": is_weekend,
                "is_holiday_season": is_holiday_season
            })
            
        df_date = pd.DataFrame(date_records)
        with self.get_connection() as conn:
            df_date.to_sql("dim_date", conn, if_exists="append", index=False)
            
        logger.info(f"Loaded {len(df_date)} calendar dates into dim_date.")

    def load_dimensions_and_facts(self) -> None:
        """Loads cleaned data into Star Schema with relational surrogate keys."""
        logger.info("Loading cleaned dimensions and facts into warehouse...")
        
        df_products = pd.read_parquet(PROCESSED_DATA_DIR / "dim_products.parquet")
        df_customers = pd.read_parquet(PROCESSED_DATA_DIR / "dim_customers.parquet")
        df_orders = pd.read_parquet(PROCESSED_DATA_DIR / "fact_orders.parquet")
        
        with self.get_connection() as conn:
            # 1. Populate dim_channel
            channels = [
                {"channel_name": "Web", "platform_type": "Desktop / Mobile Browser"},
                {"channel_name": "Mobile App", "platform_type": "iOS / Android Native"},
                {"channel_name": "In-Store", "platform_type": "Brick & Mortar POS"}
            ]
            pd.DataFrame(channels).to_sql("dim_channel", conn, if_exists="append", index=False)
            df_dim_channel = pd.read_sql("SELECT channel_key, channel_name FROM dim_channel", conn)
            channel_key_map = df_dim_channel.set_index("channel_name")["channel_key"].to_dict()
            
            # 2. Populate dim_product
            prod_cols = [
                "product_id", "product_name", "category", "subcategory",
                "unit_cost", "unit_price", "standard_margin_rate", "supplier_lead_time_days"
            ]
            df_products[prod_cols].to_sql("dim_product", conn, if_exists="append", index=False)
            df_dim_product = pd.read_sql("SELECT product_key, product_id FROM dim_product", conn)
            prod_key_map = df_dim_product.set_index("product_id")["product_key"].to_dict()
            
            # 3. Populate dim_customer
            cust_cols = [
                "customer_id", "first_name", "last_name", "email", "age", "age_group",
                "income_bracket", "region", "acquisition_channel", "acquisition_date", "loyalty_tier"
            ]
            df_cust_to_load = df_customers[cust_cols].copy()
            df_cust_to_load["acquisition_date"] = df_cust_to_load["acquisition_date"].dt.strftime("%Y-%m-%d")
            df_cust_to_load.to_sql("dim_customer", conn, if_exists="append", index=False)
            df_dim_customer = pd.read_sql("SELECT customer_key, customer_id FROM dim_customer", conn)
            cust_key_map = df_dim_customer.set_index("customer_id")["customer_key"].to_dict()
            
            # 4. Map surrogate keys to transaction line items
            df_lines = df_orders.copy()
            df_lines["customer_key"] = df_lines["customer_id"].map(cust_key_map)
            df_lines["product_key"] = df_lines["product_id"].map(prod_key_map)
            df_lines["channel_key"] = df_lines["channel"].map(channel_key_map)
            df_lines["date_key"] = pd.to_datetime(df_lines["order_timestamp"]).dt.strftime("%Y%m%d").astype(int)
            
            # 5. Populate fact_orders (order-grain roll-up)
            order_rollup = df_lines.groupby("order_id").agg({
                "customer_key": "first",
                "date_key": "first",
                "channel_key": "first",
                "order_timestamp": "first",
                "order_status": "first",
                "payment_method": "first",
                "is_return": "max",
                "gross_revenue": "sum",
                "discount_amount": "sum",
                "net_revenue": "sum",
                "cogs": "sum",
                "quantity": "sum",
                "shipping_cost": "first",
                "delivery_days": "first"
            }).reset_index()
            
            order_rollup.rename(columns={
                "gross_revenue": "gross_amount",
                "net_revenue": "net_amount",
                "cogs": "cogs_amount",
                "quantity": "item_count",
                "is_return": "is_returned"
            }, inplace=True)
            order_rollup["gross_margin"] = round(order_rollup["net_amount"] - order_rollup["cogs_amount"], 2)
            order_rollup["is_returned"] = order_rollup["is_returned"].astype(int)
            order_rollup["order_timestamp"] = pd.to_datetime(order_rollup["order_timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            
            order_rollup.to_sql("fact_orders", conn, if_exists="append", index=False)
            
            # Get order_key mappings
            df_dim_orders = pd.read_sql("SELECT order_key, order_id FROM fact_orders", conn)
            order_key_map = df_dim_orders.set_index("order_id")["order_key"].to_dict()
            
            # 6. Populate fact_order_items (item-grain)
            df_lines["order_key"] = df_lines["order_id"].map(order_key_map)
            df_lines["gross_profit"] = round(df_lines["net_revenue"] - df_lines["cogs"], 2)
            df_lines["is_returned"] = df_lines["is_return"].astype(int)
            
            fact_item_cols = [
                "order_key", "order_id", "customer_key", "product_key", "date_key", "channel_key",
                "quantity", "unit_price", "unit_cost", "discount_percent", "gross_revenue",
                "discount_amount", "net_revenue", "cogs", "gross_profit", "order_status", "is_returned"
            ]
            df_lines[fact_item_cols].to_sql("fact_order_items", conn, if_exists="append", index=False)
            
        logger.info(f"Loaded {len(order_rollup):,} records into fact_orders.")
        logger.info(f"Loaded {len(df_lines):,} records into fact_order_items.")

    def run_query(self, query: str) -> pd.DataFrame:
        """Executes an SQL query and returns result as a pandas DataFrame."""
        with self.get_connection() as conn:
            df = pd.read_sql(query, conn)
        return df

    def run_query_file(self, query_file_path: Path) -> pd.DataFrame:
        """Executes query from an external SQL file."""
        with open(query_file_path, "r", encoding="utf-8") as f:
            query = f.read()
        return self.run_query(query)

    def execute_full_etl(self) -> None:
        """End-to-end relational warehouse setup."""
        print("=" * 60)
        print("Starting Relational Star Schema ETL Pipeline")
        print("=" * 60)
        self.initialize_schema()
        self.populate_date_dimension()
        self.load_dimensions_and_facts()
        print("=" * 60)
        print("Relational Data Warehouse ETL Completed Successfully!")
        print("=" * 60)

if __name__ == "__main__":
    manager = WarehouseManager()
    manager.execute_full_etl()
