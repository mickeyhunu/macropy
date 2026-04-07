from __future__ import annotations

from contextlib import contextmanager

from app.config.settings import settings

try:
    import pymysql
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "pymysql이 필요합니다. 다음 명령으로 의존성을 설치해 주세요: "
        "python -m pip install -r requirements.txt"
    ) from exc


@contextmanager
def get_connection():
    """MySQL 커넥션 컨텍스트 매니저.

    with 블록을 벗어나면 항상 연결을 닫는다.
    """
    try:
        conn = pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            charset="utf8mb4",
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except pymysql.MySQLError as exc:
        raise RuntimeError(
            "MySQL 연결에 실패했습니다. CHATBOT_MYSQL_HOST/PORT/USER/PASSWORD/DATABASE "
            "환경변수와 네트워크 접근 권한을 확인해 주세요."
        ) from exc

    try:
        yield conn
    finally:
        conn.close()
