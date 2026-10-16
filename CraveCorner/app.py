"""CraveCorner Flask application and REST API."""

from __future__ import annotations

import hmac
import logging
import re
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from flask import (
    Flask,
    abort,
    current_app,
    jsonify,
    render_template,
    request,
    session,
)
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash

from config import PROJECT_DIR, load_config
from database import connect, initialize_database
from models import rupees, serialize_menu_item, serialize_order
from queue_manager import OrderQueue, QueueError

_LOGIN_ATTEMPTS: dict[str, list[float]] = {}
_LOGIN_LOCK = threading.Lock()
_MAX_LOGIN_FAILURES = 5
_LOGIN_WINDOW_SECONDS = 15 * 60
_PHONE_ALLOWED = re.compile(r"^\+?[\d\s()\-]+$")


def _json_error(message: str, status: int):
    return jsonify({"error": message}), status


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _db() -> sqlite3.Connection:
    return connect(current_app.config["DATABASE"])


def _require_admin(view: Callable):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return _json_error("Administrator sign-in is required.", 401)
        return view(*args, **kwargs)

    return wrapped


def _csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def _rate_limit_key() -> str:
    username = str((request.get_json(silent=True) or {}).get("username", ""))[:80]
    return f"{request.remote_addr or 'unknown'}:{username.casefold()}"


def _login_is_limited(key: str) -> bool:
    now = time.monotonic()
    with _LOGIN_LOCK:
        attempts = [
            attempt
            for attempt in _LOGIN_ATTEMPTS.get(key, [])
            if now - attempt < _LOGIN_WINDOW_SECONDS
        ]
        _LOGIN_ATTEMPTS[key] = attempts
        return len(attempts) >= _MAX_LOGIN_FAILURES


def _record_login_failure(key: str) -> None:
    now = time.monotonic()
    with _LOGIN_LOCK:
        attempts = [
            attempt
            for attempt in _LOGIN_ATTEMPTS.get(key, [])
            if now - attempt < _LOGIN_WINDOW_SECONDS
        ]
        attempts.append(now)
        _LOGIN_ATTEMPTS[key] = attempts


def _clear_login_failures(key: str) -> None:
    with _LOGIN_LOCK:
        _LOGIN_ATTEMPTS.pop(key, None)


def _parse_order_input(payload: Any) -> tuple[str, str, str | None, dict[int, int]]:
    if not isinstance(payload, dict):
        raise ValueError("Send order details as a JSON object.")

    name = payload.get("customer_name")
    if not isinstance(name, str) or not 2 <= len(name.strip()) <= 100:
        raise ValueError("Enter a name between 2 and 100 characters.")
    name = name.strip()

    phone = payload.get("customer_phone")
    if not isinstance(phone, str) or not _PHONE_ALLOWED.fullmatch(phone.strip()):
        raise ValueError("Enter a valid contact number.")
    phone = re.sub(r"[\s()\-]", "", phone.strip())
    digits = phone[1:] if phone.startswith("+") else phone
    if not digits.isdigit() or not 10 <= len(digits) <= 15:
        raise ValueError("Enter a contact number with 10 to 15 digits.")

    address = payload.get("delivery_address", "")
    if address is None:
        address = ""
    if not isinstance(address, str) or len(address.strip()) > 500:
        raise ValueError("Delivery address must be 500 characters or fewer.")
    address = address.strip() or None

    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("Your cart is empty. Add an item before placing an order.")
    if len(raw_items) > 50:
        raise ValueError("An order can contain at most 50 distinct menu items.")

    items: dict[int, int] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            raise ValueError("Each order item must include an item ID and quantity.")
        item_id = item.get("menu_item_id")
        quantity = item.get("quantity")
        if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 1:
            raise ValueError("A menu item ID is invalid.")
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            raise ValueError("Item quantities must be whole numbers.")
        if not 1 <= quantity <= 50:
            raise ValueError("Each item quantity must be between 1 and 50.")
        items[item_id] = items.get(item_id, 0) + quantity
        if items[item_id] > 50:
            raise ValueError("An item quantity cannot exceed 50.")
    return name, phone, address, items


def _fetch_order(conn: sqlite3.Connection, order_number: str):
    return conn.execute(
        "SELECT * FROM orders WHERE order_number = ?", (order_number,)
    ).fetchone()


def create_app(test_config: dict[str, object] | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(load_config())
    if test_config:
        app.config.update(test_config)
    app.config.setdefault("QUEUE", OrderQueue())
    app.logger.setLevel(logging.INFO)

    initialize_database(app.config["DATABASE"])
    queue: OrderQueue = app.config["QUEUE"]
    with connect(app.config["DATABASE"]) as conn:
        active = conn.execute(
            """SELECT order_number FROM orders
               WHERE status IN ('PENDING', 'PREPARING') ORDER BY id ASC"""
        ).fetchall()
    queue.restore_pending_orders(row["order_number"] for row in active)

    @app.before_request
    def protect_state_changes():
        if request.path.startswith("/api/") and request.method in {
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        }:
            expected = session.get("csrf_token", "")
            supplied = request.headers.get("X-CSRF-Token", "")
            if not expected or not supplied or not hmac.compare_digest(
                expected, supplied
            ):
                return _json_error(
                    "This request expired or could not be verified. Refresh and try again.",
                    403,
                )
        return None

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        if request.path.startswith("/api/"):
            return _json_error(error.description, error.code or 500)
        try:
            return render_template(
                "error.html", status=error.code or 500, message=error.description
            ), error.code or 500
        except Exception:
            return error.description, error.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception("Unhandled application error", exc_info=error)
        if request.path.startswith("/api/"):
            return _json_error("Something went wrong. Please try again.", 500)
        try:
            return render_template(
                "error.html",
                status=500,
                message="Something went wrong. Please try again.",
            ), 500
        except Exception:
            return "Something went wrong. Please try again.", 500

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/menu")
    @app.get("/menu.html")
    def menu_page():
        return render_template("menu.html")

    @app.get("/cart")
    @app.get("/cart.html")
    def cart_page():
        return render_template("cart.html")

    @app.get("/checkout")
    @app.get("/checkout.html")
    def checkout_page():
        return render_template("checkout.html")

    @app.get("/confirmation/<order_number>")
    def confirmation_page(order_number: str):
        return render_template("confirmation.html", order_number=order_number)

    @app.get("/tracking")
    @app.get("/tracking.html")
    def tracking_page():
        return render_template("tracking.html")

    @app.get("/about")
    @app.get("/about.html")
    def about_page():
        return render_template("about.html")

    @app.get("/admin/login")
    @app.get("/admin-login.html")
    def admin_login_page():
        if session.get("admin_id"):
            from flask import redirect

            return redirect("/admin")
        return render_template("admin_login.html")

    @app.get("/admin")
    @app.get("/admin.html")
    def admin_page():
        if not session.get("admin_id"):
            from flask import redirect

            return redirect("/admin/login")
        return render_template("admin.html", username=session.get("username", ""))

    @app.get("/api/healthz")
    def health_check():
        return jsonify({"status": "ok"})

    @app.get("/api/csrf")
    def get_csrf_token():
        return jsonify({"csrf_token": _csrf_token()})

    @app.get("/api/menu")
    def list_menu():
        category = request.args.get("category", "").strip()
        search = request.args.get("search", "").strip()
        vegetarian = request.args.get("vegetarian")
        if len(search) > 100:
            return _json_error("Search text must be 100 characters or fewer.", 400)
        if category and len(category) > 40:
            return _json_error("That category is not valid.", 400)
        if vegetarian not in {None, "", "true", "false"}:
            return _json_error("Vegetarian filter must be true or false.", 400)

        clauses = ["is_available = 1"]
        params: list[object] = []
        if category:
            clauses.append("category = ?")
            params.append(category)
        if vegetarian in {"true", "false"}:
            clauses.append("is_vegetarian = ?")
            params.append(1 if vegetarian == "true" else 0)
        if search:
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            clauses.append("(name LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')")
            params.extend((f"%{escaped}%", f"%{escaped}%"))
        with _db() as conn:
            rows = conn.execute(
                f"SELECT * FROM menu_items WHERE {' AND '.join(clauses)} ORDER BY id",
                params,
            ).fetchall()
        return jsonify([serialize_menu_item(row) for row in rows])

    @app.get("/api/menu/<int:item_id>")
    def get_menu_item(item_id: int):
        with _db() as conn:
            row = conn.execute(
                "SELECT * FROM menu_items WHERE id = ? AND is_available = 1",
                (item_id,),
            ).fetchone()
        if not row:
            return _json_error("That menu item is not available.", 404)
        return jsonify(serialize_menu_item(row))

    @app.post("/api/orders")
    def create_order():
        try:
            name, phone, address, requested_items = _parse_order_input(
                request.get_json(silent=True)
            )
        except ValueError as error:
            return _json_error(str(error), 400)

        with queue.lock:
            conn = connect(current_app.config["DATABASE"])
            try:
                conn.execute("BEGIN IMMEDIATE")
                placeholders = ",".join("?" for _ in requested_items)
                menu_rows = conn.execute(
                    f"""SELECT id, name, price_paise FROM menu_items
                        WHERE is_available = 1 AND id IN ({placeholders})""",
                    list(requested_items.keys()),
                ).fetchall()
                menu_by_id = {row["id"]: row for row in menu_rows}
                unavailable = [
                    item_id
                    for item_id in requested_items
                    if item_id not in menu_by_id
                ]
                if unavailable:
                    conn.rollback()
                    return _json_error(
                        "One or more selected items are no longer available.", 400
                    )

                total_paise = sum(
                    menu_by_id[item_id]["price_paise"] * quantity
                    for item_id, quantity in requested_items.items()
                )
                created_at = _now()
                cursor = conn.execute(
                    """INSERT INTO orders
                       (order_number, customer_name, customer_phone, delivery_address,
                        total_paise, status, created_at)
                       VALUES (?, ?, ?, ?, ?, 'PENDING', ?)""",
                    ("TEMP", name, phone, address, total_paise, created_at),
                )
                db_id = cursor.lastrowid
                year = datetime.now().year
                order_number = f"CC-{year}-{db_id:04d}"
                conn.execute(
                    "UPDATE orders SET order_number = ? WHERE id = ?",
                    (order_number, db_id),
                )
                for item_id, quantity in requested_items.items():
                    item = menu_by_id[item_id]
                    unit_price = item["price_paise"]
                    conn.execute(
                        """INSERT INTO order_items
                           (order_id, menu_item_id, item_name_snapshot,
                            unit_price_paise, quantity, line_total_paise)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            db_id,
                            item_id,
                            item["name"],
                            unit_price,
                            quantity,
                            unit_price * quantity,
                        ),
                    )
                conn.commit()
                queue.enqueue_order(order_number)
                order = _fetch_order(conn, order_number)
                result = serialize_order(conn, order)
            except sqlite3.Error:
                conn.rollback()
                app.logger.exception("Could not save a customer order")
                return _json_error("The order could not be saved. Please try again.", 500)
            finally:
                conn.close()
        return jsonify(result), 201

    @app.get("/api/orders/<order_number>")
    def track_order(order_number: str):
        with _db() as conn:
            order = _fetch_order(conn, order_number.strip().upper())
            if not order:
                return _json_error(
                    "We couldn't find that order. Check the ID and try again.", 404
                )
            return jsonify(serialize_order(conn, order, include_private=False))

    @app.post("/api/admin/login")
    def admin_login():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return _json_error("Enter your username and password.", 400)
        username = payload.get("username")
        password = payload.get("password")
        if (
            not isinstance(username, str)
            or not 1 <= len(username.strip()) <= 80
            or not isinstance(password, str)
            or not 1 <= len(password) <= 200
        ):
            return _json_error("Enter your username and password.", 400)

        key = _rate_limit_key()
        if _login_is_limited(key):
            return _json_error(
                "Too many sign-in attempts. Wait 15 minutes before trying again.", 429
            )
        with _db() as conn:
            user = conn.execute(
                "SELECT id, username, password_hash FROM admin_users WHERE username = ? COLLATE NOCASE",
                (username.strip(),),
            ).fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            _record_login_failure(key)
            return _json_error("The username or password is incorrect.", 401)

        _clear_login_failures(key)
        session.clear()
        session["admin_id"] = user["id"]
        session["username"] = user["username"]
        session["csrf_token"] = secrets.token_urlsafe(32)
        session.permanent = True
        return jsonify(
            {"username": user["username"], "csrf_token": session["csrf_token"]}
        )

    @app.post("/api/admin/logout")
    @_require_admin
    def admin_logout():
        session.clear()
        return jsonify({"message": "You have been signed out."})

    @app.get("/api/admin/session")
    @_require_admin
    def admin_session():
        return jsonify(
            {"username": session["username"], "csrf_token": _csrf_token()}
        )

    @app.get("/api/admin/orders")
    @_require_admin
    def admin_orders():
        with _db() as conn:
            rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
            return jsonify(
                [
                    serialize_order(conn, row, include_private=True)
                    for row in rows
                ]
            )

    @app.get("/api/admin/queue")
    @_require_admin
    def admin_queue():
        with _db() as conn:
            statuses = {
                row["order_number"]: row["status"]
                for row in conn.execute(
                    "SELECT order_number, status FROM orders WHERE status IN ('PENDING', 'PREPARING')"
                ).fetchall()
            }
        return jsonify(queue.get_queue_status(lambda number: statuses.get(number)))

    @app.get("/api/admin/stats")
    @_require_admin
    def admin_stats():
        with _db() as conn:
            row = conn.execute(
                """SELECT COUNT(*) AS total_orders,
                   SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) AS pending_orders,
                   SUM(CASE WHEN status = 'PREPARING' THEN 1 ELSE 0 END) AS preparing_orders,
                   SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed_orders,
                   COALESCE(SUM(CASE WHEN status = 'COMPLETED' THEN total_paise ELSE 0 END), 0)
                       AS completed_revenue_paise
                   FROM orders"""
            ).fetchone()
        return jsonify(
            {
                "total_orders": row["total_orders"],
                "pending_orders": row["pending_orders"] or 0,
                "preparing_orders": row["preparing_orders"] or 0,
                "completed_orders": row["completed_orders"] or 0,
                "completed_revenue": rupees(row["completed_revenue_paise"]),
            }
        )

    def process_front_order(order_number: str, action: str):
        with queue.lock:
            conn = connect(current_app.config["DATABASE"])
            try:
                conn.execute("BEGIN IMMEDIATE")
                order = _fetch_order(conn, order_number)
                if not order:
                    conn.rollback()
                    return _json_error("That order could not be found.", 404)
                try:
                    if action == "start":
                        queue.start_preparing(order_number, order["status"])
                    else:
                        queue.assert_front(order_number)
                        if order["status"] != "PREPARING":
                            raise QueueError(
                                "Only the preparing front order can be completed."
                            )
                except QueueError as error:
                    conn.rollback()
                    return _json_error(str(error), 409)

                timestamp = _now()
                if action == "start":
                    conn.execute(
                        """UPDATE orders SET status = 'PREPARING', started_at = ?
                           WHERE id = ? AND status = 'PENDING'""",
                        (timestamp, order["id"]),
                    )
                else:
                    conn.execute(
                        """UPDATE orders SET status = 'COMPLETED', completed_at = ?
                           WHERE id = ? AND status = 'PREPARING'""",
                        (timestamp, order["id"]),
                    )
                if conn.total_changes == 0:
                    conn.rollback()
                    return _json_error("The order changed. Refresh and try again.", 409)
                conn.commit()
                if action == "complete":
                    queue.complete_order(order_number, "PREPARING")
                updated = _fetch_order(conn, order_number)
                response = serialize_order(conn, updated, include_private=True)
            except sqlite3.Error:
                conn.rollback()
                app.logger.exception("Could not update order status")
                return _json_error("The order status could not be updated.", 500)
            finally:
                conn.close()
        return jsonify(response)

    @app.post("/api/admin/orders/<order_number>/start")
    @_require_admin
    def start_order(order_number: str):
        return process_front_order(order_number.strip().upper(), "start")

    @app.post("/api/admin/orders/<order_number>/complete")
    @_require_admin
    def complete_order(order_number: str):
        return process_front_order(order_number.strip().upper(), "complete")

    return app


app = create_app()


if __name__ == "__main__":
    port = int(__import__("os").environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
