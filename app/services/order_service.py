from __future__ import annotations

from app.db.order_repository import OrderRepository


class OrderService:
    """프로세스 레이어와 저장소 레이어 사이의 얇은 서비스 계층."""

    def __init__(self, repo: OrderRepository | None = None):
        self.repo = repo or OrderRepository()

    def expire_stale_jobs(self) -> int:
        return self.repo.expire_stale_orders()

    def claim_job(self):
        return self.repo.claim_next_order()

    def mark_done(self, order_no: int) -> None:
        self.repo.mark_done(order_no)

    def mark_fail(self, order_no: int, reason: str) -> None:
        self.repo.mark_fail(order_no, reason)
