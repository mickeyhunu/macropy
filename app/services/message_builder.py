from __future__ import annotations


def build_message(job: dict) -> str:
    """주문 데이터를 실제 카카오 발송 포맷 문자열로 변환."""
    first_name = str(job.get("senderName") or "").strip()
    second_line = f"{job['roomNo']} {job['sendMsg']}"
    waiter_name = str(job.get("waiterName") or "").strip()

    lines = [line for line in (first_name, second_line) if line]
    if waiter_name:
        lines.append(f"@{waiter_name}")
    return "\n".join(lines)
