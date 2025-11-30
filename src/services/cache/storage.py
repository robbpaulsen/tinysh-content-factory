"""
SQLite storage backend for asset cache.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import json


class CacheStorage:
    """SQLite-based storage for cached assets."""

    def __init__(self, db_path: Path):
        """
        Initialize cache storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_type TEXT NOT NULL,
                    prompt_hash TEXT NOT NULL,
                    prompt_text TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    last_used_at TEXT NOT NULL,
                    use_count INTEGER DEFAULT 1,
                    UNIQUE(asset_type, prompt_hash)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_asset_type_hash
                ON cache_entries(asset_type, prompt_hash)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_asset_type
                ON cache_entries(asset_type)
            """)
            conn.commit()

    def get_by_hash(
        self, asset_type: str, prompt_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached entry by exact hash match.

        Args:
            asset_type: Type of asset (image, tts)
            prompt_hash: Hash of the prompt

        Returns:
            Cache entry dict or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM cache_entries
                WHERE asset_type = ? AND prompt_hash = ?
                """,
                (asset_type, prompt_hash),
            )
            row = cursor.fetchone()
            if row:
                # Update last_used_at and use_count
                conn.execute(
                    """
                    UPDATE cache_entries
                    SET last_used_at = ?, use_count = use_count + 1
                    WHERE id = ?
                    """,
                    (datetime.utcnow().isoformat(), row["id"]),
                )
                conn.commit()
                return dict(row)
            return None

    def get_all_by_type(self, asset_type: str) -> List[Dict[str, Any]]:
        """
        Get all cached entries of a specific type.

        Args:
            asset_type: Type of asset (image, tts)

        Returns:
            List of cache entry dicts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM cache_entries
                WHERE asset_type = ?
                ORDER BY created_at DESC
                """,
                (asset_type,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def insert(
        self,
        asset_type: str,
        prompt_hash: str,
        prompt_text: str,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Insert new cache entry.

        Args:
            asset_type: Type of asset (image, tts)
            prompt_hash: Hash of the prompt
            prompt_text: Original prompt text
            file_path: Path to cached file
            metadata: Optional metadata dict

        Returns:
            ID of inserted entry
        """
        now = datetime.utcnow().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO cache_entries
                (asset_type, prompt_hash, prompt_text, file_path, metadata,
                 created_at, last_used_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_type,
                    prompt_hash,
                    prompt_text,
                    file_path,
                    metadata_json,
                    now,
                    now,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def delete(self, entry_id: int) -> None:
        """
        Delete cache entry by ID.

        Args:
            entry_id: ID of entry to delete
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache_entries WHERE id = ?", (entry_id,))
            conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT
                    asset_type,
                    COUNT(*) as count,
                    SUM(use_count) as total_uses,
                    AVG(use_count) as avg_uses_per_entry
                FROM cache_entries
                GROUP BY asset_type
                """
            )
            stats_by_type = {}
            for row in cursor.fetchall():
                stats_by_type[row[0]] = {
                    "count": row[1],
                    "total_uses": row[2],
                    "avg_uses_per_entry": round(row[3], 2),
                }

            cursor = conn.execute(
                "SELECT COUNT(*) as total FROM cache_entries"
            )
            total = cursor.fetchone()[0]

            return {"total_entries": total, "by_type": stats_by_type}
