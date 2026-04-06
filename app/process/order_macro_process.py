from __future__ import annotations

import time

try:
    import msvcrt
except ImportError:  # non-Windows 환경에서는 ESC 감지 비활성화
    msvcrt = None

from app.config.room_map import ROOM_IMAGE_MAP, TARGET_ROOM_NAME_MAP
from app.config.settings import settings
from app.core.logger import log
from app.core.timer import ElapsedTimer
from app.macro.kakao_controller import KakaoController
from app.process.steps import Step
from app.services.message_builder import build_message
from app.services.order_service import OrderService


class OrderMacroProcess:
    def __init__(self):
        self.service = OrderService()
        self.kakao = KakaoController()

        self.step = Step.CLAIM_JOB
        self.prev_step = None

        self.job = None
        self.target_room_name = ""
        self.target_room_image = ""
        self.message_text = ""
        self.fail_reason = ""
        self.stop_requested = False

        self.kakao_wait_timer = ElapsedTimer(10.0)
        self.room_wait_timer = ElapsedTimer(8.0)
        self.input_wait_timer = ElapsedTimer(5.0)
        self.done_wait_timer = ElapsedTimer(3.0)

    def set_fail(self, reason: str) -> None:
        self.fail_reason = reason
        self.step = Step.MARK_FAIL

    def prepare_job_data(self) -> bool:
        store_no = int(self.job["storeNo"])
        self.target_room_name = TARGET_ROOM_NAME_MAP.get(store_no, "")
        self.target_room_image = ROOM_IMAGE_MAP.get(store_no, "")
        self.message_text = build_message(self.job)

        if not self.target_room_name:
            self.set_fail(f"storeNo 대상방 이름 없음: {store_no}")
            return False
        if not self.target_room_image:
            self.set_fail(f"storeNo 대상방 이미지 없음: {store_no}")
            return False
        return True

    def cleanup(self) -> None:
        self.job = None
        self.target_room_name = ""
        self.target_room_image = ""
        self.message_text = ""
        self.fail_reason = ""
        self.kakao_wait_timer.reset()
        self.room_wait_timer.reset()
        self.input_wait_timer.reset()
        self.done_wait_timer.reset()
        self.step = Step.CLAIM_JOB

    def request_stop(self) -> None:
        if self.stop_requested:
            return
        self.stop_requested = True
        log("ESC 감지: 현재 작업 완료 후 종료합니다.")

    def can_shutdown(self) -> bool:
        return self.stop_requested and self.step == Step.CLAIM_JOB and self.job is None

    def recover_to_ready(self, exc: Exception) -> None:
        if not self.job:
            self.step = Step.CLAIM_JOB
            return

        order_no = self.job["orderNo"]
        reason = f"비정상 종료 복구: {exc}"
        try:
            self.service.mark_fail(order_no, reason)
            log(f"예외 복구: orderNo={order_no} 상태를 READY로 롤백")
        except Exception as rollback_exc:
            log(f"예외 복구 실패: orderNo={order_no}, err={rollback_exc}")
        finally:
            self.cleanup()

    def run_once(self):
        if self.step != self.prev_step:
            log(f"[STEP] {self.step.name}")
            self.prev_step = self.step

        if self.step == Step.CLAIM_JOB:
            if self.stop_requested:
                return
            self.job = self.service.claim_job()
            if not self.job:
                time.sleep(settings.poll_interval_sec)
                return
            log(f"작업 수신: orderNo={self.job['orderNo']}, roomNo={self.job['roomNo']}")
            self.step = Step.CHECK_KAKAO
            return

        if self.step == Step.CHECK_KAKAO:
            if not self.kakao.launch_if_needed():
                self.set_fail("카카오톡 실행 실패")
                return
            self.kakao_wait_timer.start()
            self.step = Step.FOCUS_KAKAO
            return

        if self.step == Step.FOCUS_KAKAO:
            if self.kakao.focus_window():
                self.step = Step.GO_CHAT_TAB
                return
            if self.kakao_wait_timer.is_elapsed():
                self.set_fail("카카오톡 창 활성화 timeout")
                return
            time.sleep(0.5)
            return

        if self.step == Step.GO_CHAT_TAB:
            if not self.kakao.go_to_chat_tab():
                self.set_fail("채팅 탭 이동 실패")
                return
            self.step = Step.PREPARE_MESSAGE
            return

        if self.step == Step.PREPARE_MESSAGE:
            if self.prepare_job_data():
                self.step = Step.SEARCH_ROOM
            return

        if self.step == Step.SEARCH_ROOM:
            self.kakao.search_room(self.target_room_name)
            self.room_wait_timer.start()
            self.step = Step.OPEN_ROOM
            return

        if self.step == Step.OPEN_ROOM:
            if self.kakao.open_room_by_image(self.target_room_image):
                self.step = Step.CHECK_INPUT
                return
            if self.room_wait_timer.is_elapsed():
                self.set_fail(f"채팅방 열기 timeout: {self.target_room_name}")
                return
            time.sleep(0.4)
            return

        if self.step == Step.CHECK_INPUT:
            if self.kakao.ensure_message_input():
                self.step = Step.SEND_MESSAGE
                return
            if not self.input_wait_timer.is_started():
                self.input_wait_timer.start()
            if self.input_wait_timer.is_elapsed():
                self.set_fail("입력창 탐색 timeout")
                return
            time.sleep(0.3)
            return

        if self.step == Step.SEND_MESSAGE:
            if self.kakao.send_message(self.message_text):
                self.step = Step.MARK_DONE
                self.done_wait_timer.start()
            else:
                self.set_fail("메시지 전송 실패")
            return

        if self.step == Step.MARK_DONE:
            try:
                self.service.mark_done(self.job["orderNo"])
                self.step = Step.CLEANUP
            except Exception as exc:
                if self.done_wait_timer.is_elapsed():
                    self.set_fail(f"완료 처리 timeout: {exc}")
            return

        if self.step == Step.MARK_FAIL:
            try:
                if self.job:
                    self.service.mark_fail(self.job["orderNo"], self.fail_reason)
            finally:
                self.step = Step.CLEANUP
            return

        if self.step == Step.CLEANUP:
            self.cleanup()


def main():
    process = OrderMacroProcess()
    while True:
        try:
            if msvcrt and msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b"\x1b":
                    process.request_stop()

            process.run_once()
            if process.can_shutdown():
                log("요청에 따라 정상 종료합니다.")
                break
            time.sleep(0.1)
        except KeyboardInterrupt:
            process.request_stop()
        except Exception as exc:
            log(f"메인 루프 예외: {exc}")
            process.recover_to_ready(exc)
            time.sleep(1)
