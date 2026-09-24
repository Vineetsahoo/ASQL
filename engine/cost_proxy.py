"""Lightweight cost proxy using SQLite EXPLAIN QUERY PLAN.

Per PRD v2 §3: runs flagged queries against an in-memory SQLite DB
seeded with toy tables. Flags SCAN vs SEARCH as a crude "likely slow" signal.
This is NOT real timing benchmarking — just a structural cost indicator.
"""

import sqlite3
from typing import Optional


# DDL to seed the in-memory SQLite database with toy tables
SEED_DDL = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    order_date TEXT,
    total_amount REAL,
    status TEXT
);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT,
    city TEXT,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT,
    price REAL,
    category TEXT,
    stock_qty INTEGER
);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    unit_price REAL
);
CREATE INDEX IF NOT EXISTS idx_oi_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_oi_product ON order_items(product_id);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    name TEXT,
    department TEXT,
    salary REAL,
    hire_date TEXT
);
CREATE INDEX IF NOT EXISTS idx_emp_dept ON employees(department);

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY,
    name TEXT,
    budget REAL,
    location TEXT
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY,
    order_id INTEGER,
    invoice_date TEXT,
    amount REAL,
    paid INTEGER
);

CREATE TABLE IF NOT EXISTS shipments (
    id INTEGER PRIMARY KEY,
    order_id INTEGER,
    ship_date TEXT,
    carrier TEXT,
    tracking_no TEXT
);
"""

_connection: Optional[sqlite3.Connection] = None


def _register_helper_functions(conn: sqlite3.Connection) -> None:
    """Register common SQL functions not natively supported by SQLite."""
    helpers = {
        ("year", 1): lambda d: 2024,
        ("month", 1): lambda d: 1,
        ("day", 1): lambda d: 1,
        ("substring", 3): lambda s, start, length: (str(s)[start - 1 : start - 1 + length] if s is not None else None),
        ("left", 2): lambda s, n: (str(s)[:n] if s is not None else None),
        ("right", 2): lambda s, n: (str(s)[-n:] if s is not None else None),
        ("nvl", 2): lambda a, b: a if a is not None else b,
        ("isnull", 2): lambda a, b: a if a is not None else b,
        ("datepart", 2): lambda part, d: 2024,
        ("datediff", 3): lambda part, d1, d2: 0,
        ("dateadd", 3): lambda part, n, d: str(d),
    }
    for (name, num_params), fn in helpers.items():
        try:
            conn.create_function(name, num_params, fn)
        except Exception:
            pass


def _get_connection() -> sqlite3.Connection:
    """Get or create the in-memory SQLite connection with seeded tables."""
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(":memory:")
        _register_helper_functions(_connection)
        _connection.executescript(SEED_DDL)
    return _connection


def evaluate_cost_signal(sql: str) -> str:
    """Run EXPLAIN QUERY PLAN on the given SQL and return a cost signal.
    
    Returns:
        "FULL_SCAN_DETECTED" - if any table scan is found (no index used)
        "INDEX_USED" - if all accesses use indexes
        "NOT_EVALUATED" - if the query can't be explained (syntax issues, 
                          unknown tables, etc.)
    """
    conn = _get_connection()

    try:
        # EXPLAIN QUERY PLAN returns rows like:
        # (id, parent, notused, detail)
        # detail contains "SCAN" for full table scans, "SEARCH" for index lookups
        cursor = conn.execute(f"EXPLAIN QUERY PLAN {sql}")
        rows = cursor.fetchall()
    except Exception:
        return "NOT_EVALUATED"

    if not rows:
        return "NOT_EVALUATED"

    has_scan = False
    for row in rows:
        detail = str(row[-1]).upper() if row else ""
        if "SCAN" in detail and "SEARCH" not in detail:
            has_scan = True
            break

    return "FULL_SCAN_DETECTED" if has_scan else "INDEX_USED"


def close():
    """Close the SQLite connection."""
    global _connection
    if _connection:
        _connection.close()
        _connection = None
