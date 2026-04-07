from __future__ import annotations

import time


class ElapsedTimer:
    """단순 timeout 판정을 위한 경과시간 타이머."""

    def __init__(self, timeout_sec: float):
        self.timeout_sec = timeout_sec
        self.started_at: float | None = None

    def start(self) -> None:
        self.started_at = time.time()

    def reset(self) -> None:
        self.started_at = None

    def is_started(self) -> bool:
        return self.started_at is not None

    def is_elapsed(self) -> bool:
        return self.started_at is not None and (time.time() - self.started_at) >= self.timeout_sec
