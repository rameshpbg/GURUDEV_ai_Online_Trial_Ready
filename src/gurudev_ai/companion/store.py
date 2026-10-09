"""Small, durable local breeder diary and task store. Never stores audio recordings."""
from __future__ import annotations
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import uuid


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    db = Path(path or os.getenv("GURUDEV_COMPANION_DB", "./gurudev_companion.sqlite3"))
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
        project TEXT NOT NULL, title TEXT NOT NULL,
        due_date TEXT, status TEXT NOT NULL DEFAULT 'open'
          CHECK (status IN ('open','done'))
    );
    CREATE TABLE IF NOT EXISTS observations (
        id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
        project TEXT NOT NULL, genotype TEXT NOT NULL,
        trait TEXT NOT NULL, value TEXT NOT NULL,
        environment TEXT NOT NULL, notes TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS chat_log (
        id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
        project TEXT NOT NULL, role TEXT NOT NULL,
        message TEXT NOT NULL
    );
    """)
    conn.commit()
    return conn


def _fetch(conn, sql, params=()):
    return [dict(x) for x in conn.execute(sql, params).fetchall()]


def list_tasks(conn, project="Rice", limit=100):
    return _fetch(conn, "SELECT * FROM tasks WHERE project=? ORDER BY (status='done') ASC, COALESCE(due_date,'9999-12-31') ASC,created_at DESC LIMIT ?", (project, limit))


def add_task(conn, project, title, due_date=None):
    ident = uuid.uuid4().hex[:12]
    conn.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?)", (ident, now(), project, title, due_date, "open"))
    conn.commit()
    return _fetch(conn, "SELECT * FROM tasks WHERE id=?", (ident,))[0]


def set_done(conn, project, task_id):
    result = conn.execute("UPDATE tasks SET status='done' WHERE id=? AND project=?", (task_id, project))
    conn.commit()
    return bool(result.rowcount)


def list_observations(conn, project="Rice", limit=100):
    return _fetch(conn, "SELECT * FROM observations WHERE project=? ORDER BY created_at DESC LIMIT ?", (project, limit))


def add_observation(conn, project, genotype, trait, value, environment="", notes=""):
    ident = uuid.uuid4().hex[:12]
    conn.execute("INSERT INTO observations VALUES (?,?,?,?,?,?,?,?)", (ident, now(), project, genotype, trait, str(value), environment, notes))
    conn.commit()
    return _fetch(conn, "SELECT * FROM observations WHERE id=?", (ident,))[0]


def log_chat(conn, project, role, message):
    conn.execute("INSERT INTO chat_log VALUES (?,?,?,?,?)", (uuid.uuid4().hex[:12], now(), project, role, message[:5000]))
    conn.commit()


def recent_chat(conn, project, limit=8):
    rows = _fetch(conn, "SELECT role,message FROM chat_log WHERE project=? ORDER BY created_at DESC LIMIT ?", (project, limit))
    return rows[::-1]
