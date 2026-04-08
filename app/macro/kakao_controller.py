from __future__ import annotations

import os
import subprocess
import time
from typing import Any

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
        if self._find_kakao_windows():
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
        wins = self._find_kakao_windows()
        if not wins:
            visible_titles = [w.title for w in pyautogui.getAllWindows() if getattr(w, "title", "").strip()]
            if visible_titles:
                sample = ", ".join(visible_titles[:5])
                log(f"현재 감지된 창 제목(샘플): {sample}")
            log("카카오톡 창 탐색 실패: 전체 창 목록에서 카카오톡/카카오/KakaoTalk 제목을 찾지 못했습니다.")
            return False

        win = wins[0]
        try:
            if win.isMinimized:
                win.restore()
                time.sleep(0.2)
            win.activate()
            time.sleep(0.7)
            return True
        except Exception as exc:
            log(f"카카오톡 창 활성화 실패: {exc}")
            return False

    @staticmethod
    def _find_kakao_windows() -> list[Any]:
        """카카오톡 창 제목 변형(국문/영문/공백 포함)을 허용해 후보를 찾는다."""
        # 1) pyautogui의 제목 포함 검색(빠른 경로)
        wins: list[Any] = []
        for keyword in ("카카오톡", "카카오", "KakaoTalk", "Kakao"):
            wins.extend(pyautogui.getWindowsWithTitle(keyword))

        if wins:
            return wins

        # 2) getAllWindows()로 제목 변형까지 보수적으로 탐색
        candidates: list[Any] = []
        for win in pyautogui.getAllWindows():
            title = (getattr(win, "title", "") or "").strip().lower()
            if not title:
                continue
            normalized = title.replace(" ", "")
            if any(token in normalized for token in ("카카오톡", "카카오", "kakaotalk", "kakao")):
                candidates.append(win)
        return candidates

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

    def open_room_by_enter(self) -> bool:
        # 검색 결과의 첫 번째 채팅방을 Enter로 연다.
        pyautogui.press("enter")
        time.sleep(0.5)
        return True

    def is_room_opened(self) -> bool:
        # 메시지 입력창 이미지로 채팅방 진입 여부를 판단한다.
        return bool(center_of_image(settings.message_input_image, timeout=1.0))

    def open_room_by_search_result(self) -> bool:
        # Enter 입력 후 실제로 채팅방이 열렸는지 확인한다.
        self.open_room_by_enter()
        return self.is_room_opened()

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
        # 전송 이후 검색창을 열어 검색어를 비우고 채팅 탭으로 복귀한다.
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.6)
        self._clear_search_box()
        return self.go_to_chat_tab()

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
