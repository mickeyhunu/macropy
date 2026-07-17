from __future__ import annotations

from typing import Any

from app.config.settings import settings
from app.db.connection import get_connection


class OrderRepository:
    """INFO_ORDER 테이블 접근 레이어."""

    def claim_next_order(self) -> dict[str, Any] | None:
        # READY 상태 주문 1건을 락으로 선점한다.
        select_query = """
        SELECT orderNo, storeNo, roomNo, senderName, sendMsg, waiterName
          FROM INFO_ORDER
         WHERE status = %s
           AND COALESCE(tryCount, 0) < %s
         ORDER BY orderNo ASC
         LIMIT 1
         FOR UPDATE SKIP LOCKED
        """
        # 선점된 주문을 PROCESSING으로 전환하고 시도 횟수를 누적한다.
        update_query = """
        UPDATE INFO_ORDER
           SET status = %s,
               tryCount = tryCount + 1,
               lastTriedAt = NOW()
         WHERE orderNo = %s
        """
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(select_query, (settings.status_ready, settings.max_try_count))
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
                "senderName": row["senderName"],
                "sendMsg": row["sendMsg"],
                "waiterName": row["waiterName"],
            }

    def expire_stale_orders(self) -> int:
        """오래된 READY 주문은 발송 대상에서 제외한다.

        MAX_ORDER_AGE_MINUTES가 0 이하이면 만료 처리를 비활성화한다.
        createdAt 기준으로 오래된 주문을 FAIL 상태로 전환해 claim 대상에서 빼고,
        다음 READY 주문이 있으면 즉시 처리될 수 있게 한다.
        """
        if settings.max_order_age_minutes <= 0:
            return 0

        query = """
        UPDATE INFO_ORDER
           SET status = %s,
               lastTriedAt = NOW()
         WHERE status = %s
           AND createdAt < DATE_SUB(NOW(), INTERVAL %s MINUTE)
        """
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                query,
                (settings.status_fail, settings.status_ready, settings.max_order_age_minutes),
            )
            affected = cur.rowcount
            conn.commit()
            return affected

    def mark_done(self, order_no: int) -> None:
        # 전송 완료 시 DONE으로 마킹.
        query = """
        UPDATE INFO_ORDER
           SET status = %s
         WHERE orderNo = %s
        """
        with get_connection() as conn:
            conn.cursor().execute(query, (settings.status_done, order_no))
            conn.commit()

    def mark_fail(self, order_no: int, reason: str) -> None:
        # 실패 시 READY로 복귀시켜 다음 poll 주기에 재시도되도록 한다.
        # reason은 현재 스키마에 저장하지 않지만 호출부에서 로그/추적 용도로 전달한다.
        query = """
        UPDATE INFO_ORDER
           SET status = %s,
               lastTriedAt = NOW()
         WHERE orderNo = %s
        """
        with get_connection() as conn:
            conn.cursor().execute(query, (settings.status_ready, order_no))
            conn.commit()
