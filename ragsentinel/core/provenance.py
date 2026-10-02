import sqlite3
import hashlib
import json
import threading
from datetime import datetime
from typing import Optional, Tuple
from ragsentinel.models.schemas import ChunkMetadata


class ProvenanceStore:
    """Maintains an immutable append-only ledger tracking chunks and author lineage."""

    def __init__(self, db_path: str = "data/ledger/provenance_store.db"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS provenance_ledger (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                author_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                sha256_hash TEXT NOT NULL,
                signature TEXT,
                custom_attributes TEXT,
                is_revoked INTEGER DEFAULT 0
            )
        """)
        self._conn.commit()

    def _execute(self, sql: str, params: tuple = ()):
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    @staticmethod
    def compute_sha256(text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def register_chunk(self, metadata: ChunkMetadata) -> bool:
        """Registers a chunk's cryptographic proof in the ledger."""
        try:
            self._execute("""
                INSERT INTO provenance_ledger 
                (chunk_id, document_id, author_id, timestamp, sha256_hash, signature, custom_attributes, is_revoked)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                metadata.chunk_id,
                metadata.document_id,
                metadata.author_id,
                metadata.timestamp.isoformat(),
                metadata.sha256_hash,
                metadata.signature or "",
                json.dumps(metadata.custom_attributes)
            ))
            return True
        except sqlite3.IntegrityError:
            return False

    def verify_chunk_integrity(self, chunk_id: str, raw_text: str) -> Tuple[bool, Optional[str]]:
        """Verifies chunk integrity against the recorded SHA-256 hash."""
        cursor = self._execute("SELECT sha256_hash, is_revoked FROM provenance_ledger WHERE chunk_id = ?", (chunk_id,))
        row = cursor.fetchone()
        if not row:
            return False, "Record missing from provenance ledger (Unverified Origin)."
        stored_hash, is_revoked = row
        if is_revoked == 1:
            return False, "Chunk has been explicitly revoked in provenance ledger."
        calculated_hash = self.compute_sha256(raw_text)
        if calculated_hash != stored_hash:
            return False, f"Hash mismatch. Expected {stored_hash}, computed {calculated_hash}."
        return True, None

    def revoke_chunk(self, chunk_id: str):
        self._execute("UPDATE provenance_ledger SET is_revoked = 1 WHERE chunk_id = ?", (chunk_id,))

    def get_chunk_metadata(self, chunk_id: str) -> Optional[dict]:
        """Retrieves chunk metadata from the ledger."""
        cursor = self._execute("""
            SELECT chunk_id, document_id, author_id, timestamp, sha256_hash, signature, custom_attributes, is_revoked
            FROM provenance_ledger WHERE chunk_id = ?
        """, (chunk_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "chunk_id": row[0],
            "document_id": row[1],
            "author_id": row[2],
            "timestamp": row[3],
            "sha256_hash": row[4],
            "signature": row[5],
            "custom_attributes": json.loads(row[6]) if row[6] else {},
            "is_revoked": bool(row[7])
        }
