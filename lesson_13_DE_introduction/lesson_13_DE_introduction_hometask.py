# HOW TO RUN:
# 1. Ensure Docker Desktop is installed and running on your system.
# 2. Execute the following command in the project root folder:
#    docker compose up --build
#
# HOW TO VERIFY DATA IN POSTGRESQL:
# 1. Access the PostgreSQL interactive terminal (psql) inside the running container.
# 2. Use '\dt' to inspect and list all successfully created tables.
# 3. Use 'SELECT * FROM <table_name> LIMIT 10;' to inspect the processed rows.
# PIPELINE WORKFLOW (ETL ARCHITECTURE):
# 1. EXTRACT: 
#    - Automatically reads raw, imperfect e-commerce CSV files from 'data/raw/'.
#
# 2. TRANSFORM (Defensive Data Cleaning & Aggregation):
#    - Metadata Tuning: Sanitizes headers by forcing lowercase and stripping spaces.
#    - Deduplication: Removes missing primary keys and discards duplicate ID rows.
#    - Data Validation: Validates email formats via regex; filters prices and 
#      quantities to ensure they are strictly greater than zero.
#    - Normalization: Standardizes status strings and normalizes temporal timestamps.
#    - Referential Integrity: Cleanses fact tables by removing orphan records 
#      that do not map back to existing dimension IDs.
#
# 3. LOAD:
#    - Populates the active PostgreSQL instance with 4 clean relational tables.
#    - Automatically provisions 2 Analytical Data Marts directly inside the DB:
#      - 'analytics_top_customers': Aggregates metrics to analyze Lifetime Value (LTV).
#      - 'analytics_sales_by_product': Measures revenue performance across items.

import pandas as pd
from sqlalchemy import create_engine, text
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_DIR = os.path.join(BASE_DIR, 'data', 'raw')
DB_URI = "postgresql://de_user:de_password@postgres_db:5432/warehouse"

def get_db_engine():
    """Creates a SQLAlchemy engine for PostgreSQL database connection."""
    return create_engine(DB_URI)

def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    print("Cleaning customers data...")
    df = df.dropna(subset=['customer_id'])
    df = df.drop_duplicates(subset=['customer_id'], keep='first')

    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if 'email' in df.columns:
        df['email'] = df['email'].apply(
            lambda x: x if pd.notna(x) and re.match(email_regex, str(x)) else None
        )
    return df

def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    print("Cleaning products data...")
    df = df.dropna(subset=['product_id'])
    df = df.drop_duplicates(subset=['product_id'], keep='first')

    if 'price' in df.columns:
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df = df[df['price'] > 0]
    return df

def clean_orders(df: pd.DataFrame, valid_customers: set) -> pd.DataFrame:
    print("Cleaning orders data...")
    df = df.dropna(subset=['order_id'])
    df = df.drop_duplicates(subset=['order_id'], keep='first')

    valid_statuses = {'pending', 'processing', 'shipped', 'delivered', 'cancelled'}
    if 'status' in df.columns:
        df['status'] = df['status'].astype(str).str.lower().str.strip()
        df['status'] = df['status'].apply(lambda x: x if x in valid_statuses else 'unknown')
    else:
        df['status'] = 'unknown'

    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        df = df.dropna(subset=['created_at']) 

    df = df[df['customer_id'].isin(valid_customers)]
    return df

def clean_order_items(df: pd.DataFrame, valid_orders: set, valid_products: set) -> pd.DataFrame:
    print("Cleaning order items data...")
    df = df.dropna(subset=['order_item_id'])
    df = df.drop_duplicates(subset=['order_item_id'], keep='first')

    if 'quantity' in df.columns:
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
        df = df[df['quantity'] > 0]

    df = df[df['order_id'].isin(valid_orders)]
    df = df[df['product_id'].isin(valid_products)]
    return df

def create_analytics_tables(engine):
    """Creates analytical data marts directly in PostgreSQL using strictly normalized column names."""
    print("Creating analytical tables in PostgreSQL...")
    
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS analytics_top_customers;"))
        conn.execute(text("""
            CREATE TABLE analytics_top_customers AS
            SELECT 
                o.customer_id,
                COUNT(DISTINCT o.order_id) AS total_orders,
                SUM(oi.quantity * p.price) AS total_spent,
                AVG(oi.quantity * p.price) AS average_item_value
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN products p ON oi.product_id = p.product_id
            WHERE o.status != 'cancelled'
            GROUP BY o.customer_id;
        """))

        conn.execute(text("DROP TABLE IF EXISTS analytics_sales_by_product;"))
        conn.execute(text("""
            CREATE TABLE analytics_sales_by_product AS
            SELECT 
                oi.product_id,
                SUM(oi.quantity) AS total_units_sold,
                SUM(oi.quantity * p.price) AS total_revenue
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.status IN ('delivered', 'shipped')
            GROUP BY oi.product_id;
        """))

def run_pipeline():
    print("Starting ETL Pipeline...")

    print("Extracting raw data...")
    try:
        customers_raw = pd.read_csv(os.path.join(RAW_DATA_DIR, 'customers.csv'))
        products_raw = pd.read_csv(os.path.join(RAW_DATA_DIR, 'products.csv'))
        orders_raw = pd.read_csv(os.path.join(RAW_DATA_DIR, 'orders.csv'))
        order_items_raw = pd.read_csv(os.path.join(RAW_DATA_DIR, 'order_items.csv'))
    except FileNotFoundError as e:
        print(f"Error reading files: {e}")
        return

    customers_raw.columns = customers_raw.columns.str.lower().str.strip()
    products_raw.columns = products_raw.columns.str.lower().str.strip()
    orders_raw.columns = orders_raw.columns.str.lower().str.strip()
    order_items_raw.columns = order_items_raw.columns.str.lower().str.strip()

    customers_clean = clean_customers(customers_raw)
    products_clean = clean_products(products_raw)
    
    valid_customer_ids = set(customers_clean['customer_id'])
    valid_product_ids = set(products_clean['product_id'])
    
    orders_clean = clean_orders(orders_raw, valid_customer_ids)
    valid_order_ids = set(orders_clean['order_id'])
    
    order_items_clean = clean_order_items(order_items_raw, valid_order_ids, valid_product_ids)

    print("Loading cleaned data into PostgreSQL...")
    engine = get_db_engine()

    customers_clean.to_sql('customers', engine, if_exists='replace', index=False)
    products_clean.to_sql('products', engine, if_exists='replace', index=False)
    orders_clean.to_sql('orders', engine, if_exists='replace', index=False)
    order_items_clean.to_sql('order_items', engine, if_exists='replace', index=False)

    create_analytics_tables(engine)
    
    print("ETL Pipeline completed successfully! Data is ready for analysis.")

if __name__ == "__main__":
    run_pipeline()