from __future__ import annotations

import os
import subprocess
import time

import pyautogui
import pyperclip

from app.config.settings import settings
from app.core.logger import log
from app.macro.image_locator import center_of_image, click_image

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.2


class KakaoController:
    def launch_if_needed(self) -> bool:
        if pyautogui.getWindowsWithTitle("카카오톡"):
            return True

        for path in settings.kakao_paths:
            if os.path.exists(path):
                log(f"카카오톡 실행: {path}")
                subprocess.Popen([path])
                time.sleep(1.0)
                return True

        log("카카오톡 실행 파일을 찾지 못했습니다.")
        return False

    def focus_window(self) -> bool:
        wins = pyautogui.getWindowsWithTitle("카카오톡")
        if not wins:
            return False

        win = wins[0]
        if win.isMinimized:
            win.restore()
        win.activate()
        time.sleep(0.7)
        return True

    def go_to_chat_tab(self) -> bool:
        return click_image(settings.chat_tab_image, timeout=5)

    def search_room(self, room_name: str) -> bool:
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.6)
        self._clear_search_box()
        self._paste_text(room_name)
        time.sleep(1.0)
        return True

    def open_room_by_image(self, room_image_path: str) -> bool:
        room_pos = center_of_image(room_image_path, timeout=4)
        if not room_pos:
            return False
        pyautogui.click(room_pos.x, room_pos.y)
        time.sleep(0.2)
        pyautogui.click(room_pos.x, room_pos.y)
        time.sleep(1.0)
        return True

    def ensure_message_input(self) -> bool:
        pos = center_of_image(settings.message_input_image, timeout=5)
        if not pos:
            return False
        pyautogui.click(pos.x + 80, pos.y + 10)
        time.sleep(0.2)
        pyautogui.click(pos.x + 80, pos.y + 10)
        time.sleep(0.3)
        return True

    def send_message(self, message: str) -> bool:
        self._paste_text(message)
        pyautogui.press("enter")
        time.sleep(0.5)
        return True

    @staticmethod
    def _paste_text(text: str) -> None:
        pyperclip.copy(text)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)

    @staticmethod
    def _clear_search_box() -> None:
        for _ in range(20):
            pyautogui.press("backspace")
            time.sleep(0.02)
