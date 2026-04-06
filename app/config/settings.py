from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    mysql_host: str = os.getenv("CHATBOT_MYSQL_HOST", os.getenv("DB_HOST", "localhost"))
    mysql_port: int = int(os.getenv("CHATBOT_MYSQL_PORT", os.getenv("DB_PORT", "3306")))
    mysql_user: str = os.getenv("CHATBOT_MYSQL_USER", os.getenv("DB_USER", "root"))
    mysql_password: str = os.getenv("CHATBOT_MYSQL_PASSWORD", os.getenv("DB_PASSWORD", ""))
    mysql_database: str = os.getenv("CHATBOT_MYSQL_DATABASE", os.getenv("DB_NAME", "chatBot_DB"))

    poll_interval_sec: float = float(os.getenv("POLL_INTERVAL_SEC", "1.5"))

    status_ready: str = os.getenv("STATUS_READY", "READY")
    status_processing: str = os.getenv("STATUS_PROCESSING", "PROCESSING")
    status_done: str = os.getenv("STATUS_DONE", "DONE")
    status_fail: str = os.getenv("STATUS_FAIL", "FAIL")

    chat_tab_image: str = os.getenv("CHAT_TAB_IMAGE", "assets/images/chat_tab.png")
    message_input_image: str = os.getenv("MESSAGE_INPUT_IMAGE", "assets/images/message_input.png")

    image_confidence: float = float(os.getenv("IMAGE_CONFIDENCE", "0.82"))

    kakao_paths: tuple[str, ...] = (
        os.getenv("KAKAO_PATH_1", r"D:\KakaoTalk\KakaoTalk.exe"),
        os.getenv("KAKAO_PATH_2", r"C:\Program Files\Kakao\KakaoTalk.exe"),
        os.getenv("KAKAO_PATH_3", str(Path.home() / "AppData/Local/Kakao/KakaoTalk/KakaoTalk.exe")),
    )


settings = Settings()
