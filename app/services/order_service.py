from __future__ import annotations

from app.db.order_repository import OrderRepository


class OrderService:
    def __init__(self, repo: OrderRepository | None = None):
        self.repo = repo or OrderRepository()

    def claim_job(self):
        return self.repo.claim_next_order()

    def mark_done(self, order_no: int) -> None:
        self.repo.mark_done(order_no)

    def mark_fail(self, order_no: int, reason: str) -> None:
        self.repo.mark_fail(order_no, reason)
