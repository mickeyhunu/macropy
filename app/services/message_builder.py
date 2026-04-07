from __future__ import annotations


def build_message(job: dict) -> str:
    """주문 데이터를 실제 카카오 발송 포맷 문자열로 변환."""
    first_line = f"{job['roomNo']} {job['sendMsg']}"
    waiter_name = str(job.get("waiterName") or "").strip()
    if waiter_name:
        return f"{first_line}\n@{waiter_name}"
    return first_line
