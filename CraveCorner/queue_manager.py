"""In-memory FIFO queue for the educational, single-process CraveCorner app."""

from collections import deque
from threading import RLock
from typing import Callable, Iterable


class QueueError(ValueError):
    """Raised when an order cannot take its requested FIFO transition."""


class OrderQueue:
    """Maintain active order numbers in arrival order.

    SQLite remains the durable source of truth. On startup the queue is
    reconstructed from active database rows, including PREPARING orders.
    """

    def __init__(self) -> None:
        self._orders: deque[str] = deque()
        self._lock = RLock()

    @property
    def lock(self) -> RLock:
        """Shared lock used around queue and database state transitions."""
        return self._lock

    def enqueue_order(self, order_id: str) -> None:
        with self._lock:
            if order_id in self._orders:
                raise QueueError(f"Order {order_id} is already in the queue.")
            self._orders.append(order_id)

    def get_next_order(self) -> str | None:
        with self._lock:
            return self._orders[0] if self._orders else None

    def start_preparing(self, order_id: str, current_status: str) -> None:
        with self._lock:
            self.assert_front(order_id)
            if current_status != "PENDING":
                raise QueueError("Only a pending front order can be started.")

    def complete_order(self, order_id: str, current_status: str) -> None:
        with self._lock:
            self.assert_front(order_id)
            if current_status != "PREPARING":
                raise QueueError("Only a preparing front order can be completed.")
            self._orders.popleft()

    def assert_front(self, order_id: str) -> None:
        with self._lock:
            self._require_front(order_id)

    def get_queue_status(
        self, status_for: Callable[[str], str | None] | None = None
    ) -> dict[str, object]:
        with self._lock:
            active = list(self._orders)
            front = active[0] if active else None
            status = status_for(front) if front and status_for else None
            if status == "PENDING":
                action = "START_PREPARING"
            elif status == "PREPARING":
                action = "COMPLETE_ORDER"
            else:
                action = None
            return {"active": active, "front": front, "next_action": action}

    def restore_pending_orders(self, order_numbers: Iterable[str]) -> None:
        with self._lock:
            self._orders = deque(order_numbers)

    def _require_front(self, order_id: str) -> None:
        if not self._orders:
            raise QueueError("The active order queue is empty.")
        if self._orders[0] != order_id:
            raise QueueError(
                f"FIFO order violation: {self._orders[0]} must be processed first."
            )
