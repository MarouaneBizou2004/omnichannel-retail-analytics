"""
Project Configuration Module
Centralizes paths, parameters, schemas, and analytical constants.
"""

from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SQL_DIR = PROJECT_ROOT / "sql"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
MODELS_DIR = PROJECT_ROOT / "models"
DASHBOARDS_DIR = PROJECT_ROOT / "dashboards"

# Ensure runtime directories exist
for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, FIGURES_DIR, MODELS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Database Configuration
DATABASE_PATH = PROCESSED_DATA_DIR / "retail_warehouse.db"

# Data Generation Parameters
RANDOM_SEED = 42
SIMULATION_START_DATE = "2024-01-01"
SIMULATION_END_DATE = "2025-12-31"
NUM_CUSTOMERS = 4500
NUM_PRODUCTS = 120
NUM_ORDERS = 16500

# Churn Modeling Parameters
# Observation cutoff separates feature history from future outcome (leakage prevention)
OBSERVATION_CUTOFF_DATE = "2025-10-01"
CHURN_EVALUATION_DAYS = 90  # 90-day future inactive window defines churn

# Business Parameters
RETENTION_CAMPAIGN_COST_PER_CUSTOMER = 15.0  # Cost of retention voucher/outreach ($)
AVERAGE_CUSTOMER_MARGIN_REVENUE = 120.0     # Expected recovered margin if retained ($)
SUCCESSFUL_RETENTION_RATE = 0.35            # Probability an at-risk customer accepts offer

# Product Categories and Margins
PRODUCT_CATEGORIES = {
    "Home & Living": {"subcategories": ["Furniture", "Cookware", "Bedding", "Decor"], "margin_range": (0.35, 0.55)},
    "Apparel & Footwear": {"subcategories": ["Outerwear", "Athleisure", "Footwear", "Accessories"], "margin_range": (0.45, 0.65)},
    "Consumer Electronics": {"subcategories": ["Audio", "Smart Home", "Accessories", "Wearables"], "margin_range": (0.20, 0.35)},
    "Beauty & Wellness": {"subcategories": ["Skincare", "Haircare", "Fragrance", "Supplements"], "margin_range": (0.50, 0.70)},
    "Outdoor & Fitness": {"subcategories": ["Camping", "Cycling", "Yoga & Gym", "Hydration"], "margin_range": (0.30, 0.50)}
}

CHANNELS = ["Web", "Mobile App", "In-Store"]
PAYMENT_METHODS = ["Credit Card", "PayPal", "Apple Pay", "Buy Now Pay Later"]
ACQUISITION_CHANNELS = ["Organic Search", "Paid Social", "Affiliate", "Direct", "Email/CRM"]
REGIONS = ["Northeast", "Midwest", "West", "South", "UK & Europe"]
