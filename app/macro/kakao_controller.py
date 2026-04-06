import os
import time
import subprocess
from pathlib import Path
from datetime import datetime
from enum import Enum, auto

import requests
import pyautogui
import pyperclip


# =========================================================
# 기본 설정값
# =========================================================

# API 서버 주소
# - 메신저봇이 INFO_ORDER에 주문을 넣고
# - 이 워커가 claim / done / fail API를 호출해서 작업을 처리함
API_URL = "http://localhost:3001"

# 카카오톡 실행 파일 후보 경로
# - 여러 PC 환경에서 경로가 다를 수 있으므로 후보를 여러 개 둠
KAKAO_PATHS = [
    r"D:\KakaoTalk\KakaoTalk.exe",
    r"C:\Program Files\Kakao\KakaoTalk\KakaoTalk.exe",
    str(Path.home() / "AppData/Local/Kakao/KakaoTalk/KakaoTalk.exe"),
]

# 카카오톡 UI 인식용 이미지
CHAT_TAB_IMAGE = "assets/images/chat_tab.png"              # 좌측 "채팅" 탭 이미지
MESSAGE_INPUT_IMAGE = "assets/images/message_input.png"    # 메시지 입력창 이미지

# storeNo -> 해당 웨톡방 이미지 파일
# - 방 검색 후 검색 결과에서 이 이미지를 찾아 더블클릭하여 진입
ROOM_IMAGE_MAP = {
    1: "assets/images/room_wteam_hajun.png",
    2: "assets/images/room_wteam_hajun.png",
    3: "assets/images/room_wteam_hajun.png",
    4: "assets/images/room_wteam_hajun.png",
    5: "assets/images/room_wteam_hajun.png",
    6: "assets/images/room_wteam_hajun.png",
}

# storeNo -> 카카오톡 검색용 방 이름
# - INFO_ORDER의 storeNo를 이용하여 어느 웨톡방으로 들어갈지 결정
TARGET_ROOM_NAME_MAP = {
    1: "달토웨톡",
    2: "엘리트웨톡",
    3: "디저트웨톡",
    4: "유앤미웨톡",
    5: "도파민웨톡",
    6: "제우스웨톡",
}

# 이미지 탐색 신뢰도
CONFIDENCE = 0.82

# pyautogui 기본 설정
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.2


# =========================================================
# 공통 로그 함수
# =========================================================
def log(msg: str):
    """
    로그 출력용 함수
    - 현재 시각과 함께 로그를 출력해
      어떤 step에서 멈췄는지 추적하기 쉽게 함
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# =========================================================
# 단순 타이머 클래스
# - C# 예시의 ElapsedTimer 역할
# - 각 step에서 timeout 관리용으로 사용
# =========================================================
class ElapsedTimer:
    def __init__(self, timeout_sec: float):
        self.timeout_sec = timeout_sec
        self.started_at = None

    def start(self):
        """타이머 시작"""
        self.started_at = time.time()

    def reset(self):
        """타이머 초기화"""
        self.started_at = None

    def is_started(self):
        """타이머 시작 여부"""
        return self.started_at is not None

    def is_elapsed(self):
        """
        timeout이 지났는지 확인
        - 아직 start() 안 했으면 False
        """
        if self.started_at is None:
            return False
        return (time.time() - self.started_at) >= self.timeout_sec

    def elapsed(self):
        """경과 시간 반환"""
        if self.started_at is None:
            return 0
        return time.time() - self.started_at


# =========================================================
# 카카오톡 관련 기본 동작 함수들
# - 기존 테스트 코드의 함수들을 재사용한 형태
# =========================================================
def launch_kakao():
    """
    카카오톡 실행
    - 실행 파일 후보 경로를 순서대로 검사한 뒤
      존재하는 첫 번째 경로를 실행
    """
    for path in KAKAO_PATHS:
        if os.path.exists(path):
            log(f"카카오톡 실행: {path}")
            subprocess.Popen([path])
            return True

    log("카카오톡 실행 파일을 찾지 못했습니다.")
    return False


def focus_kakao_window():
    """
    카카오톡 창 활성화
    - 최소화 상태면 복원
    - 활성화 후 약간 대기
    """
    wins = pyautogui.getWindowsWithTitle("카카오톡")
    if not wins:
        log("카카오톡 창을 찾지 못했습니다.")
        return False

    win = wins[0]
    try:
        if win.isMinimized:
            win.restore()

        win.activate()
        time.sleep(1)
        return True

    except Exception as e:
        log(f"카카오톡 창 활성화 실패: {e}")
        return False


def center_of_image(image_path: str, confidence=CONFIDENCE, timeout=5, region=None):
    """
    화면에서 특정 이미지의 중심 좌표를 찾는 함수

    동작:
    - timeout 동안 반복 탐색
    - 찾으면 좌표 반환
    - 못 찾으면 None 반환

    용도:
    - 채팅 탭 찾기
    - 채팅방 이미지 찾기
    - 메시지 입력창 찾기
    """
    start = time.time()

    while time.time() - start < timeout:
        try:
            pos = pyautogui.locateCenterOnScreen(
                image_path,
                confidence=confidence,
                region=region
            )
            if pos:
                return pos

        except Exception as e:
            log(f"이미지 탐색 오류 ({image_path}): {e}")
            return None

        time.sleep(0.4)

    return None


def click_image(image_path: str, confidence=CONFIDENCE, timeout=5, region=None, clicks=1):
    """
    화면에서 이미지를 찾아 클릭하는 함수

    동작:
    1. center_of_image()로 좌표 찾기
    2. 찾으면 클릭 수행
    3. 못 찾으면 False
    """
    pos = center_of_image(image_path, confidence=confidence, timeout=timeout, region=region)
    if not pos:
        return False

    pyautogui.click(pos.x, pos.y, clicks=clicks, interval=0.15)
    time.sleep(0.6)
    return True


def go_to_chat_tab():
    """
    카카오톡 좌측의 '채팅' 탭으로 이동

    이유:
    - 검색 대상이 친구/오픈채팅 등 다른 탭이면
      원하는 웨톡방 검색이 불안정해질 수 있으므로
      항상 채팅 탭으로 맞춰놓고 시작
    """
    log("채팅 탭 이동 시도")
    ok = click_image(CHAT_TAB_IMAGE, timeout=5)

    if ok:
        log("채팅 탭 이동 성공")
        return True

    log("채팅 탭 이미지를 찾지 못했습니다.")
    return False


def paste_text(text: str):
    """
    텍스트 붙여넣기
    - 한글 입력 안정성을 위해 직접 타이핑 대신 클립보드 사용
    """
    pyperclip.copy(text)
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.3)


def clear_search_box():
    """
    검색창 비우기
    - Ctrl+A 대신 backspace 반복 사용
    - 기존 테스트 코드 스타일 유지
    """
    for _ in range(20):
        pyautogui.press("backspace")
        time.sleep(0.02)

    time.sleep(0.2)


def search_room(room_name: str):
    """
    채팅방 검색 단계

    동작:
    1. Ctrl+F로 검색창 열기
    2. 기존 검색어 지우기
    3. 대상 방 이름 붙여넣기

    주의:
    - 이 단계는 '검색어를 넣는 것'만 담당
    - 실제 검색 결과에서 방을 클릭하는 건 다음 step에서 처리
    """
    log(f"채팅방 검색 시작: {room_name}")

    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.7)

    clear_search_box()
    paste_text(room_name)
    time.sleep(1.2)

    return True


def open_room_by_image(room_image: str):
    """
    검색 결과 영역에서 방 이미지를 찾아 더블클릭

    이유:
    - 검색어만 입력했다고 방에 들어간 것이 아님
    - 실제 검색 결과 리스트에서 원하는 방을 클릭해야 함
    """
    room_pos = center_of_image(room_image, timeout=4)

    if room_pos:
        pyautogui.click(room_pos.x, room_pos.y)
        time.sleep(0.2)
        pyautogui.click(room_pos.x, room_pos.y)
        time.sleep(1.2)
        log("채팅방 클릭 성공")
        return True

    log("검색 결과에서 채팅방 이미지를 찾지 못했습니다.")
    return False


def click_message_input():
    """
    메시지 입력창 클릭

    이유:
    - 채팅방에 들어가도 포커스가 입력창에 바로 안 갈 수 있음
    - 입력 placeholder 이미지를 찾아 실제 입력 영역 쪽을 클릭해 포커스를 유도
    """
    log("메시지 입력창 탐색 시작")

    pos = center_of_image(MESSAGE_INPUT_IMAGE, timeout=5)
    if not pos:
        log("메시지 입력 이미지를 찾지 못했습니다.")
        return False

    # placeholder 중앙보다 약간 오른쪽/아래를 눌러 실제 입력 영역 포커스
    click_x = pos.x + 80
    click_y = pos.y + 10

    pyautogui.click(click_x, click_y)
    time.sleep(0.3)
    pyautogui.click(click_x, click_y)
    time.sleep(0.5)

    log("메시지 입력창 클릭 성공")
    return True


def send_message(message: str):
    """
    메시지 전송

    동작:
    1. 메시지 텍스트 붙여넣기
    2. Enter 입력
    3. 짧게 대기

    주의:
    - 입력창 포커스는 이전 step(CHECK_INPUT)에서 맞춰놓는 구조
    """
    log(f"메시지 전송: {message}")

    paste_text(message)
    time.sleep(0.2)
    pyautogui.press("enter")
    time.sleep(0.8)

    log("메시지 전송 완료")
    return True


# =========================================================
# 메시지 조합
# INFO_ORDER 데이터(roomNo, sendMsg, waiterName)를 실제 전송문으로 조합
# =========================================================
def build_message(job: dict) -> str:
    """
    실제 카카오톡으로 보낼 메시지 조합

    예:
    roomNo = 403
    sendMsg = 얼재요
    waiterName = 하준

    결과:
    403 얼재요
    @하준
    """
    first_line = f"{job['roomNo']} {job['sendMsg']}"
    waiter_name = str(job.get("waiterName") or "").strip()

    if waiter_name:
        return f"{first_line}\n@{waiter_name}"

    return first_line


# =========================================================
# API 호출 공통 함수
# =========================================================
def api_post(path: str, payload=None):
    """
    서버 POST 호출 공통 함수
    - claim / done / fail 처리에 사용
    """
    url = f"{API_URL}{path}"
    r = requests.post(url, json=payload or {}, timeout=5)
    r.raise_for_status()
    return r.json()


# =========================================================
# STEP 정의
# - C# 예시처럼 현재 작업 상태를 명확히 분리
# =========================================================
class STEP(Enum):
    IDLE = auto()            # 대기 상태
    CLAIM_JOB = auto()       # READY 작업 1건 점유
    CHECK_KAKAO = auto()     # 카카오톡 실행 여부 확인
    FOCUS_KAKAO = auto()     # 카카오톡 창 활성화
    GO_CHAT_TAB = auto()     # 채팅 탭 이동
    PREPARE_MESSAGE = auto() # storeNo -> 방 이름/이미지, 전송문 준비
    SEARCH_ROOM = auto()     # 채팅방 검색어 입력
    OPEN_ROOM = auto()       # 검색 결과에서 실제 방 열기
    CHECK_INPUT = auto()     # 입력창 포커스 확인
    SEND_MESSAGE = auto()    # 메시지 전송
    MARK_DONE = auto()       # 성공 완료 처리 API 호출
    MARK_FAIL = auto()       # 실패 처리 API 호출
    CLEANUP = auto()         # 내부 변수/타이머 정리


# =========================================================
# 메인 프로세스 클래스
# - 예전 C#의 ProcessReadyGlassGap 같은 역할
# =========================================================
class OrderMacroProcess:
    def __init__(self):
        # 프로세스 실행 여부
        self.is_run = False

        # 1사이클 완료 여부
        self.is_complete = False

        # 현재 step
        self.step = STEP.IDLE

        # 직전 step
        # - step 변경 시 로그를 1번만 찍기 위해 사용
        self.prev_step = None

        # 현재 처리 중인 작업 데이터
        self.job = None

        # 현재 작업에서 사용할 대상방 이름 / 이미지 / 메시지
        self.target_room_name = ""
        self.target_room_image = ""
        self.message_text = ""

        # 실패 사유
        self.fail_reason = ""

        # 각 단계별 timeout 관리용 타이머
        self.claim_wait_timer = ElapsedTimer(2.0)
        self.kakao_wait_timer = ElapsedTimer(10.0)
        self.room_wait_timer = ElapsedTimer(8.0)
        self.input_wait_timer = ElapsedTimer(5.0)
        self.send_wait_timer = ElapsedTimer(3.0)

    def start(self):
        """
        프로세스 시작
        - 처음 시작하면 CLAIM_JOB부터 수행
        """
        if self.is_run:
            return

        self.is_run = True
        self.is_complete = False
        self.step = STEP.CLAIM_JOB

    def stop(self):
        """
        프로세스 정지
        """
        self.is_run = False
        self.is_complete = False
        self.step = STEP.IDLE

    def set_fail(self, reason: str):
        """
        실패 사유를 저장하고 MARK_FAIL step으로 이동
        - 각 단계에서 예외 조건이 생기면 이 함수로 통일
        """
        self.fail_reason = reason
        self.step = STEP.MARK_FAIL

    def claim_job(self):
        """
        READY 작업 1건 점유
        서버에서:
        - 가장 오래된 READY 1건을 PROCESSING으로 바꾸고
        - 해당 행을 반환해준다는 전제
        """
        try:
            res = api_post("/api/info-order/claim")
            return res.get("data")
        except Exception as e:
            log(f"작업 claim 실패: {e}")
            return None

    def mark_done(self):
        """
        현재 작업 완료 처리
        - 서버에 orderNo done API 호출
        """
        if not self.job:
            return False

        try:
            api_post(f"/api/info-order/{self.job['orderNo']}/done")
            return True
        except Exception as e:
            log(f"완료 처리 실패: {e}")
            return False

    def mark_fail(self):
        """
        현재 작업 실패 처리
        - 서버에 fail API 호출
        - 서버는 여기서 READY 복귀 / FAILED 처리 등을 담당
        """
        if not self.job:
            return False

        try:
            api_post(
                f"/api/info-order/{self.job['orderNo']}/fail",
                {"reason": self.fail_reason}
            )
            return True
        except Exception as e:
            log(f"실패 처리 실패: {e}")
            return False

    def prepare_job_data(self):
        """
        현재 작업 데이터로부터
        - 대상 카카오톡 방 이름
        - 대상 방 이미지 파일
        - 실제 전송 메시지
        를 준비하는 단계
        """
        store_no = int(self.job["storeNo"])

        self.target_room_name = TARGET_ROOM_NAME_MAP.get(store_no, "")
        self.target_room_image = ROOM_IMAGE_MAP.get(store_no, "")
        self.message_text = build_message(self.job)

        # 방 이름이 없으면 어디로 보낼지 몰라서 실패
        if not self.target_room_name:
            self.set_fail(f"storeNo 대상방 이름 없음: {store_no}")
            return False

        # 방 이미지가 없으면 검색 결과 클릭 기준이 없어 실패
        if not self.target_room_image:
            self.set_fail(f"storeNo 대상방 이미지 없음: {store_no}")
            return False

        return True

    def run_once(self):
        """
        프로세스 1회 실행
        - 이 함수는 while True 루프에서 반복 호출됨
        - 매 호출마다 현재 step에 해당하는 동작만 수행
        - 조건 만족 시 다음 step으로 넘어감

        즉:
        C#의 switch(step) 구조를 Python으로 옮긴 핵심 부분
        """
        if not self.is_run:
            return

        # step이 바뀌었을 때만 로그 출력
        if self.step != self.prev_step:
            log(f"[STEP] {self.step.name}")
            self.prev_step = self.step

        # 아무 작업도 안 하는 대기 상태
        if self.step == STEP.IDLE:
            return

        # =====================================================
        # 1. 작업 1건 점유
        # =====================================================
        elif self.step == STEP.CLAIM_JOB:
            self.job = self.claim_job()

            # 작업이 없으면 잠시 쉬고 그대로 CLAIM_JOB 유지
            if not self.job:
                time.sleep(2.0)
                return

            log(f"작업 수신: orderNo={self.job['orderNo']}, roomNo={self.job['roomNo']}")
            self.step = STEP.CHECK_KAKAO

        # =====================================================
        # 2. 카카오톡 실행 여부 확인
        # =====================================================
        elif self.step == STEP.CHECK_KAKAO:
            wins = pyautogui.getWindowsWithTitle("카카오톡")

            # 이미 실행 중이면 다음 단계
            if wins:
                self.step = STEP.FOCUS_KAKAO
                return

            # 실행 안 되어 있으면 실행 시도
            if not launch_kakao():
                self.set_fail("카카오톡 실행 실패")
                return

            # 실행 후 창이 뜰 때까지 기다리기 위한 타이머 시작
            self.kakao_wait_timer.start()
            self.step = STEP.FOCUS_KAKAO

        # =====================================================
        # 3. 카카오톡 창 활성화
        # =====================================================
        elif self.step == STEP.FOCUS_KAKAO:
            if focus_kakao_window():
                self.step = STEP.GO_CHAT_TAB
                return

            # 너무 오래 활성화 실패 시 timeout
            if self.kakao_wait_timer.is_started() and self.kakao_wait_timer.is_elapsed():
                self.set_fail("카카오톡 창 활성화 timeout")
                return

            time.sleep(0.8)

        # =====================================================
        # 4. 채팅 탭으로 이동
        # =====================================================
        elif self.step == STEP.GO_CHAT_TAB:
            if not go_to_chat_tab():
                self.set_fail("채팅 탭 이동 실패")
                return

            self.step = STEP.PREPARE_MESSAGE

        # =====================================================
        # 5. 현재 작업의 메타데이터 준비
        # =====================================================
        elif self.step == STEP.PREPARE_MESSAGE:
            if not self.prepare_job_data():
                return

            self.step = STEP.SEARCH_ROOM

        # =====================================================
        # 6. 채팅방 검색어 입력
        # =====================================================
        elif self.step == STEP.SEARCH_ROOM:
            if not search_room(self.target_room_name):
                self.set_fail("채팅방 검색 실패")
                return

            # 검색 결과 로딩/표시 대기용 타이머 시작
            self.room_wait_timer.start()
            self.step = STEP.OPEN_ROOM

        # =====================================================
        # 7. 검색 결과에서 실제 채팅방 열기
        # =====================================================
        elif self.step == STEP.OPEN_ROOM:
            if open_room_by_image(self.target_room_image):
                self.step = STEP.CHECK_INPUT
                return

            # 제한 시간 내 못 찾으면 실패
            if self.room_wait_timer.is_elapsed():
                self.set_fail(f"채팅방 열기 timeout: {self.target_room_name}")
                return

            time.sleep(0.5)

        # =====================================================
        # 8. 메시지 입력창 포커스 맞추기
        # =====================================================
        elif self.step == STEP.CHECK_INPUT:
            if click_message_input():
                self.step = STEP.SEND_MESSAGE
                return

            # 처음 진입 시 타이머 시작
            if not self.input_wait_timer.is_started():
                self.input_wait_timer.start()

            # 입력창을 끝내 못 찾으면 실패
            if self.input_wait_timer.is_elapsed():
                self.set_fail("입력창 탐색 timeout")
                return

            time.sleep(0.4)

        # =====================================================
        # 9. 메시지 전송
        # =====================================================
        elif self.step == STEP.SEND_MESSAGE:
            if send_message(self.message_text):
                self.send_wait_timer.start()
                self.step = STEP.MARK_DONE
                return

            self.set_fail("메시지 전송 실패")

        # =====================================================
        # 10. 서버에 완료 처리
        # =====================================================
        elif self.step == STEP.MARK_DONE:
            if self.mark_done():
                self.step = STEP.CLEANUP
                return

            # 완료 처리 API 응답이 너무 늦으면 실패 전환
            if self.send_wait_timer.is_elapsed():
                self.set_fail("완료 처리 API timeout")
                return

            time.sleep(0.3)

        # =====================================================
        # 11. 서버에 실패 처리
        # =====================================================
        elif self.step == STEP.MARK_FAIL:
            self.mark_fail()
            self.step = STEP.CLEANUP

        # =====================================================
        # 12. 내부 상태 정리 후 다음 작업으로 복귀
        # =====================================================
        elif self.step == STEP.CLEANUP:
            self.job = None
            self.target_room_name = ""
            self.target_room_image = ""
            self.message_text = ""
            self.fail_reason = ""

            # 타이머 초기화
            self.claim_wait_timer.reset()
            self.kakao_wait_timer.reset()
            self.room_wait_timer.reset()
            self.input_wait_timer.reset()
            self.send_wait_timer.reset()

            # 다음 작업을 계속 처리하기 위해 다시 CLAIM_JOB으로 복귀
            self.step = STEP.CLAIM_JOB


# =========================================================
# 메인 루프
# =========================================================
def main():
    """
    메인 실행 함수

    동작:
    - 프로세스 시작
    - 무한 루프에서 run_once() 반복 호출
    - 각 호출마다 현재 step 1회분만 진행
    """
    process = OrderMacroProcess()
    process.start()

    while True:
        try:
            process.run_once()
            time.sleep(0.1)

        except KeyboardInterrupt:
            log("사용자 종료")
            break

        except Exception as e:
            log(f"메인 루프 예외: {e}")
            time.sleep(1.0)


if __name__ == "__main__":
    main()