import time
import win32con
import win32api
import win32gui

# 대상 채팅방 이름
TARGET_ROOM = "독고테스트"
SEND_MSG = "테스트 @희망"


# 엔터 입력
def send_enter(hwnd):
    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
    time.sleep(0.01)
    win32api.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)

def send_enter_real():
    win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
    time.sleep(0.05)
    win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)

# 채팅방 열기 (검색 → 엔터)
def open_chatroom(chatroom_name):
    hwndKakao = win32gui.FindWindow(None, "카카오톡")

    hwnd1 = win32gui.FindWindowEx(hwndKakao, None, "EVA_ChildWindow", None)
    hwnd2 = win32gui.FindWindowEx(hwnd1, None, "EVA_Window", None)
    hwnd3 = win32gui.FindWindowEx(hwnd1, hwnd2, "EVA_Window", None)
    hwndEdit = win32gui.FindWindowEx(hwnd3, None, "Edit", None)

    # 검색창에 채팅방 이름 입력
    win32api.SendMessage(hwndEdit, win32con.WM_SETTEXT, 0, chatroom_name)
    time.sleep(1)

    # 엔터 → 채팅방 열기
    send_enter(hwndEdit)
    time.sleep(1)


# 메시지 전송
def send_text(chatroom_name, text):
    hwndMain = win32gui.FindWindow(None, chatroom_name)
    hwndEdit = win32gui.FindWindowEx(hwndMain, None, "RICHEDIT50W", None)

    # 메시지 입력
    time.sleep(1)
    win32api.SendMessage(hwndEdit, win32con.WM_SETTEXT, 0, text)
    time.sleep(1)

    # 엔터 → 전송
    send_enter_real()
    time.sleep(1)
    send_enter_real()

def main():
    print("카카오톡 자동 전송 시작")

    # 채팅방 열기
    open_chatroom(TARGET_ROOM)

    # 메시지 전송
    send_text(TARGET_ROOM, SEND_MSG)

    print("전송 완료")


if __name__ == "__main__":
    main()