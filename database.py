import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "products.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create products table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        specs TEXT NOT NULL
    )
    ''')
    
    # Create warranty_records table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS warranty_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        serial_number TEXT UNIQUE NOT NULL,
        product_id TEXT NOT NULL,
        product_name TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        purchase_date TEXT NOT NULL,
        warranty_months INTEGER NOT NULL,
        care_plus INTEGER DEFAULT 0,
        status TEXT NOT NULL
    )
    ''')
    
    # Seed Products if table is empty
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        products_seed = [
            ("TPL-X1-2026", "TechPro Laptop X1 Ultra", "Laptops", 1499.99, "Intel Core Ultra 7, 32GB RAM, 1TB SSD, 14\" 2.8K OLED"),
            ("TPA-EAR-PRO", "TechPro Wireless Earbuds Air Pro", "Audio", 179.99, "Hybrid ANC 45dB, 32hr Battery, IPX5, Wireless Charging"),
            ("TPS-WATCH-U2", "TechPro Smartwatch Ultra 2", "Wearables", 299.99, "1.96\" AMOLED, Titanium Body, ECG & SpO2, 5 ATM"),
            ("TPH-HUB-7IN1", "TechPro 7-in-1 USB-C Hub", "Accessories", 49.99, "4K@60Hz HDMI, 100W PD Pass-through, SD/microSD, 3x USB 3.0")
        ]
        cursor.executemany("INSERT INTO products (product_id, name, category, price, specs) VALUES (?, ?, ?, ?, ?)", products_seed)
    
    # Seed Warranty Records if table is empty
    cursor.execute("SELECT COUNT(*) FROM warranty_records")
    if cursor.fetchone()[0] == 0:
        warranties_seed = [
            ("SN1001", "TPL-X1-2026", "TechPro Laptop X1 Ultra", "Alex Vance", "2025-11-15", 12, 0, "Active"),
            ("SN1002", "TPL-X1-2026", "TechPro Laptop X1 Ultra", "Sarah Connor", "2023-05-10", 12, 0, "Expired"),
            ("SN1003", "TPA-EAR-PRO", "TechPro Wireless Earbuds Air Pro", "Michael Scott", "2026-01-20", 12, 0, "Active"),
            ("SN1004", "TPA-EAR-PRO", "TechPro Wireless Earbuds Air Pro", "Pam Beesly", "2024-02-14", 12, 0, "Expired"),
            ("SN1005", "TPS-WATCH-U2", "TechPro Smartwatch Ultra 2", "Bruce Wayne", "2025-08-01", 24, 1, "Active"),
            ("SN1006", "TPS-WATCH-U2", "TechPro Smartwatch Ultra 2", "Clark Kent", "2024-01-10", 12, 0, "Expired"),
            ("SN1007", "TPH-HUB-7IN1", "TechPro 7-in-1 USB-C Hub", "Diana Prince", "2026-02-01", 12, 0, "Active"),
            ("SN1008", "TPH-HUB-7IN1", "TechPro 7-in-1 USB-C Hub", "Barry Allen", "2024-06-15", 12, 0, "Expired")
        ]
        cursor.executemany("""
        INSERT INTO warranty_records (serial_number, product_id, product_name, customer_name, purchase_date, warranty_months, care_plus, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, warranties_seed)
        
    conn.commit()
    conn.close()

def check_warranty(serial_number):
    """
    Queries SQLite database for serial number and evaluates exact warranty status against current date.
    """
    if not serial_number:
        return {"found": False, "message": "No serial number provided."}
    
    sn_clean = serial_number.strip().upper()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM warranty_records WHERE UPPER(serial_number) = ?", (sn_clean,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {
            "found": False,
            "serial_number": sn_clean,
            "message": f"Serial number '{sn_clean}' was not found in the official TechPro warranty database."
        }
    
    record = dict(row)
    p_date = datetime.strptime(record["purchase_date"], "%Y-%m-%d")
    w_months = record["warranty_months"]
    
    # Calculate expiry date approx (adding days)
    expiry_date = p_date + timedelta(days=w_months * 30)
    today = datetime.now()
    
    is_active = today <= expiry_date
    status_str = "ACTIVE" if is_active else "EXPIRED"
    days_left = (expiry_date - today).days if is_active else 0
    
    return {
        "found": True,
        "serial_number": record["serial_number"],
        "product_id": record["product_id"],
        "product_name": record["product_name"],
        "customer_name": record["customer_name"],
        "purchase_date": record["purchase_date"],
        "warranty_months": record["warranty_months"],
        "expiry_date": expiry_date.strftime("%Y-%m-%d"),
        "care_plus": bool(record["care_plus"]),
        "status": status_str,
        "is_active": is_active,
        "days_remaining": days_left,
        "message": f"Serial number {record['serial_number']} ({record['product_name']}) purchase on {record['purchase_date']} is {status_str} (Expires: {expiry_date.strftime('%Y-%m-%d')})."
    }

def get_all_products():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_all_warranties():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM warranty_records")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
    print("Test SN1001:", check_warranty("SN1001"))
