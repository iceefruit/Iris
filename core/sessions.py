"""Multi-Session and Project Workspace Manager for Iris."""

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional

from config import config


class SessionManager:
    """Manages isolated conversation workspaces and session contexts."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or getattr(config, "memory_db_path", ".iris_memory.db"))
        self._active_session: str = "default"
        self._lock = threading.Lock()
        self._init_db()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._lock:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation_sessions (
                        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT DEFAULT '',
                        created_at TEXT NOT NULL,
                        last_active_at TEXT NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                    """
                )
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO conversation_sessions (name, description, created_at, last_active_at)
                    VALUES ('default', 'Main Default Workspace', ?, ?)
                    """,
                    (now, now),
                )

    @property
    def active_session(self) -> str:
        return self._active_session

    def create_session(self, name: str, description: str = "") -> bool:
        """Creates a new named conversation workspace session."""
        clean_name = name.strip().lower()
        if not clean_name:
            return False

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            with self._connect() as conn:
                try:
                    conn.execute(
                        """
                        INSERT INTO conversation_sessions (name, description, created_at, last_active_at)
                        VALUES (?, ?, ?, ?)
                        """,
                        (clean_name, description, now, now),
                    )
                    return True
                except sqlite3.IntegrityError:
                    return False

    def switch_session(self, name: str) -> bool:
        """Switches the active conversation session to the target workspace."""
        clean_name = name.strip().lower()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM conversation_sessions WHERE name = ?", (clean_name,))
                row = cursor.fetchone()
                if not row:
                    # Auto-create session if it doesn't exist
                    cursor.execute(
                        """
                        INSERT INTO conversation_sessions (name, description, created_at, last_active_at)
                        VALUES (?, 'Custom Workspace', ?, ?)
                        """,
                        (clean_name, now, now),
                    )

                cursor.execute("UPDATE conversation_sessions SET last_active_at = ? WHERE name = ?", (now, clean_name))
                self._active_session = clean_name
                return True

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Returns all registered workspace sessions."""
        with self._lock:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT s.name, s.description, s.created_at, s.last_active_at,
                           (SELECT COUNT(*) FROM conversation_history WHERE session_id = s.name) as message_count
                    FROM conversation_sessions s
                    ORDER BY s.last_active_at DESC
                    """
                )
                rows = cursor.fetchall()
                return [
                    {
                        "name": r["name"],
                        "description": r["description"],
                        "created_at": r["created_at"],
                        "last_active_at": r["last_active_at"],
                        "message_count": r["message_count"],
                        "is_active": r["name"] == self._active_session,
                    }
                    for r in rows
                ]

    def delete_session(self, name: str) -> bool:
        """Deletes a session and its associated conversation history."""
        clean_name = name.strip().lower()
        if clean_name == "default":
            return False  # Cannot delete default session

        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM conversation_history WHERE session_id = ?", (clean_name,))
                cursor = conn.execute("DELETE FROM conversation_sessions WHERE name = ?", (clean_name,))
                if self._active_session == clean_name:
                    self._active_session = "default"
                return cursor.rowcount > 0


# Global session manager singleton
session_manager = SessionManager()
