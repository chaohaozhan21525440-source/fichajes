import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "local_store.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pending_checkins (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                nfc_uid          TEXT NOT NULL,
                device_id        TEXT NOT NULL,
                detected_at      TEXT NOT NULL,
                idempotency_key  TEXT NOT NULL UNIQUE,
                synced           INTEGER NOT NULL DEFAULT 0,
                created_at       TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)


def add_pending(
    nfc_uid: str,
    device_id: str,
    detected_at: datetime,
    idempotency_key: str | None = None,
) -> str:
    if idempotency_key is None:
        idempotency_key = str(uuid.uuid4())
    with _conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO pending_checkins
               (nfc_uid, device_id, detected_at, idempotency_key)
               VALUES (?, ?, ?, ?)""",
            (nfc_uid, device_id, detected_at.isoformat(), idempotency_key),
        )
    return idempotency_key


def get_pending() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM pending_checkins WHERE synced = 0 ORDER BY detected_at ASC"
        ).fetchall()
    return [dict(r) for r in rows]


def mark_synced(idempotency_key: str) -> None:
    with _conn() as conn:
        conn.execute(
            "UPDATE pending_checkins SET synced = 1 WHERE idempotency_key = ?",
            (idempotency_key,),
        )


def pending_count() -> int:
    with _conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM pending_checkins WHERE synced = 0"
        ).fetchone()[0]
