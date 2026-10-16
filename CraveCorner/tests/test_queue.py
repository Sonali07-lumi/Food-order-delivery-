import unittest

from queue_manager import OrderQueue, QueueError


class OrderQueueTests(unittest.TestCase):
    def setUp(self):
        self.queue = OrderQueue()
        self.queue.restore_pending_orders(["CC-2026-0001", "CC-2026-0002"])

    def test_orders_are_processed_fifo_and_new_items_join_rear(self):
        self.queue.enqueue_order("CC-2026-0003")
        self.assertEqual(self.queue.get_next_order(), "CC-2026-0001")
        self.queue.start_preparing("CC-2026-0001", "PENDING")
        self.queue.complete_order("CC-2026-0001", "PREPARING")
        self.assertEqual(
            self.queue.get_queue_status()["active"],
            ["CC-2026-0002", "CC-2026-0003"],
        )

    def test_later_order_cannot_start_or_complete_first(self):
        with self.assertRaises(QueueError):
            self.queue.start_preparing("CC-2026-0002", "PENDING")
        with self.assertRaises(QueueError):
            self.queue.complete_order("CC-2026-0002", "PREPARING")
        self.assertEqual(self.queue.get_next_order(), "CC-2026-0001")

    def test_invalid_status_transitions_are_rejected(self):
        with self.assertRaises(QueueError):
            self.queue.start_preparing("CC-2026-0001", "PREPARING")
        with self.assertRaises(QueueError):
            self.queue.complete_order("CC-2026-0001", "PENDING")

    def test_restore_keeps_pending_and_preparing_orders_in_arrival_order(self):
        self.queue.restore_pending_orders(["CC-2026-0007", "CC-2026-0008"])
        self.assertEqual(self.queue.get_next_order(), "CC-2026-0007")
        self.assertEqual(
            self.queue.get_queue_status(lambda order: "PREPARING")["next_action"],
            "COMPLETE_ORDER",
        )


if __name__ == "__main__":
    unittest.main()
