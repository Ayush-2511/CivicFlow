"""SQLite Document & Clause Store.

Provides local persistent caching of ingested documents and extracted clauses.
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List, Optional
from app.config import settings
from app.schemas import Clause


class DocumentStore:
    """Manages SQLite persistence for documents, clauses, and metadata."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = str(db_path or settings.SQLITE_DB_PATH)
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database tables if they do not exist."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS clauses (
                    id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    page INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_clauses_doc_id ON clauses(doc_id)"
            )
            conn.commit()

    def has_document(self, doc_id: str) -> bool:
        """Check if document already exists in store."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT 1 FROM documents WHERE doc_id = ?", (doc_id,))
            return cursor.fetchone() is not None

    def get_document(self, doc_id: str) -> Optional[dict]:
        """Fetch document metadata by doc_id."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT doc_id, filename, content_type, created_at FROM documents WHERE doc_id = ?",
                (doc_id,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_clauses(self, doc_id: str) -> Optional[List[Clause]]:
        """Retrieve stored clauses for a document."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, doc_id, page, text FROM clauses WHERE doc_id = ? ORDER BY page ASC, id ASC",
                (doc_id,),
            )
            rows = cursor.fetchall()
            if not rows:
                return None
            return [
                Clause(
                    id=row["id"],
                    doc_id=row["doc_id"],
                    page=row["page"],
                    text=row["text"],
                )
                for row in rows
            ]

    def save_document(
        self,
        doc_id: str,
        filename: str,
        content_type: str,
        clauses: List[Clause],
    ) -> None:
        """Persist document metadata and clauses."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO documents (doc_id, filename, content_type)
                VALUES (?, ?, ?)
                """,
                (doc_id, filename, content_type),
            )
            conn.execute("DELETE FROM clauses WHERE doc_id = ?", (doc_id,))
            conn.executemany(
                """
                INSERT INTO clauses (id, doc_id, page, text)
                VALUES (?, ?, ?, ?)
                """,
                [(c.id, c.doc_id, c.page, c.text) for c in clauses],
            )
            conn.commit()


# Default singleton instance
store = DocumentStore()
