from __future__ import annotations

import os
import subprocess
import time
from typing import Any

import pyautogui
import pyperclip
import win32api
import win32con
import win32gui

from app.config.settings import settings
from app.core.logger import log
from app.macro.image_locator import click_image

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
            self._click_recovery_point()
            time.sleep(0.4)
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
            log(f"카카오톡 창 활성화 실패: {exc} (복구 클릭 후 재시도)")
            self._click_recovery_point()
            time.sleep(0.4)
            return self._retry_activate_first_window()

    def _retry_activate_first_window(self) -> bool:
        wins = self._find_kakao_windows()
        if not wins:
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
            log(f"카카오톡 창 활성화 재시도 실패: {exc}")
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
        # 검색창 핸들을 직접 찾아 대상 채팅방 이름을 입력한다.
        hwnd_kakao = win32gui.FindWindow(None, "카카오톡")
        if not hwnd_kakao:
            return False

        hwnd1 = win32gui.FindWindowEx(hwnd_kakao, None, "EVA_ChildWindow", None)
        hwnd2 = win32gui.FindWindowEx(hwnd1, None, "EVA_Window", None)
        hwnd3 = win32gui.FindWindowEx(hwnd1, hwnd2, "EVA_Window", None)
        hwnd_edit = win32gui.FindWindowEx(hwnd3, None, "Edit", None)
        if not hwnd_edit:
            return False

        win32api.SendMessage(hwnd_edit, win32con.WM_SETTEXT, 0, room_name)
        time.sleep(1.0)
        return True

    def open_room_by_enter(self) -> bool:
        # 검색 결과의 첫 번째 채팅방을 Enter로 연다.
        hwnd_kakao = win32gui.FindWindow(None, "카카오톡")
        if not hwnd_kakao:
            return False

        hwnd1 = win32gui.FindWindowEx(hwnd_kakao, None, "EVA_ChildWindow", None)
        hwnd2 = win32gui.FindWindowEx(hwnd1, None, "EVA_Window", None)
        hwnd3 = win32gui.FindWindowEx(hwnd1, hwnd2, "EVA_Window", None)
        hwnd_edit = win32gui.FindWindowEx(hwnd3, None, "Edit", None)
        if not hwnd_edit:
            return False

        self._send_enter(hwnd_edit)
        time.sleep(1.0)
        return True

    def is_room_opened(self) -> bool:
        # 포그라운드 창의 메시지 입력창 핸들로 채팅방 진입 여부를 판단한다.
        hwnd_main = win32gui.GetForegroundWindow()
        if not hwnd_main:
            return False
        hwnd_edit = win32gui.FindWindowEx(hwnd_main, None, "RICHEDIT50W", None)
        return bool(hwnd_edit)

    def open_room_by_search_result(self) -> bool:
        # Enter 입력 후 실제로 채팅방이 열렸는지 확인한다.
        self.open_room_by_enter()
        return self.is_room_opened()

    def ensure_message_input(self) -> bool:
        # 포그라운드 창의 메시지 입력창 핸들 존재 여부를 확인한다.
        hwnd_main = win32gui.GetForegroundWindow()
        if not hwnd_main:
            return False
        hwnd_edit = win32gui.FindWindowEx(hwnd_main, None, "RICHEDIT50W", None)
        return bool(hwnd_edit)

    def send_message(self, message: str) -> bool:
        # 활성화된 채팅방의 메시지 입력창 핸들을 찾아 붙여넣기/Enter로 전송한다.
        hwnd_main = win32gui.GetForegroundWindow()
        if not hwnd_main:
            return False

        hwnd_edit = win32gui.FindWindowEx(hwnd_main, None, "RICHEDIT50W", None)
        if not hwnd_edit:
            return False

        win32gui.SetForegroundWindow(hwnd_main)
        time.sleep(0.1)
        win32gui.SetFocus(hwnd_edit)
        time.sleep(0.1)

        self._paste_text(message)
        self._send_enter(hwnd_edit)
        time.sleep(0.3)
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

    @staticmethod
    def _send_enter(hwnd: int) -> None:
        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
        time.sleep(0.01)
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)

    @staticmethod
    def _click_recovery_point() -> None:
        # env에 좌표가 있으면 우선 사용하고, 없으면 기본 좌측 중앙으로 복구 클릭한다.
        width, height = pyautogui.size()
        configured_x = settings.kakao_recovery_click_x
        configured_y = settings.kakao_recovery_click_y

        if configured_x >= 0 and configured_y >= 0:
            target_x = min(max(1, configured_x), max(1, width - 1))
            target_y = min(max(1, configured_y), max(1, height - 1))
            source = "env"
        else:
            target_x = 20
            target_y = max(1, height // 2)
            source = "default"

        pyautogui.click(target_x, target_y)
        log(f"카카오톡 창 탐색 복구 클릭 수행({source}): x={target_x}, y={target_y}, 화면={width}x{height}")
