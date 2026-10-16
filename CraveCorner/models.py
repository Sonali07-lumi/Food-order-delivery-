"""Small serialization helpers that keep database paise values precise."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def rupees(paise: int) -> float:
    """Convert integer paise to a JSON-friendly rupee amount."""
    return float(Decimal(paise) / Decimal(100))


def serialize_menu_item(row: Any) -> dict[str, object]:
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "category": row["category"],
        "price": rupees(row["price_paise"]),
        "image_path": row["image_path"],
        "is_vegetarian": bool(row["is_vegetarian"]),
    }


def serialize_order(conn: Any, order: Any, include_private: bool = False) -> dict[str, object]:
    items = conn.execute(
        """SELECT item_name_snapshot, unit_price_paise, quantity, line_total_paise
           FROM order_items WHERE order_id = ? ORDER BY id""",
        (order["id"],),
    ).fetchall()
    result: dict[str, object] = {
        "order_number": order["order_number"],
        "customer_name": order["customer_name"],
        "total_amount": rupees(order["total_paise"]),
        "status": order["status"],
        "created_at": order["created_at"],
        "started_at": order["started_at"],
        "completed_at": order["completed_at"],
        "items": [
            {
                "name": item["item_name_snapshot"],
                "unit_price": rupees(item["unit_price_paise"]),
                "quantity": item["quantity"],
                "line_total": rupees(item["line_total_paise"]),
            }
            for item in items
        ],
    }
    if include_private:
        result["customer_phone"] = order["customer_phone"]
        result["delivery_address"] = order["delivery_address"]
    return result
