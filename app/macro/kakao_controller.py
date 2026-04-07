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
    """카카오톡 UI 자동화를 담당하는 어댑터."""

    def launch_if_needed(self) -> bool:
        # 이미 실행 중이면 재실행하지 않는다.
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
        # 카카오톡 메인 창 활성화.
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
        # 탭 전환은 이미지 매칭으로 수행한다.
        return click_image(settings.chat_tab_image, timeout=5)

    def search_room(self, room_name: str) -> bool:
        # Ctrl+F 검색창을 열고 대상 채팅방 이름을 입력한다.
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.6)
        self._clear_search_box()
        self._paste_text(room_name)
        time.sleep(1.0)
        return True

    def open_room_by_image(self, room_image_path: str) -> bool:
        # 목록에서 방 이름 이미지를 찾아 더블클릭(2회 클릭)으로 진입.
        room_pos = center_of_image(room_image_path, timeout=4)
        if not room_pos:
            return False
        pyautogui.click(room_pos.x, room_pos.y)
        time.sleep(0.2)
        pyautogui.click(room_pos.x, room_pos.y)
        time.sleep(1.0)
        return True

    def ensure_message_input(self) -> bool:
        # 검색창 포커스가 남아있는 경우를 대비해 backspace로 정리 후
        # 입력창 이미지를 찾아 클릭한다.
        self._clear_search_box()
        pos = center_of_image(settings.message_input_image, timeout=5)
        if not pos:
            return False
        pyautogui.click(pos.x + 80, pos.y + 10)
        time.sleep(0.2)
        pyautogui.click(pos.x + 80, pos.y + 10)
        time.sleep(0.3)
        return True

    def send_message(self, message: str) -> bool:
        # 붙여넣기 후 Enter 2회로 전송 안정성을 높인다.
        self._paste_text(message)
        pyautogui.press("enter")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.3)
        pyautogui.press("esc")
        time.sleep(0.5)
        return True

    @staticmethod
    def _paste_text(text: str) -> None:
        # 한글 입력 안정성을 위해 키 타이핑 대신 클립보드 붙여넣기를 사용.
        pyperclip.copy(text)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)

    @staticmethod
    def _clear_search_box() -> None:
        # 현재 포커스가 검색창인 경우 기존 검색어를 제거하기 위한 방어 루틴.
        for _ in range(20):
            pyautogui.press("backspace")
            time.sleep(0.02)
