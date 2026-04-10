from enum import Enum, auto


class Step(Enum):
    """주문 발송 상태 머신 단계."""

    CLAIM_JOB = auto()
    CHECK_KAKAO = auto()
    FOCUS_KAKAO = auto()
    PREPARE_MESSAGE = auto()
    SEARCH_ROOM = auto()
    OPEN_ROOM = auto()
    CHECK_INPUT = auto()
    SEND_MESSAGE = auto()
    MARK_DONE = auto()
    MARK_FAIL = auto()
    CLEANUP = auto()

    @property
    def label(self) -> str:
        """로그 출력용 한글 단계명."""
        return {
            Step.CLAIM_JOB: "주문 선점",
            Step.CHECK_KAKAO: "카카오톡 실행 확인",
            Step.FOCUS_KAKAO: "카카오톡 창 활성화",
            Step.PREPARE_MESSAGE: "발송 데이터 준비",
            Step.SEARCH_ROOM: "채팅방 검색",
            Step.OPEN_ROOM: "채팅방 열기",
            Step.CHECK_INPUT: "입력창 확인",
            Step.SEND_MESSAGE: "메시지 전송",
            Step.MARK_DONE: "완료 상태 반영",
            Step.MARK_FAIL: "실패 상태 반영",
            Step.CLEANUP: "정리 및 다음 주문 대기",
        }[self]
