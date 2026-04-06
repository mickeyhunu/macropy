from __future__ import annotations

import time

import pyautogui

from app.config.settings import settings


def center_of_image(image_path: str, timeout: float = 5.0, region=None):
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
    pos = center_of_image(image_path, timeout=timeout, region=region)
    if not pos:
        return False
    pyautogui.click(pos.x, pos.y, clicks=clicks, interval=0.15)
    time.sleep(0.6)
    return True
