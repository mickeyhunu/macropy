from __future__ import annotations

import time

try:
    import msvcrt
except ImportError:  # non-Windows 환경에서는 ESC 감지 비활성화
    msvcrt = None

from app.config.room_map import TARGET_ROOM_NAME_MAP
from app.config.settings import settings
from app.core.logger import log
from app.core.timer import ElapsedTimer
from app.macro.kakao_controller import KakaoController
from app.process.steps import Step
from app.services.message_builder import build_message
from app.services.order_service import OrderService


class OrderMacroProcess:
    """주문 1건을 카카오톡 발송까지 처리하는 상태 머신."""

    def __init__(self):
        # 외부 의존성(DB/카카오 제어기)을 초기화한다.
        self.service = OrderService()
        self.kakao = KakaoController()

        # step은 현재 상태, prev_step은 상태 변경 로그 중복 출력 방지용이다.
        self.step = Step.CLAIM_JOB
        self.prev_step = None

        # 현재 처리 중인 주문 컨텍스트.
        self.job = None
        self.target_room_name = ""
        self.message_text = ""
        self.fail_reason = ""
        self.stop_requested = False

        # UI 자동화는 실패/지연이 잦아 단계별 timeout 타이머를 분리해 둔다.
        self.kakao_wait_timer = ElapsedTimer(10.0)
        self.room_wait_timer = ElapsedTimer(8.0)
        self.input_wait_timer = ElapsedTimer(5.0)
        self.done_wait_timer = ElapsedTimer(3.0)

    def set_fail(self, reason: str) -> None:
        self.fail_reason = reason
        log(f"[오류] 단계={self.step.label}, 사유={reason}")
        self.step = Step.MARK_FAIL

    def prepare_job_data(self) -> bool:
        """storeNo 기반 방 정보와 최종 발송 메시지를 만든다."""
        store_no = int(self.job["storeNo"])
        self.target_room_name = TARGET_ROOM_NAME_MAP.get(store_no, "")
        self.message_text = build_message(self.job)

        if not self.target_room_name:
            self.set_fail(f"storeNo={store_no}에 매핑된 대상 채팅방 이름이 없습니다.")
            return False
        return True

    def cleanup(self) -> None:
        """한 건 처리 후 컨텍스트/타이머를 초기화하고 다음 주문 대기 상태로 복귀."""
        self.job = None
        self.target_room_name = ""
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
        # 중간 단계에서 즉시 종료하면 주문 상태가 꼬일 수 있으므로,
        # 안전 지점(CLAIM_JOB)에서만 프로세스를 종료한다.
        return self.stop_requested and self.step == Step.CLAIM_JOB and self.job is None

    def recover_to_ready(self, exc: Exception) -> None:
        """메인 루프 예외 시 현재 주문을 READY로 되돌리고 안전 복구."""
        if not self.job:
            self.step = Step.CLAIM_JOB
            return

        order_no = self.job["orderNo"]
        reason = f"비정상 종료 복구: {exc}"
        try:
            self.service.mark_fail(order_no, reason)
            log(f"[복구] orderNo={order_no} 주문 상태를 READY로 롤백했습니다.")
        except Exception as rollback_exc:
            log(f"[복구 오류] orderNo={order_no} 롤백 실패, 오류={rollback_exc}")
        finally:
            self.cleanup()

    def run_once(self):
        """상태 머신을 한 tick 실행한다."""
        if self.step != self.prev_step:
            log(f"[단계 전환] {self.step.label} ({self.step.name})")
            self.prev_step = self.step

        if self.step == Step.CLAIM_JOB:
            # 1) DB에서 처리할 주문을 선점(claim)한다.
            if self.stop_requested:
                return
            self.job = self.service.claim_job()
            if not self.job:
                time.sleep(settings.poll_interval_sec)
                return
            log(f"[작업 수신] orderNo={self.job['orderNo']}, roomNo={self.job['roomNo']}")
            self.step = Step.CHECK_KAKAO
            return

        if self.step == Step.CHECK_KAKAO:
            # 2) 카카오톡 프로세스가 없으면 실행한다.
            if not self.kakao.launch_if_needed():
                self.set_fail("카카오톡 실행에 실패했습니다.")
                return
            self.kakao_wait_timer.start()
            self.step = Step.FOCUS_KAKAO
            return

        if self.step == Step.FOCUS_KAKAO:
            # 3) 카카오톡 창이 포커스될 때까지 짧게 재시도한다.
            if self.kakao.focus_window():
                self.step = Step.GO_CHAT_TAB
                return
            if self.kakao_wait_timer.is_elapsed():
                self.set_fail("카카오톡 창 활성화 대기 시간이 초과되었습니다.")
                return
            time.sleep(0.5)
            return

        if self.step == Step.GO_CHAT_TAB:
            # 4) 채팅 탭으로 이동.
            if not self.kakao.go_to_chat_tab():
                self.set_fail("채팅 탭 이동에 실패했습니다.")
                return
            self.step = Step.PREPARE_MESSAGE
            return

        if self.step == Step.PREPARE_MESSAGE:
            # 5) room 이미지/이름 매핑과 메시지 본문을 준비한다.
            if self.prepare_job_data():
                self.step = Step.SEARCH_ROOM
            return

        if self.step == Step.SEARCH_ROOM:
            # 6) 채팅방 검색창에 대상 방 이름 입력.
            self.kakao.search_room(self.target_room_name)
            self.room_wait_timer.start()
            self.step = Step.OPEN_ROOM
            return

        if self.step == Step.OPEN_ROOM:
            # 7) 검색 결과에서 Enter로 방을 열고, 실제 진입 완료까지 대기한다.
            if self.kakao.open_room_by_search_result():
                self.step = Step.CHECK_INPUT
                return
            if self.room_wait_timer.is_elapsed():
                self.set_fail(f"채팅방 열기 대기 시간이 초과되었습니다. 대상방={self.target_room_name}")
                return
            time.sleep(0.4)
            return

        if self.step == Step.CHECK_INPUT:
            # 8) 메시지 입력창이 보일 때까지 확인.
            if self.kakao.ensure_message_input():
                self.step = Step.SEND_MESSAGE
                return
            if not self.input_wait_timer.is_started():
                self.input_wait_timer.start()
            if self.input_wait_timer.is_elapsed():
                self.set_fail("메시지 입력창 탐색 대기 시간이 초과되었습니다.")
                return
            time.sleep(0.3)
            return

        if self.step == Step.SEND_MESSAGE:
            # 9) 메시지 붙여넣기 + Enter 전송.
            if self.kakao.send_message(self.message_text):
                self.step = Step.MARK_DONE
                self.done_wait_timer.start()
            else:
                self.set_fail("메시지 전송에 실패했습니다.")
            return

        if self.step == Step.MARK_DONE:
            # 10) DB 상태를 DONE으로 반영.
            try:
                self.service.mark_done(self.job["orderNo"])
                log(f"[완료] orderNo={self.job['orderNo']} 주문을 DONE으로 반영했습니다.")
                self.step = Step.CLEANUP
            except Exception as exc:
                if self.done_wait_timer.is_elapsed():
                    self.set_fail(f"완료 처리 대기 시간이 초과되었습니다. 오류={exc}")
            return

        if self.step == Step.MARK_FAIL:
            # 실패 시 해당 주문을 READY로 되돌려 재처리 대상에 남긴다.
            try:
                if self.job:
                    self.service.mark_fail(self.job["orderNo"], self.fail_reason)
                    log(
                        f"[실패 처리] orderNo={self.job['orderNo']} 주문을 READY로 롤백했습니다. "
                        f"사유={self.fail_reason}"
                    )
            finally:
                self.step = Step.CLEANUP
            return

        if self.step == Step.CLEANUP:
            self.cleanup()


def main():
    """프로세스 메인 루프(ESC/KeyboardInterrupt 기반 안전 종료 지원)."""
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
            log(f"[메인 루프 오류] {exc}")
            process.recover_to_ready(exc)
            time.sleep(1)
