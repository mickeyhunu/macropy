from __future__ import annotations


def build_message(job: dict) -> str:
    first_line = f"{job['roomNo']} {job['sendMsg']}"
    waiter_name = str(job.get("waiterName") or "").strip()
    if waiter_name:
        return f"{first_line}\n@{waiter_name}"
    return first_line
