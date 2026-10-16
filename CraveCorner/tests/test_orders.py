import tempfile
import unittest
from pathlib import Path

from app import create_app
from database import connect
from queue_manager import OrderQueue


class OrderApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.sqlite3")
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-only-secret",
                "DATABASE": self.db_path,
                "QUEUE": OrderQueue(),
            }
        )
        with connect(self.db_path) as conn:
            self.item = conn.execute(
                "SELECT id, price_paise FROM menu_items ORDER BY id LIMIT 1"
            ).fetchone()
        self.client = self.app.test_client()
        self.csrf = self.client.get("/api/csrf").get_json()["csrf_token"]

    def tearDown(self):
        self.temp_dir.cleanup()

    def _place_order(self, items=None):
        return self.client.post(
            "/api/orders",
            json={
                "customer_name": "Test Customer",
                "customer_phone": "9876543210",
                "items": items
                if items is not None
                else [{"menu_item_id": self.item["id"], "quantity": 2}],
                "total_amount": 0,
            },
            headers={"X-CSRF-Token": self.csrf},
        )

    def test_valid_order_uses_server_price_and_persists(self):
        response = self._place_order()
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["total_amount"], self.item["price_paise"] * 2 / 100)
        self.assertTrue(data["order_number"].startswith("CC-"))
        self.assertEqual(self.app.config["QUEUE"].get_next_order(), data["order_number"])
        with connect(self.db_path) as conn:
            saved = conn.execute(
                "SELECT total_paise FROM orders WHERE order_number = ?",
                (data["order_number"],),
            ).fetchone()
        self.assertEqual(saved["total_paise"], self.item["price_paise"] * 2)

    def test_empty_order_invalid_item_and_invalid_quantity_are_rejected(self):
        self.assertEqual(self._place_order([]).status_code, 400)
        self.assertEqual(
            self._place_order([{"menu_item_id": 999999, "quantity": 1}]).status_code,
            400,
        )
        self.assertEqual(
            self._place_order([{"menu_item_id": self.item["id"], "quantity": -1}]).status_code,
            400,
        )

    def test_browser_cannot_submit_without_csrf_token(self):
        response = self.client.post(
            "/api/orders",
            json={
                "customer_name": "Test Customer",
                "customer_phone": "9876543210",
                "items": [{"menu_item_id": self.item["id"], "quantity": 1}],
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_tracking_hides_private_contact_details(self):
        order = self._place_order().get_json()
        response = self.client.get(f"/api/orders/{order['order_number']}")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("customer_phone", response.get_json())
        self.assertNotIn("delivery_address", response.get_json())


if __name__ == "__main__":
    unittest.main()
