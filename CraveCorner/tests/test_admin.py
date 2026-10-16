import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.security import generate_password_hash

from app import create_app
from database import connect
from queue_manager import OrderQueue


class AdminApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.sqlite3")
        self.queue = OrderQueue()
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-only-secret",
                "DATABASE": self.db_path,
                "QUEUE": self.queue,
            }
        )
        with connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO admin_users (username, password_hash, created_at)
                   VALUES (?, ?, ?)""",
                (
                    "kitchen",
                    generate_password_hash("correct-horse-battery-staple"),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            item = conn.execute(
                "SELECT id FROM menu_items ORDER BY id LIMIT 1"
            ).fetchone()
            self.item_id = item["id"]
        self.client = self.app.test_client()
        self.csrf = self.client.get("/api/csrf").get_json()["csrf_token"]

    def tearDown(self):
        self.temp_dir.cleanup()

    def _login(self, password="correct-horse-battery-staple"):
        return self.client.post(
            "/api/admin/login",
            json={"username": "kitchen", "password": password},
            headers={"X-CSRF-Token": self.csrf},
        )

    def _order(self, quantity=1):
        token = self.client.get("/api/csrf").get_json()["csrf_token"]
        return self.client.post(
            "/api/orders",
            json={
                "customer_name": "Test Customer",
                "customer_phone": "9876543210",
                "items": [{"menu_item_id": self.item_id, "quantity": quantity}],
            },
            headers={"X-CSRF-Token": token},
        ).get_json()["order_number"]

    def test_admin_routes_require_authentication(self):
        response = self.client.get("/api/admin/orders")
        self.assertEqual(response.status_code, 401)

    def test_valid_and_invalid_authentication(self):
        self.assertEqual(self._login("wrong-password").status_code, 401)
        self.assertEqual(self._login().status_code, 200)
        self.assertEqual(
            self.client.get("/api/admin/session").get_json()["username"], "kitchen"
        )

    def test_login_attempts_are_limited(self):
        client = self.app.test_client()
        remote = "192.0.2.42"
        token = client.get(
            "/api/csrf", environ_base={"REMOTE_ADDR": remote}
        ).get_json()["csrf_token"]
        responses = [
            client.post(
                "/api/admin/login",
                json={"username": "kitchen", "password": "wrong"},
                headers={"X-CSRF-Token": token},
                environ_base={"REMOTE_ADDR": remote},
            )
            for _ in range(6)
        ]
        self.assertEqual(
            [response.status_code for response in responses[:5]], [401] * 5
        )
        self.assertEqual(responses[5].status_code, 429)

    def test_backend_enforces_fifo_and_preserves_completed_order_history(self):
        first = self._order()
        second = self._order()
        self.assertNotEqual(first, second)
        self.assertEqual(self._login().status_code, 200)
        csrf = self.client.get("/api/admin/session").get_json()["csrf_token"]

        blocked = self.client.post(
            f"/api/admin/orders/{second}/start",
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(blocked.status_code, 409)

        started = self.client.post(
            f"/api/admin/orders/{first}/start",
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(started.status_code, 200)
        self.assertEqual(started.get_json()["status"], "PREPARING")
        completed = self.client.post(
            f"/api/admin/orders/{first}/complete",
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.get_json()["status"], "COMPLETED")
        duplicate = self.client.post(
            f"/api/admin/orders/{first}/complete",
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(duplicate.status_code, 409)
        invalid_transition = self.client.post(
            f"/api/admin/orders/{second}/complete",
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(invalid_transition.status_code, 409)
        self.assertEqual(self.queue.get_next_order(), second)
        tracked = self.client.get(f"/api/orders/{first}").get_json()
        self.assertEqual(tracked["status"], "COMPLETED")

        history = self.client.get("/api/admin/orders").get_json()
        first_saved = next(row for row in history if row["order_number"] == first)
        self.assertEqual(first_saved["status"], "COMPLETED")
        stats = self.client.get("/api/admin/stats").get_json()
        self.assertEqual(stats["completed_orders"], 1)

    def test_restart_restores_incomplete_orders_in_arrival_order(self):
        first = self._order()
        second = self._order()
        self.assertEqual(self._login().status_code, 200)
        csrf = self.client.get("/api/admin/session").get_json()["csrf_token"]
        self.client.post(
            f"/api/admin/orders/{first}/start", headers={"X-CSRF-Token": csrf}
        )

        restored = OrderQueue()
        restarted_app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-only-secret",
                "DATABASE": self.db_path,
                "QUEUE": restored,
            }
        )
        self.assertEqual(restored.get_queue_status()["active"], [first, second])
        self.assertEqual(restarted_app.test_client().get("/api/healthz").status_code, 200)


if __name__ == "__main__":
    unittest.main()
