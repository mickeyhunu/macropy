from __future__ import annotations

from typing import Any

from app.config.settings import settings
from app.db.connection import get_connection


class OrderRepository:
    """INFO_ORDER 테이블 접근 레이어."""

    def claim_next_order(self) -> dict[str, Any] | None:
        select_query = """
        SELECT orderNo, storeNo, roomNo, sendMsg, waiterName
          FROM INFO_ORDER
         WHERE status = %s
         ORDER BY orderNo ASC
         LIMIT 1
         FOR UPDATE SKIP LOCKED
        """
        update_query = """
        UPDATE INFO_ORDER
           SET status = %s,
               startedAt = NOW()
         WHERE orderNo = %s
        """
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(select_query, (settings.status_ready,))
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return None

            cur.execute(update_query, (settings.status_processing, row["orderNo"]))
            conn.commit()
            return {
                "orderNo": row["orderNo"],
                "storeNo": row["storeNo"],
                "roomNo": row["roomNo"],
                "sendMsg": row["sendMsg"],
                "waiterName": row["waiterName"],
            }

    def mark_done(self, order_no: int) -> None:
        query = """
        UPDATE INFO_ORDER
           SET status = %s,
               completedAt = NOW(),
               failReason = NULL
         WHERE orderNo = %s
        """
        with get_connection() as conn:
            conn.cursor().execute(query, (settings.status_done, order_no))
            conn.commit()

    def mark_fail(self, order_no: int, reason: str) -> None:
        query = """
        UPDATE INFO_ORDER
           SET status = %s,
               failReason = %s,
               completedAt = NOW()
         WHERE orderNo = %s
        """
        with get_connection() as conn:
            conn.cursor().execute(query, (settings.status_fail, reason, order_no))
            conn.commit()
