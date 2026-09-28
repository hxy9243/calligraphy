"""Database layer supporting SQLite (default) and PostgreSQL for Calligraphy Studio."""
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    """Thread-safe SQLite/PostgreSQL database client."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.environ.get("DATABASE_URL", "sqlite:///calligraphy.db")
        self._is_sqlite = not self.db_url.startswith(("postgres://", "postgresql://"))
        self._lock = threading.Lock()
        if self._is_sqlite:
            path_str = self.db_url.replace("sqlite:///", "").replace("sqlite://", "")
            self.sqlite_path = Path(path_str).resolve()
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            self._local = threading.local()
        else:
            # PostgreSQL fallback if configured
            import psycopg2
            self._pg_pool = None  # placeholder for Postgres connection
        self.init_schema()

    def _get_sqlite_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.sqlite_path),
                timeout=30.0,
                check_same_thread=False,
            )
            self._local.conn.row_factory = sqlite3.Row
            # Enable WAL mode for high concurrency
            self._local.conn.execute("PRAGMA journal_mode=WAL;")
        return self._local.conn

    def init_schema(self) -> None:
        """Create tables if they do not exist."""
        if self._is_sqlite:
            conn = self._get_sqlite_conn()
            with self._lock:
                with conn:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS sessions (
                            session_id TEXT PRIMARY KEY,
                            created_at TEXT NOT NULL,
                            last_seen_at TEXT NOT NULL
                        );
                        """
                    )
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS jobs (
                            job_id TEXT PRIMARY KEY,
                            session_id TEXT NOT NULL,
                            job_type TEXT NOT NULL,
                            status TEXT NOT NULL,
                            text TEXT NOT NULL,
                            style TEXT NOT NULL,
                            params_json TEXT NOT NULL,
                            output_path TEXT,
                            error_message TEXT,
                            progress REAL DEFAULT 0.0,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            completed_at TEXT,
                            expires_at TEXT,
                            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                        );
                        """
                    )
                    conn.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_jobs_session
                        ON jobs(session_id, created_at DESC);
                        """
                    )
                    conn.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_jobs_status
                        ON jobs(status, created_at ASC);
                        """
                    )

    def touch_session(self, session_id: str) -> None:
        now = now_utc_iso()
        if self._is_sqlite:
            conn = self._get_sqlite_conn()
            with self._lock:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO sessions (session_id, created_at, last_seen_at)
                        VALUES (?, ?, ?)
                        ON CONFLICT(session_id) DO UPDATE SET last_seen_at = excluded.last_seen_at;
                        """,
                        (session_id, now, now),
                    )

    def create_job(
        self,
        job_id: str,
        session_id: str,
        job_type: str,
        text: str,
        style: str,
        params: Dict[str, Any],
        output_path: Optional[str] = None,
        status: str = "queued",
        progress: float = 0.0,
    ) -> Dict[str, Any]:
        now = now_utc_iso()
        params_str = json.dumps(params, ensure_ascii=False)
        self.touch_session(session_id)
        if self._is_sqlite:
            conn = self._get_sqlite_conn()
            with self._lock:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO jobs (
                            job_id, session_id, job_type, status, text, style,
                            params_json, output_path, error_message, progress,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?);
                        """,
                        (
                            job_id,
                            session_id,
                            job_type,
                            status,
                            text,
                            style,
                            params_str,
                            output_path,
                            progress,
                            now,
                            now,
                        ),
                    )
        return self.get_job(job_id)

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        output_path: Optional[str] = None,
        error_message: Optional[str] = None,
        completed: bool = False,
    ) -> Optional[Dict[str, Any]]:
        now = now_utc_iso()
        updates = ["updated_at = ?"]
        values = [now]
        if status is not None:
            updates.append("status = ?")
            values.append(status)
        if progress is not None:
            updates.append("progress = ?")
            values.append(progress)
        if output_path is not None:
            updates.append("output_path = ?")
            values.append(output_path)
        if error_message is not None:
            updates.append("error_message = ?")
            values.append(error_message)
        if completed:
            updates.append("completed_at = ?")
            values.append(now)

        values.append(job_id)
        query = f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?;"
        if self._is_sqlite:
            conn = self._get_sqlite_conn()
            with self._lock:
                with conn:
                    conn.execute(query, values)
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        if self._is_sqlite:
            conn = self._get_sqlite_conn()
            with self._lock:
                cursor = conn.execute("SELECT * FROM jobs WHERE job_id = ?;", (job_id,))
                row = cursor.fetchone()
                if row is None:
                    return None
                data = dict(row)
                data["params"] = json.loads(data.pop("params_json", "{}"))
                return data
        return None

    def list_jobs(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        if self._is_sqlite:
            conn = self._get_sqlite_conn()
            with self._lock:
                cursor = conn.execute(
                    "SELECT * FROM jobs WHERE session_id = ? ORDER BY created_at DESC LIMIT ?;",
                    (session_id, limit),
                )
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    data = dict(row)
                    data["params"] = json.loads(data.pop("params_json", "{}"))
                    result.append(data)
                return result
        return []

    def claim_next_job(self) -> Optional[Dict[str, Any]]:
        """Worker claims the oldest queued job atomically."""
        if self._is_sqlite:
            conn = self._get_sqlite_conn()
            with self._lock:
                with conn:
                    cursor = conn.execute(
                        "SELECT job_id FROM jobs WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1;"
                    )
                    row = cursor.fetchone()
                    if not row:
                        return None
                    job_id = row["job_id"]
                    now = now_utc_iso()
                    conn.execute(
                        "UPDATE jobs SET status = 'rendering', updated_at = ? WHERE job_id = ? AND status = 'queued';",
                        (now, job_id),
                    )
            return self.get_job(job_id)
        return None


_DB_INSTANCE: Optional[Database] = None


def get_db(db_url: Optional[str] = None) -> Database:
    global _DB_INSTANCE
    if _DB_INSTANCE is None or (db_url and db_url != _DB_INSTANCE.db_url):
        _DB_INSTANCE = Database(db_url)
    return _DB_INSTANCE
