"""Local Zero-Dependency BM25 RAG & Codebase Search Engine for Iris."""

from contextlib import contextmanager
import math
import os
import re
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

from config import config


@dataclass
class SearchResult:
    file_path: str
    chunk_index: int
    start_line: int
    end_line: int
    content: str
    score: float


class LocalRAGStore:
    """Zero-dependency local SQLite-backed text & code indexer with BM25 ranking."""

    SUPPORTED_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".md", ".txt", ".json",
        ".yaml", ".yml", ".html", ".css", ".rs", ".go", ".c", ".cpp",
        ".h", ".sql", ".sh", ".ps1", ".toml", ".ini", ".csv"
    }

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or ".iris_rag.db")
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
                    CREATE TABLE IF NOT EXISTS rag_documents (
                        doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT UNIQUE NOT NULL,
                        total_chunks INTEGER NOT NULL,
                        indexed_at TEXT NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rag_chunks (
                        chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        doc_id INTEGER NOT NULL,
                        file_path TEXT NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        start_line INTEGER NOT NULL,
                        end_line INTEGER NOT NULL,
                        content TEXT NOT NULL,
                        FOREIGN KEY(doc_id) REFERENCES rag_documents(doc_id) ON DELETE CASCADE
                    )
                    """
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunk_path ON rag_chunks(file_path)")

    def _tokenize(self, text: str) -> List[str]:
        """Simple lowercase word tokenizer."""
        return re.findall(r"\w+", text.lower())

    def index_directory(
        self,
        folder_path: str,
        max_files: int = 200,
        chunk_size: int = 600,
        overlap: int = 100,
    ) -> Tuple[int, int]:
        """Indexes all supported text and code files within a folder."""
        root = Path(folder_path).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        files_indexed = 0
        total_chunks = 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Exclude typical ignore folders
        ignored_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", ".iris_cache", "dist", "build"}

        for p in root.rglob("*"):
            if files_indexed >= max_files:
                break
            if p.is_file() and p.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                if any(part in ignored_dirs for part in p.parts):
                    continue

                try:
                    with open(p, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                    if not lines:
                        continue

                    # Chunk by lines
                    doc_chunks = []
                    curr_chunk = []
                    curr_len = 0
                    start_ln = 1

                    for idx, line in enumerate(lines, 1):
                        curr_chunk.append(line)
                        curr_len += len(line)

                        if curr_len >= chunk_size:
                            chunk_text = "".join(curr_chunk)
                            doc_chunks.append((start_ln, idx, chunk_text))
                            # Overlap by taking last few lines
                            overlap_lines = curr_chunk[-3:] if len(curr_chunk) > 3 else []
                            curr_chunk = list(overlap_lines)
                            curr_len = sum(len(l) for l in curr_chunk)
                            start_ln = max(1, idx - len(overlap_lines) + 1)

                    if curr_chunk:
                        doc_chunks.append((start_ln, len(lines), "".join(curr_chunk)))

                    # Save to DB
                    file_str = str(p)
                    with self._lock:
                        with self._connect() as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                """
                                INSERT INTO rag_documents (file_path, total_chunks, indexed_at)
                                VALUES (?, ?, ?)
                                ON CONFLICT(file_path) DO UPDATE SET total_chunks=excluded.total_chunks, indexed_at=excluded.indexed_at
                                """,
                                (file_str, len(doc_chunks), now),
                            )
                            doc_id = cursor.execute("SELECT doc_id FROM rag_documents WHERE file_path = ?", (file_str,)).fetchone()["doc_id"]
                            cursor.execute("DELETE FROM rag_chunks WHERE doc_id = ?", (doc_id,))

                            for c_idx, (s_ln, e_ln, c_text) in enumerate(doc_chunks):
                                cursor.execute(
                                    """
                                    INSERT INTO rag_chunks (doc_id, file_path, chunk_index, start_line, end_line, content)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                    """,
                                    (doc_id, file_str, c_idx, s_ln, e_ln, c_text),
                                )

                    files_indexed += 1
                    total_chunks += len(doc_chunks)

                except Exception:
                    continue

        return files_indexed, total_chunks

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """BM25 ranking search over indexed chunks."""
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        with self._lock:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT chunk_id, file_path, chunk_index, start_line, end_line, content FROM rag_chunks")
                all_chunks = cursor.fetchall()

        if not all_chunks:
            return []

        N = len(all_chunks)
        avg_doc_len = sum(len(self._tokenize(c["content"])) for c in all_chunks) / max(1, N)

        # Document Frequency (DF) for each query term
        doc_freq: Dict[str, int] = {t: 0 for t in query_terms}
        chunk_tokens_map = {}

        for c in all_chunks:
            c_tokens = self._tokenize(c["content"])
            chunk_tokens_map[c["chunk_id"]] = c_tokens
            token_set = set(c_tokens)
            for t in query_terms:
                if t in token_set:
                    doc_freq[t] += 1

        # BM25 Hyperparameters
        k1 = 1.5
        b = 0.75

        scored_results = []
        for c in all_chunks:
            cid = c["chunk_id"]
            tokens = chunk_tokens_map[cid]
            doc_len = len(tokens)
            score = 0.0

            # Count term frequencies in this chunk
            tf_map: Dict[str, int] = {}
            for tok in tokens:
                tf_map[tok] = tf_map.get(tok, 0) + 1

            for term in query_terms:
                if term in tf_map:
                    tf = tf_map[term]
                    df = doc_freq.get(term, 0)
                    idf = math.log(1.0 + (N - df + 0.5) / (df + 0.5))
                    num = tf * (k1 + 1)
                    denom = tf + k1 * (1 - b + b * (doc_len / avg_doc_len))
                    score += idf * (num / max(0.001, denom))

            if score > 0.1:
                scored_results.append(
                    SearchResult(
                        file_path=c["file_path"],
                        chunk_index=c["chunk_index"],
                        start_line=c["start_line"],
                        end_line=c["end_line"],
                        content=c["content"],
                        score=round(score, 3),
                    )
                )

        scored_results.sort(key=lambda x: x.score, reverse=True)
        return scored_results[:top_k]
