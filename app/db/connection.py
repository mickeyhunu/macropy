from __future__ import annotations

from contextlib import contextmanager

from app.config.settings import settings

try:
    import pyodbc
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("pyodbc가 필요합니다. requirements.txt를 설치해 주세요.") from exc


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
    conn = pyodbc.connect(build_conn_str(), autocommit=False)
    try:
        yield conn
    finally:
        conn.close()
