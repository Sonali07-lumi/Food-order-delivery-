"""SQLite schema, seed data, and connection helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class ClosingConnection(sqlite3.Connection):
    """A SQLite connection context manager that also closes on exit."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


MENU_SEED = [
    ("Corner Classic Burger", "Smash patty, aged cheddar, pickles and house sauce.", "Burgers", 34900, "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=900&q=85", 0),
    ("Smoky BBQ Burger", "Charred onion, smoked barbecue glaze and crisp lettuce.", "Burgers", 38900, "https://images.unsplash.com/photo-1553979459-d2229ba7433a?auto=format&fit=crop&w=900&q=85", 0),
    ("Garden Crunch Burger", "Herbed potato patty, tomato, lettuce and mint mayo.", "Burgers", 29900, "https://images.unsplash.com/photo-1520072959219-c595dc870360?auto=format&fit=crop&w=900&q=85", 1),
    ("Margherita Garden Pizza", "Basil, mozzarella and bright tomato on a crisp crust.", "Pizza", 32900, "https://images.unsplash.com/photo-1579751626657-72bc17010498?auto=format&fit=crop&w=900&q=85", 1),
    ("Roasted Pepper Pizza", "Roasted peppers, olives, onion and mozzarella.", "Pizza", 38900, "https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=900&q=85", 1),
    ("Farmhouse Feast Pizza", "A generous mix of mushrooms, peppers and sweet corn.", "Pizza", 42900, "https://images.unsplash.com/photo-1571407970349-bc81e7e96d47?auto=format&fit=crop&w=900&q=85", 1),
    ("Creamy Truffle Alfredo", "Silky parmesan cream, cracked pepper and herbs.", "Pasta", 36900, "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?auto=format&fit=crop&w=900&q=85", 1),
    ("Spicy Arrabbiata", "Slow-simmered tomato, garlic, chilli and basil.", "Pasta", 31900, "https://images.unsplash.com/photo-1551183053-bf91a1d81141?auto=format&fit=crop&w=900&q=85", 1),
    ("Roasted Tomato Penne", "Penne tossed with roast tomatoes and parmesan.", "Pasta", 33900, "https://images.unsplash.com/photo-1551183053-bf91a1d81141?auto=format&fit=crop&w=900&q=85", 1),
    ("Chicken Pesto Melt", "Grilled chicken, basil pesto and melted cheese.", "Sandwiches", 32900, "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?auto=format&fit=crop&w=900&q=85", 0),
    ("Crispy Paneer Club", "Golden paneer, crunchy slaw and coriander chutney.", "Sandwiches", 28900, "https://images.unsplash.com/photo-1553909489-cd47e0ef937f?auto=format&fit=crop&w=900&q=85", 1),
    ("Golden Parmesan Fries", "Crisp-cut potatoes, parmesan and garden herbs.", "Starters", 18900, "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?auto=format&fit=crop&w=900&q=85", 1),
    ("Crispy Chicken Bites", "Buttermilk-marinated bites with smoky dip.", "Starters", 26900, "https://images.unsplash.com/photo-1562967914-608f82629710?auto=format&fit=crop&w=900&q=85", 0),
    ("Chilli Garlic Mushrooms", "Pan-seared mushrooms with garlic and fresh chilli.", "Starters", 22900, "https://images.unsplash.com/photo-1504544750208-dc0358e63f7f?auto=format&fit=crop&w=900&q=85", 1),
    ("Loaded Nachos", "Corn chips, salsa, cheese and a little jalapeño.", "Starters", 24900, "https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?auto=format&fit=crop&w=900&q=85", 1),
    ("Chocolate Fudge Brownie", "Warm chocolate brownie with a soft-centred finish.", "Desserts", 19900, "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=900&q=85", 1),
    ("Classic Tiramisu", "Coffee-soaked layers with a dusting of cocoa.", "Desserts", 23900, "https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?auto=format&fit=crop&w=900&q=85", 1),
    ("Vanilla Bean Cheesecake", "Creamy baked cheesecake with a biscuit base.", "Desserts", 22900, "https://images.unsplash.com/photo-1533134242443-d4fd215305ad?auto=format&fit=crop&w=900&q=85", 1),
    ("Fresh Lime Cooler", "Fresh lime, mint and a sparkling finish.", "Beverages", 12900, "https://images.unsplash.com/photo-1513558161293-cdaf765edfd7?auto=format&fit=crop&w=900&q=85", 1),
    ("Mango Lassi", "Chilled yoghurt blended with ripe mango.", "Beverages", 14900, "https://images.unsplash.com/photo-1527661591475-527312dd65f5?auto=format&fit=crop&w=900&q=85", 1),
    ("Cold Brew Coffee", "Slow-steeped coffee served smooth and chilled.", "Beverages", 16900, "https://images.unsplash.com/photo-1517701604599-bb29b565090c?auto=format&fit=crop&w=900&q=85", 1),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS menu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    price_paise INTEGER NOT NULL CHECK (price_paise > 0),
    image_path TEXT NOT NULL,
    is_vegetarian INTEGER NOT NULL DEFAULT 0 CHECK (is_vegetarian IN (0, 1)),
    is_available INTEGER NOT NULL DEFAULT 1 CHECK (is_available IN (0, 1))
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT NOT NULL UNIQUE,
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    delivery_address TEXT,
    total_paise INTEGER NOT NULL CHECK (total_paise >= 0),
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'PREPARING', 'COMPLETED')),
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    menu_item_id INTEGER REFERENCES menu_items(id) ON DELETE SET NULL,
    item_name_snapshot TEXT NOT NULL,
    unit_price_paise INTEGER NOT NULL CHECK (unit_price_paise >= 0),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    line_total_paise INTEGER NOT NULL CHECK (line_total_paise >= 0)
);

CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_status_id ON orders(status, id);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
"""


def connect(database: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(
        str(database),
        timeout=10,
        isolation_level=None,
        factory=ClosingConnection,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def initialize_database(database: str | Path) -> None:
    path = Path(database)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)
        conn.executemany(
            """INSERT INTO menu_items
               (name, description, category, price_paise, image_path, is_vegetarian)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(name) DO NOTHING""",
            MENU_SEED,
        )
