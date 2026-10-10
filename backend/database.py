"""Database layer supporting SQLite (default) and PostgreSQL for Calligraphy Studio."""
import json
import os
import sqlite3
import threading
import time
import math
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# Accepted output defaults also describe legacy rows written before a parameter
# was explicit in the API. Unknown/new keys remain part of the render identity.
RENDER_PARAMETER_DEFAULTS = {
    "fps": 24, "speed": 1.0, "spacing": 0.18, "direction": "vertical-rl",
    "font_size": None, "fit": True,
}


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AdmissionError(Exception):
    def __init__(self, message, retry_after=60):
        super().__init__(message)
        self.retry_after = retry_after


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
                    # Serialize additive schema upgrades across worker processes.
                    conn.execute("BEGIN IMMEDIATE;")
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
                            warning_message TEXT,
                            progress REAL DEFAULT 0.0,
                            created_at TEXT NOT NULL,
                            updated_at TEXT NOT NULL,
                            completed_at TEXT,
                            expires_at TEXT,
                            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                        );
                        """
                    )
                    columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
                    if "warning_message" not in columns:
                        conn.execute("ALTER TABLE jobs ADD COLUMN warning_message TEXT")
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
                    # One short-lived, revocable capability per finished video.
                    conn.execute("CREATE TABLE IF NOT EXISTS video_exports (job_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, expires_at REAL NOT NULL)")
                    # Sharing has its own capability; it never extends an export link.
                    conn.execute("CREATE TABLE IF NOT EXISTS video_shares (job_id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, expires_at REAL NOT NULL)")
                    conn.execute("CREATE TABLE IF NOT EXISTS creation_events (session_id TEXT NOT NULL, created_at REAL NOT NULL)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_creation_events ON creation_events(session_id, created_at)")

    def _admit_creation(self, conn, session_id):
        """Called inside the same write transaction as the new job insertion."""
        now = time.time()
        conn.execute("DELETE FROM creation_events WHERE created_at <= ?", (now - 60,))
        events = conn.execute("SELECT created_at FROM creation_events WHERE session_id = ? ORDER BY created_at", (session_id,)).fetchall()
        if len(events) >= 3:
            raise AdmissionError("每分钟最多创建 3 次，请稍后再试 / Maximum 3 creations per minute.", max(1, math.ceil(events[0][0] + 60 - now)))
        active = conn.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued', 'rendering', 'running')").fetchone()[0]
        if active >= int(os.environ.get("CALLIGRAPHY_MAX_ACTIVE_JOBS", "10")):
            raise AdmissionError("任务队列已满，请稍后再试 / Render queue is full.", 10)
        conn.execute("INSERT INTO creation_events VALUES (?, ?)", (session_id, now))

    def recover_interrupted_jobs(self):
        """The exclusive single-instance runner calls this before accepting work."""
        now = now_utc_iso()
        conn = self._get_sqlite_conn()
        with self._lock, conn:
            return conn.execute("UPDATE jobs SET status = 'failed', error_message = ?, completed_at = ?, updated_at = ? WHERE status IN ('rendering', 'running')", ("服务重启中断了任务，请重新创建 / Interrupted by server restart; please retry.", now, now)).rowcount

    @contextmanager
    def retention_cleanup(self, cutoff):
        """Serialize cleanup through unlink with share creation across processes.

        The caller must remove expired files before leaving this context. A share
        is never issued between protected-path selection and physical removal.
        """
        conn = self._get_sqlite_conn()
        with self._lock, conn:
            conn.execute("BEGIN IMMEDIATE;")
            now = time.time()
            conn.execute("""DELETE FROM jobs WHERE status IN ('succeeded', 'failed')
                AND COALESCE(completed_at, created_at) < ?
                AND NOT (status = 'succeeded' AND job_type = 'render' AND EXISTS
                    (SELECT 1 FROM video_shares WHERE video_shares.job_id = jobs.job_id AND video_shares.expires_at > ?))""", (cutoff, now))
            conn.execute("DELETE FROM video_exports WHERE expires_at <= ? OR job_id NOT IN (SELECT job_id FROM jobs)", (now,))
            conn.execute("DELETE FROM video_shares WHERE expires_at <= ? OR job_id NOT IN (SELECT job_id FROM jobs)", (now,))
            rows = conn.execute("""SELECT jobs.output_path FROM jobs JOIN video_shares USING (job_id)
                WHERE video_shares.expires_at > ? AND jobs.status = 'succeeded'
                    AND jobs.job_type = 'render' AND jobs.output_path IS NOT NULL""", (now,)).fetchall()
            yield {Path(row["output_path"]).resolve() for row in rows}

    def prune_history(self, cutoff):
        with self.retention_cleanup(cutoff):
            pass

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
        admit: bool = False,
    ) -> Dict[str, Any]:
        now = now_utc_iso()
        params_str = json.dumps(params, ensure_ascii=False, sort_keys=True)
        self.touch_session(session_id)
        if self._is_sqlite:
            conn = self._get_sqlite_conn()
            with self._lock:
                with conn:
                    if admit:
                        conn.execute("BEGIN IMMEDIATE;")
                        self._admit_creation(conn, session_id)
                    self._insert_job(
                        conn, job_id, session_id, job_type, text, style,
                        params_str, output_path, status, progress, now,
                    )
        return self.get_job(job_id)

    @staticmethod
    def _insert_job(conn, job_id, session_id, job_type, text, style,
                    params_json, output_path, status, progress, now):
        conn.execute(
            """
            INSERT INTO jobs (
                job_id, session_id, job_type, status, text, style,
                params_json, output_path, error_message, progress,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?);
            """,
            (job_id, session_id, job_type, status, text, style,
             params_json, output_path, progress, now, now),
        )

    def enqueue_render(
        self,
        job_id: str,
        session_id: str,
        text: str,
        style: str,
        params: Dict[str, Any],
        admit: bool = False,
    ) -> Dict[str, Any]:
        """Reuse identical active renders in this session, or enqueue a new one.

        BEGIN IMMEDIATE serializes lookup + insert across SQLite connections and
        processes, not just threads sharing this Database instance. Comparing the
        decoded parameters also handles jobs saved before canonical JSON ordering.
        Terminal jobs are deliberately excluded so users can retry or render again.
        """
        identity_params = {**RENDER_PARAMETER_DEFAULTS, **params}
        self.touch_session(session_id)
        if not self._is_sqlite:
            raise NotImplementedError("Render queue requires SQLite")
        conn = self._get_sqlite_conn()
        with self._lock:
            with conn:
                conn.execute("BEGIN IMMEDIATE;")
                rows = conn.execute(
                    """
                    SELECT * FROM jobs
                    WHERE session_id = ? AND job_type = 'render'
                        AND text = ? AND style = ?
                        AND status IN ('queued', 'rendering', 'running')
                    ORDER BY created_at ASC;
                    """,
                    (session_id, text, style),
                ).fetchall()
                for row in rows:
                    job = self._decode_job(row)
                    if {**RENDER_PARAMETER_DEFAULTS, **job["params"]} == identity_params:
                        return job

                if admit:
                    self._admit_creation(conn, session_id)
                self._insert_job(
                    conn, job_id, session_id, "render", text, style,
                    json.dumps(identity_params, ensure_ascii=False, sort_keys=True),
                    None, "queued", 0.0, now_utc_iso(),
                )
                row = conn.execute(
                    "SELECT * FROM jobs WHERE job_id = ?;", (job_id,)
                ).fetchone()
                return self._decode_job(row)

    @staticmethod
    def _decode_job(row) -> Dict[str, Any]:
        data = dict(row)
        data["params"] = json.loads(data.pop("params_json", "{}"))
        return data

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        output_path: Optional[str] = None,
        error_message: Optional[str] = None,
        warning_message: Optional[str] = None,
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
        if warning_message is not None:
            updates.append("warning_message = ?")
            values.append(warning_message)
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
                return self._decode_job(row)
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
                    result.append(self._decode_job(row))
                return result
        return []

    def delete_history_job(self, job_id: str, session_id: str) -> str:
        """Remove a terminal history row, atomically checking session and status.

        Output files are retained for the existing output-retention lifecycle.
        """
        if not self._is_sqlite:
            raise NotImplementedError("Job history requires SQLite")
        conn = self._get_sqlite_conn()
        with self._lock:
            with conn:
                conn.execute("BEGIN IMMEDIATE;")
                row = conn.execute(
                    "SELECT status FROM jobs WHERE job_id = ? AND session_id = ?;",
                    (job_id, session_id),
                ).fetchone()
                if row is None:
                    return "missing"
                if row["status"] not in ("succeeded", "failed"):
                    return "active"
                conn.execute(
                    "DELETE FROM jobs WHERE job_id = ? AND session_id = ?;",
                    (job_id, session_id),
                )
                conn.execute("DELETE FROM video_exports WHERE job_id = ?", (job_id,))
                conn.execute("DELETE FROM video_shares WHERE job_id = ?", (job_id,))
                return "deleted"

    def set_video_export(self, job_id, session_id, token_hash, expires_at):
        conn = self._get_sqlite_conn()
        with self._lock, conn:
            conn.execute("BEGIN IMMEDIATE;")
            conn.execute("DELETE FROM video_exports WHERE expires_at <= ? OR job_id NOT IN (SELECT job_id FROM jobs)", (time.time(),))
            job = conn.execute("SELECT status, job_type FROM jobs WHERE job_id = ? AND session_id = ?", (job_id, session_id)).fetchone()
            if not job or job["status"] != "succeeded" or job["job_type"] != "render":
                return False
            conn.execute("INSERT INTO video_exports VALUES (?, ?, ?) ON CONFLICT(job_id) DO UPDATE SET token_hash = excluded.token_hash, expires_at = excluded.expires_at", (job_id, token_hash, expires_at))
            return True

    def get_video_export(self, job_id):
        conn = self._get_sqlite_conn()
        with self._lock:
            row = conn.execute("SELECT * FROM video_exports WHERE job_id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

    def revoke_video_export(self, job_id):
        conn = self._get_sqlite_conn()
        with self._lock, conn:
            conn.execute("DELETE FROM video_exports WHERE job_id = ?", (job_id,))

    def set_video_share(self, job_id, session_id, token_hash, expires_at, validate_artifact=None):
        """Rotate under the same database reservation as retention cleanup.

        API issuance supplies validate_artifact, which checks the current file
        and ordinary retention or existing lease *inside* this transaction.
        """
        conn = self._get_sqlite_conn()
        with self._lock, conn:
            conn.execute("BEGIN IMMEDIATE;")
            conn.execute("DELETE FROM video_shares WHERE expires_at <= ? OR job_id NOT IN (SELECT job_id FROM jobs)", (time.time(),))
            job = conn.execute("SELECT * FROM jobs WHERE job_id = ? AND session_id = ?", (job_id, session_id)).fetchone()
            if not job or job["status"] != "succeeded" or job["job_type"] != "render":
                return False
            if validate_artifact is not None:
                previous = conn.execute("SELECT * FROM video_shares WHERE job_id = ?", (job_id,)).fetchone()
                validate_artifact(self._decode_job(job), dict(previous) if previous else None)
            conn.execute("INSERT INTO video_shares VALUES (?, ?, ?) ON CONFLICT(job_id) DO UPDATE SET token_hash = excluded.token_hash, expires_at = excluded.expires_at", (job_id, token_hash, expires_at))
            return True

    def get_video_share(self, job_id):
        conn = self._get_sqlite_conn()
        with self._lock:
            row = conn.execute("SELECT * FROM video_shares WHERE job_id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

    def revoke_video_share(self, job_id, session_id):
        conn = self._get_sqlite_conn()
        with self._lock, conn:
            conn.execute("BEGIN IMMEDIATE;")
            if not conn.execute("SELECT 1 FROM jobs WHERE job_id = ? AND session_id = ?", (job_id, session_id)).fetchone():
                return False
            conn.execute("DELETE FROM video_shares WHERE job_id = ?", (job_id,))
            return True

    def claim_next_job(self) -> Optional[Dict[str, Any]]:
        """Atomically claim the oldest queued render across worker processes."""
        if self._is_sqlite:
            conn = self._get_sqlite_conn()
            with self._lock:
                with conn:
                    conn.execute("BEGIN IMMEDIATE;")
                    row = conn.execute(
                        """
                        SELECT * FROM jobs
                        WHERE status = 'queued' AND job_type = 'render'
                        ORDER BY created_at ASC LIMIT 1;
                        """
                    ).fetchone()
                    if not row:
                        return None
                    now = now_utc_iso()
                    cursor = conn.execute(
                        "UPDATE jobs SET status = 'rendering', updated_at = ? WHERE job_id = ? AND status = 'queued';",
                        (now, row["job_id"]),
                    )
                    if cursor.rowcount != 1:
                        return None
                    job = self._decode_job(row)
                    job.update(status="rendering", updated_at=now)
                    return job
        return None


_DB_INSTANCE: Optional[Database] = None


def get_db(db_url: Optional[str] = None) -> Database:
    global _DB_INSTANCE
    if _DB_INSTANCE is None or (db_url and db_url != _DB_INSTANCE.db_url):
        _DB_INSTANCE = Database(db_url)
    return _DB_INSTANCE
