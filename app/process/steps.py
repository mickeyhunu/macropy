from enum import Enum, auto


class Step(Enum):
    CLAIM_JOB = auto()
    CHECK_KAKAO = auto()
    FOCUS_KAKAO = auto()
    GO_CHAT_TAB = auto()
    PREPARE_MESSAGE = auto()
    SEARCH_ROOM = auto()
    OPEN_ROOM = auto()
    CHECK_INPUT = auto()
    SEND_MESSAGE = auto()
    MARK_DONE = auto()
    MARK_FAIL = auto()
    CLEANUP = auto()
