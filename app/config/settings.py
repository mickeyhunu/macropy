from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_env_file() -> None:
    """프로젝트 루트(.env) 값을 읽어 process 환경변수에 기본 주입."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            os.environ.setdefault(key, value)


_load_env_file()


@dataclass(frozen=True)
class Settings:
    """실행 시점 설정 집합(환경변수 기반)."""

    mysql_host: str = os.getenv("CHATBOT_MYSQL_HOST", os.getenv("DB_HOST", "localhost"))
    mysql_port: int = int(os.getenv("CHATBOT_MYSQL_PORT", os.getenv("DB_PORT", "3306")))
    mysql_user: str = os.getenv("CHATBOT_MYSQL_USER", os.getenv("DB_USER", "root"))
    mysql_password: str = os.getenv("CHATBOT_MYSQL_PASSWORD", os.getenv("DB_PASSWORD", ""))
    mysql_database: str = os.getenv("CHATBOT_MYSQL_DATABASE", os.getenv("DB_NAME", "chatBot_DB"))

    poll_interval_sec: float = float(os.getenv("POLL_INTERVAL_SEC", "1.5"))
    max_try_count: int = int(os.getenv("MAX_TRY_COUNT", "10"))

    status_ready: str = os.getenv("STATUS_READY", "READY")
    status_processing: str = os.getenv("STATUS_PROCESSING", "PROCESSING")
    status_done: str = os.getenv("STATUS_DONE", "DONE")
    status_fail: str = os.getenv("STATUS_FAIL", "FAIL")

    kakao_focus_retry_interval_sec: float = float(os.getenv("KAKAO_FOCUS_RETRY_INTERVAL_SEC", "0.5"))
    kakao_recovery_click_x: int = int(os.getenv("KAKAO_RECOVERY_CLICK_X", "-1"))
    kakao_recovery_click_y: int = int(os.getenv("KAKAO_RECOVERY_CLICK_Y", "-1"))

    kakao_paths: tuple[str, ...] = (
        os.getenv("KAKAO_PATH_1", r"D:\KakaoTalk\KakaoTalk.exe"),
        os.getenv("KAKAO_PATH_2", r"C:\Program Files\Kakao\KakaoTalk.exe"),
        os.getenv("KAKAO_PATH_3", r"C:\Program Files (x86)\Kakao\KakaoTalk.exe"),
        os.getenv("KAKAO_PATH_4", r"C:\Program Files (x86)\Kakao\KakaoTalk\KakaoTalk.exe"),
        os.getenv("KAKAO_PATH_5", str(Path.home() / "AppData/Local/Kakao/KakaoTalk/KakaoTalk.exe")),
    )


settings = Settings()
