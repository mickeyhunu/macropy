from __future__ import annotations

from datetime import datetime


def log(message: str) -> None:
    """프로세스 공통 로그 출력."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")
