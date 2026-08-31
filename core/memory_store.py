from contextlib import contextmanager
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from config import config
from core.protocols import MemoryProtocol


class PersistentMemoryStore(MemoryProtocol):
    """SQLite-backed conversation memory and persistent user knowledge vault."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or getattr(config, "memory_db_path", ".iris_memory.db"))
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
        """Initializes database schema if not present."""
        with self._lock:
            with self._connect() as conn:
                cursor = conn.cursor()
                # 1. Conversation History Table
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
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_session ON conversation_history(session_id)")

                # 2. User Knowledge & Preference Vault Table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_vault (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        category TEXT DEFAULT 'general',
                        updated_at TEXT NOT NULL
                    )
                    """
                )

    # --- Conversation Memory Protocol Implementation ---

    def add_message(self, role: str, content: str, session_id: str = "default") -> None:
        """Stores a message turn in persistent history."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO conversation_history (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    (session_id, role, content, now),
                )

    def get_context(self, session_id: str = "default", limit: int = 20) -> List[Dict[str, str]]:
        """Retrieves the recent sliding context window."""
        with self._lock:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT role, content FROM (
                        SELECT role, content, id FROM conversation_history
                        WHERE session_id = ?
                        ORDER BY id DESC LIMIT ?
                    ) ORDER BY id ASC
                    """,
                    (session_id, limit),
                )
                rows = cursor.fetchall()
                return [{"role": r["role"], "content": r["content"]} for r in rows]

    def clear(self, session_id: str = "default") -> None:
        """Clears conversation turns for a given session."""
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM conversation_history WHERE session_id = ?", (session_id,))

    # --- User Knowledge Vault Methods ---

    def remember_fact(self, key: str, value: str, category: str = "general") -> None:
        """Stores or updates a learned user preference or fact."""
        clean_key = key.strip().lower()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO user_vault (key, value, category, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value, category=excluded.category, updated_at=excluded.updated_at
                    """,
                    (clean_key, value.strip(), category, now),
                )

    def forget_fact(self, key: str) -> bool:
        """Removes a fact from the user vault."""
        clean_key = key.strip().lower()
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute("DELETE FROM user_vault WHERE key = ?", (clean_key,))
                return cursor.rowcount > 0

    def get_all_facts(self) -> Dict[str, str]:
        """Returns all stored user preferences and facts."""
        with self._lock:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value FROM user_vault ORDER BY key ASC")
                rows = cursor.fetchall()
                return {r["key"]: r["value"] for r in rows}

    def format_vault_prompt(self) -> str:
        """Formats stored user facts into a prompt header block for the AI."""
        facts = self.get_all_facts()
        if not facts:
            return ""

        lines = [f"- **{k}**: {v}" for k, v in facts.items()]
        facts_block = "\n".join(lines)
        return (
            "## Stored User Profile & Preferences\n"
            f"{facts_block}\n"
        )
