import sqlite3
import json
import threading
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple


class QuarantineStore:
    """Manages quarantined chunks with approve/reject workflow."""

    def __init__(self, db_path: str = "data/ledger/quarantine.db"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quarantine (
                chunk_id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                author_id TEXT NOT NULL,
                risk REAL NOT NULL,
                reasons TEXT,
                status TEXT DEFAULT 'PENDING',
                reviewer TEXT,
                reviewed_at TEXT,
                created_at TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def _execute(self, sql: str, params: tuple = ()):
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def add_to_quarantine(self, chunk_id: str, text: str, author_id: str, risk: float, reasons: List[str]) -> bool:
        """Adds a chunk to quarantine."""
        try:
            self._execute("""
                INSERT INTO quarantine (chunk_id, text, author_id, risk, reasons, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'PENDING', ?)
            """, (chunk_id, text, author_id, risk, json.dumps(reasons), datetime.now(timezone.utc).isoformat()))
            return True
        except sqlite3.IntegrityError:
            return False

    def get_pending_chunks(self) -> List[Dict]:
        """Retrieves all pending quarantined chunks."""
        cursor = self._execute("""
            SELECT chunk_id, text, author_id, risk, reasons, created_at
            FROM quarantine WHERE status = 'PENDING'
        """)
        rows = cursor.fetchall()
        return [
            {
                "chunk_id": row[0],
                "text": row[1],
                "author_id": row[2],
                "risk": row[3],
                "reasons": json.loads(row[4]) if row[4] else [],
                "created_at": row[5]
            }
            for row in rows
        ]

    def approve_chunk(self, chunk_id: str, reviewer: str) -> bool:
        """Approves a quarantined chunk."""
        cursor = self._execute("""
            UPDATE quarantine 
            SET status = 'APPROVED', reviewer = ?, reviewed_at = ?
            WHERE chunk_id = ? AND status = 'PENDING'
        """, (reviewer, datetime.now(timezone.utc).isoformat(), chunk_id))
        return cursor.rowcount > 0

    def reject_chunk(self, chunk_id: str, reviewer: str) -> bool:
        """Rejects a quarantined chunk."""
        cursor = self._execute("""
            UPDATE quarantine 
            SET status = 'REJECTED', reviewer = ?, reviewed_at = ?
            WHERE chunk_id = ? AND status = 'PENDING'
        """, (reviewer, datetime.now(timezone.utc).isoformat(), chunk_id))
        return cursor.rowcount > 0

    def get_chunk_status(self, chunk_id: str) -> Optional[Dict]:
        """Gets the status of a quarantined chunk."""
        cursor = self._execute("""
            SELECT chunk_id, status, reviewer, reviewed_at, created_at
            FROM quarantine WHERE chunk_id = ?
        """, (chunk_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "chunk_id": row[0],
            "status": row[1],
            "reviewer": row[2],
            "reviewed_at": row[3],
            "created_at": row[4]
        }
