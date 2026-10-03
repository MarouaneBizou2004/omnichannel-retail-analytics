"""
Raw Dataset Generation Script
Synthesizes a high-fidelity omnichannel retail dataset with realistic business distributions,
cohort decay patterns, seasonal peaks (Q4/Black Friday), and intentional real-world data flaws
(duplicates, inconsistent casing, missing demographic values, negative return lines).
"""

import sys
from pathlib import Path
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Ensure src is in sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.config import (
    RAW_DATA_DIR,
    RANDOM_SEED,
    SIMULATION_START_DATE,
    SIMULATION_END_DATE,
    NUM_CUSTOMERS,
    NUM_PRODUCTS,
    PRODUCT_CATEGORIES,
    CHANNELS,
    PAYMENT_METHODS,
    ACQUISITION_CHANNELS,
    REGIONS,
)

def set_seed(seed: int = RANDOM_SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)

def generate_products(num_products: int = NUM_PRODUCTS) -> pd.DataFrame:
    """Generates the raw product catalog with pricing, costs, and categories."""
    products = []
    prod_id = 1001

    category_names = list(PRODUCT_CATEGORIES.keys())
    
    # Adjectives and nouns for realistic naming
    adjectives = ["Pro", "Classic", "Ultra", "Eco", "Smart", "Signature", "Heritage", "Nordic", "Active", "Studio"]
    
    for _ in range(num_products):
        category = random.choice(category_names)
        subcat = random.choice(PRODUCT_CATEGORIES[category]["subcategories"])
        margin_min, margin_max = PRODUCT_CATEGORIES[category]["margin_range"]
        
        # Base retail price based on category
        if category == "Home & Living":
            retail_price = round(random.uniform(35.0, 320.0), 2)
        elif category == "Consumer Electronics":
            retail_price = round(random.uniform(49.0, 450.0), 2)
        elif category == "Beauty & Wellness":
            retail_price = round(random.uniform(18.0, 95.0), 2)
        elif category == "Apparel & Footwear":
            retail_price = round(random.uniform(28.0, 180.0), 2)
        else: # Outdoor & Fitness
            retail_price = round(random.uniform(22.0, 220.0), 2)
            
        target_margin = random.uniform(margin_min, margin_max)
        unit_cost = round(retail_price * (1.0 - target_margin), 2)
        
        name = f"{random.choice(adjectives)} {subcat} {random.randint(10, 99)}"
        lead_time = random.choice([2, 3, 5, 7, 10, 14, None]) # intentional rare nulls
        
        # Introduce casing quirks into raw data
        raw_category = category
        if random.random() < 0.08:
            raw_category = category.lower() if random.random() < 0.5 else category.upper()
            
        products.append({
            "product_id": f"PRD-{prod_id}",
            "product_name": name,
            "category": raw_category,
            "subcategory": subcat,
            "unit_price": retail_price,
            "unit_cost": unit_cost,
            "supplier_lead_time_days": lead_time
        })
        prod_id += 1
        
    df = pd.DataFrame(products)
    return df

def generate_customers(num_customers: int = NUM_CUSTOMERS) -> pd.DataFrame:
    """Generates customer profiles with demographics, channels, and acquisition dates."""
    first_names = ["James", "Emma", "Liam", "Olivia", "Noah", "Sophia", "Oliver", "Ava", "Elijah", "Isabella",
                   "Lucas", "Mia", "Benjamin", "Charlotte", "Henry", "Amelia", "Alexander", "Harper", "Sebastian", "Evelyn",
                   "Mateo", "Camila", "Jack", "Gianna", "Daniel", "Abigail", "Julian", "Ella", "David", "Avery",
                   "Tariq", "Fatima", "Chen", "Yuki", "Marco", "Elena", "Chloe", "Lars", "Siddharth", "Priya"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                  "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
                  "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"]
    
    email_domains = ["gmail.com", "yahoo.com", "outlook.com", "icloud.com", "company.org", "mail.com"]
    income_brackets = ["< $35k", "$35k-$65k", "$65k-$100k", "$100k-$150k", "> $150k"]
    loyalty_tiers = ["Bronze", "Silver", "Gold", "Platinum"]
    
    start_dt = datetime.strptime(SIMULATION_START_DATE, "%Y-%m-%d")
    end_dt = datetime.strptime("2025-10-31", "%Y-%m-%d")
    total_days = (end_dt - start_dt).days
    
    customers = []
    for i in range(1, num_customers + 1):
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        domain = random.choice(email_domains)
        email = f"{fn.lower()}.{ln.lower()}{random.randint(1, 999)}@{domain}"
        
        # Demographics with realistic missingness
        age = random.randint(18, 72) if random.random() > 0.04 else None
        income = random.choice(income_brackets) if random.random() > 0.05 else None
        
        # Acquisition time (front-loaded with continuous growth)
        day_offset = int(np.random.beta(1.5, 2.5) * total_days)
        acq_date = start_dt + timedelta(days=day_offset)
        
        # Tier assignment weighted towards entry levels
        tier = np.random.choice(loyalty_tiers, p=[0.60, 0.25, 0.11, 0.04])
        region = random.choice(REGIONS)
        acq_chan = random.choice(ACQUISITION_CHANNELS)
        
        # Intentional uppercase email or string whitespace
        if random.random() < 0.05:
            email = email.upper()
        if random.random() < 0.03:
            region = f"  {region}  "
            
        customers.append({
            "customer_id": f"CUST-{i:05d}",
            "first_name": fn,
            "last_name": ln,
            "email": email,
            "age": age,
            "income_bracket": income,
            "region": region,
            "acquisition_channel": acq_chan,
            "acquisition_date": acq_date.strftime("%Y-%m-%d"),
            "loyalty_tier": tier
        })
        
    df = pd.DataFrame(customers)
    
    # Introduce duplicate rows (0.8% duplicated records from system replay)
    dup_sample = df.sample(frac=0.008, random_state=RANDOM_SEED)
    df = pd.concat([df, dup_sample], ignore_index=True)
    return df

def generate_orders_and_items(df_customers: pd.DataFrame, df_products: pd.DataFrame) -> pd.DataFrame:
    """
    Generates realistic order line items across 2024-2025.
    Implements customer repeat purchase propensity, Q4 holiday spikes,
    payment channels, order status, discounts, and fulfillment metrics.
    """
    sim_start = datetime.strptime(SIMULATION_START_DATE, "%Y-%m-%d")
    sim_end = datetime.strptime(SIMULATION_END_DATE, "%Y-%m-%d")
    
    cust_dict = {}
    for _, row in df_customers.drop_duplicates(subset=["customer_id"]).iterrows():
        cust_dict[row["customer_id"]] = {
            "acq_date": datetime.strptime(row["acquisition_date"], "%Y-%m-%d"),
            "loyalty_tier": row["loyalty_tier"]
        }
        
    products_lookup = df_products.to_dict(orient="records")
    
    raw_lines = []
    order_counter = 10001
    
    # Channel dirty string variants
    channel_variants = {
        "Web": ["Web", "web", "WEB", "Online-Web"],
        "Mobile App": ["Mobile App", "mobile_app", "Mobile-App", "APP"],
        "In-Store": ["In-Store", "in_store", "INSTORE", "Physical Store"]
    }
    
    for cust_id, cust_info in cust_dict.items():
        acq_date = cust_info["acq_date"]
        tier = cust_info["loyalty_tier"]
        
        # Customer repeat purchase frequency follows negative binomial / geometric distribution
        tier_order_multiplier = {"Bronze": 1.1, "Silver": 2.2, "Gold": 3.8, "Platinum": 6.5}
        expected_orders = max(1, int(np.random.negative_binomial(1.8, 0.45) * tier_order_multiplier[tier]))
        
        curr_order_date = acq_date
        
        for ord_idx in range(expected_orders):
            if ord_idx > 0:
                # Interval between purchases: Log-normal inter-purchase time
                days_gap = int(np.random.lognormal(mean=3.6, sigma=0.75))
                curr_order_date = curr_order_date + timedelta(days=days_gap)
                
            if curr_order_date > sim_end:
                break
                
            # Seasonality boost: November/December Q4 multiplier (Black Friday / Holidays)
            month = curr_order_date.month
            day_of_month = curr_order_date.day
            is_black_friday = (month == 11 and day_of_month >= 20)
            is_holiday_rush = (month == 12 and day_of_month <= 23)
            
            # Base order attributes
            order_id = f"ORD-{curr_order_date.year}-{order_counter:06d}"
            order_counter += 1
            
            # Channel selection
            base_channel = random.choice(CHANNELS)
            channel_str = random.choice(channel_variants[base_channel]) if random.random() < 0.25 else base_channel
            
            # Payment method
            payment = random.choice(PAYMENT_METHODS)
            
            # Order items count (1 to 4 items in basket)
            num_items = np.random.choice([1, 2, 3, 4], p=[0.55, 0.28, 0.12, 0.05])
            
            # Order level discount
            base_discount = 0.0
            if is_black_friday:
                base_discount = round(random.uniform(0.15, 0.35), 2)
            elif is_holiday_rush or random.random() < 0.22:
                base_discount = round(random.uniform(0.05, 0.25), 2)
            elif tier in ["Gold", "Platinum"] and random.random() < 0.40:
                base_discount = 0.10 # Loyalty perk
                
            # Order fulfillment status
            # Apparel and BNPL orders have higher return propensities
            return_prob = 0.06
            if payment == "Buy Now Pay Later":
                return_prob += 0.05
            
            is_cancelled = (random.random() < 0.02)
            is_returned = (not is_cancelled and random.random() < return_prob)
            
            if is_cancelled:
                status = "Cancelled"
            elif is_returned:
                status = "Returned"
            else:
                status = "Completed"
                
            # Shipping delivery days (lognormal distribution, occasional carrier delay)
            delivery_days = int(np.clip(np.random.lognormal(mean=1.2, sigma=0.4), 1, 15))
            shipping_fee = 0.0 if (random.random() < 0.4 or tier in ["Gold", "Platinum"]) else random.choice([4.99, 7.99, 12.99])
            
            # Sample items in this basket
            selected_products = random.sample(products_lookup, num_items)
            for prod in selected_products:
                qty = np.random.choice([1, 2, 3], p=[0.82, 0.14, 0.04])
                
                # Intentional edge case: Negative quantity for logged returns or credit memos
                if status == "Returned" and random.random() < 0.15:
                    qty = -1 * qty
                    
                # Time string formatted with occasional format variations
                if random.random() < 0.05:
                    timestamp_str = curr_order_date.strftime("%Y/%m/%d %H:%M:%S")
                else:
                    timestamp_str = curr_order_date.strftime("%Y-%m-%d %H:%M:%S")
                    
                raw_lines.append({
                    "order_id": order_id,
                    "customer_id": cust_id,
                    "order_timestamp": timestamp_str,
                    "channel": channel_str,
                    "payment_method": payment,
                    "product_id": prod["product_id"],
                    "quantity": qty,
                    "unit_price": prod["unit_price"],
                    "discount_percent": base_discount,
                    "shipping_cost": shipping_fee,
                    "order_status": status,
                    "delivery_days": delivery_days
                })
                
    df_orders = pd.DataFrame(raw_lines)
    
    # Introduce duplicate rows (0.5% duplicates)
    dup_orders = df_orders.sample(frac=0.005, random_state=RANDOM_SEED)
    df_orders = pd.concat([df_orders, dup_orders], ignore_index=True)
    
    return df_orders

def main() -> None:
    print("=" * 60)
    print("Starting Raw Enterprise Dataset Generation")
    print("=" * 60)
    
    set_seed(RANDOM_SEED)
    
    print(f"Generating {NUM_PRODUCTS} products across categories...")
    df_products = generate_products(NUM_PRODUCTS)
    products_path = RAW_DATA_DIR / "raw_products.csv"
    df_products.to_csv(products_path, index=False)
    print(f"Saved raw products to: {products_path} ({len(df_products)} rows)")
    
    print(f"Generating {NUM_CUSTOMERS} customers with demographic profiles...")
    df_customers = generate_customers(NUM_CUSTOMERS)
    customers_path = RAW_DATA_DIR / "raw_customers.csv"
    df_customers.to_csv(customers_path, index=False)
    print(f"Saved raw customers to: {customers_path} ({len(df_customers)} rows)")
    
    print("Generating omnichannel transaction line items and order logs...")
    df_orders = generate_orders_and_items(df_customers, df_products)
    orders_path = RAW_DATA_DIR / "raw_orders.csv"
    df_orders.to_csv(orders_path, index=False)
    print(f"Saved raw orders to: {orders_path} ({len(df_orders)} rows)")
    
    print("=" * 60)
    print("Raw Dataset Generation Completed Successfully!")
    print(f"Summary:")
    print(f" - Raw Customers: {len(df_customers):,}")
    print(f" - Raw Products:  {len(df_products):,}")
    print(f" - Raw Lines:     {len(df_orders):,}")
    print("=" * 60)

if __name__ == "__main__":
    main()
