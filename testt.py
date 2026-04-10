import time
import win32gui
import win32api
import keyboard  # 추가

def inspect_mouse_point():
    print("S 누르면 좌표 출력 / ESC 누르면 종료")

    while True:
        if keyboard.is_pressed('s'):
            x, y = win32api.GetCursorPos()
            hwnd = win32gui.WindowFromPoint((x, y))

            print("좌표:", (x, y))
            print("HWND:", hwnd)
            print("Class:", win32gui.GetClassName(hwnd))
            print("Text:", win32gui.GetWindowText(hwnd))
            print("Rect:", win32gui.GetWindowRect(hwnd))
            print("-" * 30)

            time.sleep(0.3)  # 중복 출력 방지

        if keyboard.is_pressed('esc'):
            print("종료")
            break

        time.sleep(0.05)


inspect_mouse_point()