"""Incremental SQLite cache tracking file offsets, size, and mtime for zero-redundancy ingestion."""

import json
import os
import pathlib
import sqlite3
import datetime as dt
from typing import Dict, Any, List, Optional, Tuple


class MetricsCache:
    def __init__(self, db_path: Optional[pathlib.Path] = None):
        if db_path is None:
            # Default to ~/.devcity/cache.db, or local data/cache.db
            base_dir = pathlib.Path.home() / ".devcity"
            try:
                base_dir.mkdir(parents=True, exist_ok=True)
                db_path = base_dir / "cache.db"
            except Exception:
                db_path = pathlib.Path("data") / "cache.db"
                db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_offsets (
                    file_path TEXT PRIMARY KEY,
                    file_size INTEGER,
                    mtime REAL,
                    byte_offset INTEGER,
                    last_scanned TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    source TEXT,
                    project_name TEXT,
                    session_id TEXT,
                    timestamp TEXT,
                    model TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cache_write_tokens INTEGER,
                    cache_read_tokens INTEGER,
                    tool_calls_json TEXT,
                    event_timestamps_json TEXT,
                    PRIMARY KEY (source, session_id)
                )
            """)
            conn.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', '1')")
            conn.commit()

    def get_file_offset(self, file_path: pathlib.Path) -> int:
        """Returns the byte offset to start reading from. Resets to 0 if truncated or rotated."""
        fp_str = str(file_path.resolve())
        if not file_path.exists():
            return 0
        stat = file_path.stat()
        with self._get_conn() as conn:
            cur = conn.execute("SELECT file_size, mtime, byte_offset FROM file_offsets WHERE file_path = ?", (fp_str,))
            row = cur.fetchone()
            if not row:
                return 0
            # If file shrank, it was truncated or rotated -> start from 0
            if stat.st_size < row["file_size"] or stat.st_size < row["byte_offset"]:
                return 0
            # If mtime is identical and size is identical, it hasn't changed
            if stat.st_mtime == row["mtime"] and stat.st_size == row["file_size"]:
                return row["byte_offset"]
            return row["byte_offset"]

    def update_file_offset(self, file_path: pathlib.Path, new_offset: int):
        fp_str = str(file_path.resolve())
        stat = file_path.stat() if file_path.exists() else None
        fsize = stat.st_size if stat else 0
        fmtime = stat.st_mtime if stat else 0.0
        now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO file_offsets (file_path, file_size, mtime, byte_offset, last_scanned)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_size = excluded.file_size,
                    mtime = excluded.mtime,
                    byte_offset = excluded.byte_offset,
                    last_scanned = excluded.last_scanned
            """, (fp_str, fsize, fmtime, new_offset, now_iso))
            conn.commit()

    def save_session(
        self,
        source: str,
        project_name: str,
        session_id: str,
        timestamp_iso: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_write_tokens: int,
        cache_read_tokens: int,
        tool_calls: Dict[str, int],
        event_timestamps: List[float]
    ):
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO sessions (
                    source, project_name, session_id, timestamp, model,
                    input_tokens, output_tokens, cache_write_tokens, cache_read_tokens,
                    tool_calls_json, event_timestamps_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, session_id) DO UPDATE SET
                    project_name = excluded.project_name,
                    timestamp = excluded.timestamp,
                    model = excluded.model,
                    input_tokens = excluded.input_tokens,
                    output_tokens = excluded.output_tokens,
                    cache_write_tokens = excluded.cache_write_tokens,
                    cache_read_tokens = excluded.cache_read_tokens,
                    tool_calls_json = excluded.tool_calls_json,
                    event_timestamps_json = excluded.event_timestamps_json
            """, (
                source, project_name, session_id, timestamp_iso, model,
                input_tokens, output_tokens, cache_write_tokens, cache_read_tokens,
                json.dumps(tool_calls), json.dumps(event_timestamps)
            ))
            conn.commit()

    def get_sessions(self, since_iso: str) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cur = conn.execute("""
                SELECT source, project_name, session_id, timestamp, model,
                       input_tokens, output_tokens, cache_write_tokens, cache_read_tokens,
                       tool_calls_json, event_timestamps_json
                FROM sessions
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            """, (since_iso,))
            rows = []
            for r in cur.fetchall():
                rows.append({
                    "source": r["source"],
                    "project_name": r["project_name"],
                    "session_id": r["session_id"],
                    "timestamp": r["timestamp"],
                    "model": r["model"],
                    "input_tokens": r["input_tokens"],
                    "output_tokens": r["output_tokens"],
                    "cache_write_tokens": r["cache_write_tokens"],
                    "cache_read_tokens": r["cache_read_tokens"],
                    "tool_calls": json.loads(r["tool_calls_json"] or "{}"),
                    "event_timestamps": json.loads(r["event_timestamps_json"] or "[]"),
                })
            return rows

    def purge_missing_files(self, existing_file_paths: List[pathlib.Path]):
        existing_set = {str(p.resolve()) for p in existing_file_paths}
        with self._get_conn() as conn:
            cur = conn.execute("SELECT file_path FROM file_offsets")
            all_tracked = [r["file_path"] for r in cur.fetchall()]
            for tracked in all_tracked:
                if tracked not in existing_set:
                    conn.execute("DELETE FROM file_offsets WHERE file_path = ?", (tracked,))
            conn.commit()
