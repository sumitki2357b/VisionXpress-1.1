from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from backend.config import DB_PATH, DEMO_USERS


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def get_connection():
    connection = _connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    with get_connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                department TEXT NOT NULL UNIQUE,
                user_id TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS maintenance_requests (
                request_id TEXT PRIMARY KEY,
                department TEXT NOT NULL,
                source_system TEXT NOT NULL,
                status TEXT NOT NULL,
                block_id TEXT,
                rejection_reason TEXT,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS coa_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                planning_date TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                uploaded_by TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS blocks (
                block_id TEXT PRIMARY KEY,
                planning_date TEXT NOT NULL,
                section_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                priority TEXT NOT NULL,
                priority_score REAL NOT NULL,
                status TEXT NOT NULL,
                coordination INTEGER NOT NULL,
                existing_block INTEGER NOT NULL,
                block_calendar_id TEXT,
                data_json TEXT NOT NULL,
                rejection_reason TEXT,
                modification_reason TEXT,
                approved_by TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                department TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                block_id TEXT,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                details_json TEXT,
                created_at TEXT NOT NULL
            );
            """
        )

        for department, details in DEMO_USERS.items():
            db.execute(
                """
                INSERT OR IGNORE INTO users
                (department, user_id, password_hash, role)
                VALUES (?, ?, ?, ?)
                """,
                (
                    department,
                    details["user_id"],
                    hash_password(details["password"]),
                    details["role"],
                ),
            )


def create_session(user_row: sqlite3.Row) -> str:
    token = secrets.token_urlsafe(32)
    with get_connection() as db:
        db.execute(
            "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_row["id"], utc_now()),
        )
    return token


def get_user_by_credentials(department: str, user_id: str, password: str):
    with get_connection() as db:
        row = db.execute(
            """
            SELECT * FROM users
            WHERE department = ? AND user_id = ? AND password_hash = ?
            """,
            (department, user_id, hash_password(password)),
        ).fetchone()
    return row


def get_user_by_token(token: str):
    if not token:
        return None
    with get_connection() as db:
        row = db.execute(
            """
            SELECT users.*
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
    return row


def delete_session(token: str) -> None:
    with get_connection() as db:
        db.execute("DELETE FROM sessions WHERE token = ?", (token,))


def _json(value) -> str:
    return json.dumps(value, default=str)


def save_request(data: dict, status: str = "SUBMITTED") -> None:
    now = utc_now()
    with get_connection() as db:
        db.execute(
            """
            INSERT INTO maintenance_requests
            (request_id, department, source_system, status, block_id,
             rejection_reason, data_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, NULL, NULL, ?, ?, ?)
            ON CONFLICT(request_id) DO UPDATE SET
                department=excluded.department,
                source_system=excluded.source_system,
                status=excluded.status,
                data_json=excluded.data_json,
                updated_at=excluded.updated_at
            """,
            (
                data["request_id"],
                data["department"],
                data["source_system"],
                status,
                _json(data),
                now,
                now,
            ),
        )


def get_request(request_id: str):
    with get_connection() as db:
        return db.execute(
            "SELECT * FROM maintenance_requests WHERE request_id = ?",
            (request_id,),
        ).fetchone()


def list_requests(department: str | None = None, request_id: str | None = None):
    query = "SELECT * FROM maintenance_requests WHERE 1=1"
    params: list = []
    if department:
        query += " AND department = ?"
        params.append(department)
    if request_id:
        query += " AND request_id = ?"
        params.append(request_id)
    query += " ORDER BY updated_at DESC"
    with get_connection() as db:
        return db.execute(query, params).fetchall()


def update_request_status(request_id: str, status: str, block_id: str | None = None, rejection_reason: str | None = None):
    with get_connection() as db:
        db.execute(
            """
            UPDATE maintenance_requests
            SET status = ?, block_id = ?, rejection_reason = ?, updated_at = ?
            WHERE request_id = ?
            """,
            (status, block_id, rejection_reason, utc_now(), request_id),
        )


def save_coa_upload(filename: str, planning_date: str, rows: list[dict], uploaded_by: str) -> None:
    with get_connection() as db:
        db.execute(
            """
            INSERT INTO coa_uploads
            (filename, planning_date, row_count, uploaded_by, data_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (filename, planning_date, len(rows), uploaded_by, _json(rows), utc_now()),
        )


def latest_coa_for_date(planning_date: str) -> list[dict]:
    with get_connection() as db:
        row = db.execute(
            """
            SELECT data_json FROM coa_uploads
            WHERE planning_date = ?
            ORDER BY id DESC LIMIT 1
            """,
            (planning_date,),
        ).fetchone()
    return json.loads(row["data_json"]) if row else []


def list_coa_uploads(limit: int = 20):
    with get_connection() as db:
        return db.execute(
            """
            SELECT id, filename, planning_date, row_count, uploaded_by, created_at
            FROM coa_uploads
            ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()


def save_block(block: dict) -> None:
    now = utc_now()
    with get_connection() as db:
        db.execute(
            """
            INSERT OR REPLACE INTO blocks
            (block_id, planning_date, section_id, start_time, end_time,
             duration_minutes, priority, priority_score, status, coordination,
             existing_block, block_calendar_id, data_json, rejection_reason,
             modification_reason, approved_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    COALESCE((SELECT created_at FROM blocks WHERE block_id = ?), ?), ?)
            """,
            (
                block["block_id"],
                block["planning_date"],
                block["section_id"],
                block["start_time"],
                block["end_time"],
                block["duration_minutes"],
                block["priority"],
                block["priority_score"],
                block["status"],
                int(block.get("coordination", False)),
                int(block.get("existing_block", False)),
                block.get("block_calendar_id"),
                _json(block.get("data", {})),
                block.get("rejection_reason"),
                block.get("modification_reason"),
                block.get("approved_by"),
                block["block_id"],
                now,
                now,
            ),
        )


def get_block(block_id: str):
    with get_connection() as db:
        return db.execute(
            "SELECT * FROM blocks WHERE block_id = ?",
            (block_id,),
        ).fetchone()


def list_blocks(planning_date: str | None = None, statuses: tuple[str, ...] | None = None):
    query = "SELECT * FROM blocks WHERE 1=1"
    params: list = []
    if planning_date:
        query += " AND planning_date = ?"
        params.append(planning_date)
    if statuses:
        placeholders = ",".join("?" for _ in statuses)
        query += f" AND status IN ({placeholders})"
        params.extend(statuses)
    query += " ORDER BY priority_score DESC, start_time ASC"
    with get_connection() as db:
        return db.execute(query, params).fetchall()


def update_block(block_id: str, **fields) -> None:
    allowed = {
        "start_time", "end_time", "duration_minutes", "status",
        "data_json", "rejection_reason", "modification_reason", "approved_by",
    }
    updates = [(key, value) for key, value in fields.items() if key in allowed]
    if not updates:
        return
    set_sql = ", ".join(f"{key} = ?" for key, _ in updates)
    values = [value for _, value in updates]
    values.extend([utc_now(), block_id])
    with get_connection() as db:
        db.execute(
            f"UPDATE blocks SET {set_sql}, updated_at = ? WHERE block_id = ?",
            values,
        )


def add_notification(department: str, title: str, message: str, block_id: str | None = None) -> None:
    with get_connection() as db:
        db.execute(
            """
            INSERT INTO notifications
            (department, title, message, block_id, is_read, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (department, title, message, block_id, utc_now()),
        )


def list_notifications(department: str, limit: int = 50):
    with get_connection() as db:
        return db.execute(
            """
            SELECT * FROM notifications
            WHERE department = ?
            ORDER BY id DESC LIMIT ?
            """,
            (department, limit),
        ).fetchall()


def mark_notification_read(notification_id: int, department: str) -> None:
    with get_connection() as db:
        db.execute(
            "UPDATE notifications SET is_read = 1 WHERE id = ? AND department = ?",
            (notification_id, department),
        )


def audit(actor: str, action: str, entity_type: str, entity_id: str | None, details: dict | None = None) -> None:
    with get_connection() as db:
        db.execute(
            """
            INSERT INTO audit_log (actor, action, entity_type, entity_id, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (actor, action, entity_type, entity_id, _json(details or {}), utc_now()),
        )
