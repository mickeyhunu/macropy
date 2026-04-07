from __future__ import annotations

import time

import pyautogui

from app.config.settings import settings


def center_of_image(image_path: str, timeout: float = 5.0, region=None):
    """timeout 동안 화면에서 이미지 중심 좌표를 탐색한다."""
    start = time.time()
    while time.time() - start < timeout:
        pos = pyautogui.locateCenterOnScreen(
            image_path,
            confidence=settings.image_confidence,
            region=region,
        )
        if pos:
            return pos
        time.sleep(0.4)
    return None


def click_image(image_path: str, timeout: float = 5.0, clicks: int = 1, region=None) -> bool:
    """이미지를 찾으면 클릭하고 True, 찾지 못하면 False."""
    pos = center_of_image(image_path, timeout=timeout, region=region)
    if not pos:
        return False
    pyautogui.click(pos.x, pos.y, clicks=clicks, interval=0.15)
    time.sleep(0.6)
    return True
