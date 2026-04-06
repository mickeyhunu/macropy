from __future__ import annotations

from contextlib import contextmanager

from app.config.settings import settings

try:
    import pyodbc
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "pyodbc가 필요합니다. 다음 명령으로 의존성을 설치해 주세요: "
        "python -m pip install -r requirements.txt"
    ) from exc


def build_conn_str() -> str:
    return (
        f"DRIVER={{{settings.db_driver}}};"
        f"SERVER={settings.db_host},{settings.db_port};"
        f"DATABASE={settings.db_name};"
        f"UID={settings.db_user};"
        f"PWD={settings.db_password};"
        f"Encrypt={settings.db_encrypt};"
        "TrustServerCertificate=yes;"
    )


@contextmanager
def get_connection():
    try:
        conn = pyodbc.connect(build_conn_str(), autocommit=False)
    except pyodbc.Error as exc:
        raise RuntimeError(
            "DB 연결에 실패했습니다. pyodbc 설치 여부와 ODBC Driver(예: ODBC Driver 18 for SQL Server) "
            "설치를 확인해 주세요."
        ) from exc

    try:
        yield conn
    finally:
        conn.close()
