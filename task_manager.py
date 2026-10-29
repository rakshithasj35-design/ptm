"""SQLite-backed data and validation helpers for the student task manager."""

from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterator


DATABASE_PATH = Path(
    os.environ.get("TASK_MANAGER_DB", Path(__file__).with_name("tasks.db"))
)
PRIORITIES = ("Low", "Medium", "High")
STATUSES = ("Pending", "In Progress", "Completed")
PASSWORD_HASH_ITERATIONS = 310_000


@dataclass(frozen=True)
class User:
    id: int
    username: str


@contextmanager
def _connect(database_path: str | Path = DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return f"{salt.hex()}:{digest.hex()}"


def _password_matches(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split(":", maxsplit=1)
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    actual_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def initialize_database(database_path: str | Path = DATABASE_PATH) -> None:
    """Create the schema and seed the database-backed demo account once."""
    with _connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL CHECK(length(name) BETWEEN 1 AND 100),
                priority TEXT NOT NULL CHECK(priority IN ('Low', 'Medium', 'High')),
                due_date TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK(status IN ('Pending', 'In Progress', 'Completed')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS tasks_user_id_due_date
                ON tasks(user_id, due_date);
            """
        )
        account = connection.execute(
            "SELECT id FROM users WHERE username = ?", ("admin",)
        ).fetchone()
        if account is None:
            connection.execute(
                "INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)",
                ("admin", _hash_password("admin123")),
            )


def authenticate(
    username: str, password: str, database_path: str | Path = DATABASE_PATH
) -> User | None:
    with _connect(database_path) as connection:
        row = connection.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    if row is None or not _password_matches(password, row["password_hash"]):
        return None
    return User(id=row["id"], username=row["username"])


def validate_task(
    name: str, priority: str, due_date: date | str, status: str
) -> tuple[str, str, str, str]:
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("Task name is required.")
    if len(cleaned_name) > 100:
        raise ValueError("Task name must be 100 characters or fewer.")
    if priority not in PRIORITIES:
        raise ValueError("Choose a valid priority.")
    if status not in STATUSES:
        raise ValueError("Choose a valid status.")
    try:
        parsed_date = due_date if isinstance(due_date, date) else date.fromisoformat(due_date)
    except (TypeError, ValueError) as error:
        raise ValueError("Enter a valid due date.") from error
    return cleaned_name, priority, parsed_date.isoformat(), status


def add_task(
    user_id: int,
    name: str,
    priority: str,
    due_date: date | str,
    status: str,
    database_path: str | Path = DATABASE_PATH,
) -> int:
    cleaned_name, priority, due_date_text, status = validate_task(
        name, priority, due_date, status
    )
    with _connect(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO tasks (user_id, name, priority, due_date, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, cleaned_name, priority, due_date_text, status),
        )
        return int(cursor.lastrowid)


def get_tasks(
    user_id: int, database_path: str | Path = DATABASE_PATH
) -> list[dict[str, object]]:
    with _connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT name, priority, due_date, status
            FROM tasks
            WHERE user_id = ?
            ORDER BY due_date, id
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_task_metrics(
    user_id: int, database_path: str | Path = DATABASE_PATH
) -> dict[str, int]:
    metrics = {"Total": 0, "Pending": 0, "In Progress": 0, "Completed": 0}
    with _connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM tasks
            WHERE user_id = ?
            GROUP BY status
            """,
            (user_id,),
        ).fetchall()
    for row in rows:
        metrics[row["status"]] = row["count"]
        metrics["Total"] += row["count"]
    return metrics
