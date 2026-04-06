from __future__ import annotations

from typing import Any

from app.config.settings import settings
from app.db.connection import get_connection


class OrderRepository:
    """INFO_ORDER 테이블 접근 레이어."""

    def claim_next_order(self) -> dict[str, Any] | None:
        query = """
        ;WITH next_item AS (
            SELECT TOP 1 *
            FROM INFO_ORDER WITH (UPDLOCK, READPAST, ROWLOCK)
            WHERE status = ?
            ORDER BY orderNo ASC
        )
        UPDATE next_item
           SET status = ?,
               startedAt = GETDATE()
        OUTPUT INSERTED.orderNo,
               INSERTED.storeNo,
               INSERTED.roomNo,
               INSERTED.sendMsg,
               INSERTED.waiterName;
        """
        with get_connection() as conn:
            cur = conn.cursor()
            row = cur.execute(query, settings.status_ready, settings.status_processing).fetchone()
            conn.commit()
            if not row:
                return None
            return {
                "orderNo": row.orderNo,
                "storeNo": row.storeNo,
                "roomNo": row.roomNo,
                "sendMsg": row.sendMsg,
                "waiterName": row.waiterName,
            }

    def mark_done(self, order_no: int) -> None:
        query = """
        UPDATE INFO_ORDER
           SET status = ?,
               completedAt = GETDATE(),
               failReason = NULL
         WHERE orderNo = ?
        """
        with get_connection() as conn:
            conn.cursor().execute(query, settings.status_done, order_no)
            conn.commit()

    def mark_fail(self, order_no: int, reason: str) -> None:
        query = """
        UPDATE INFO_ORDER
           SET status = ?,
               failReason = ?,
               completedAt = GETDATE()
         WHERE orderNo = ?
        """
        with get_connection() as conn:
            conn.cursor().execute(query, settings.status_fail, reason, order_no)
            conn.commit()
