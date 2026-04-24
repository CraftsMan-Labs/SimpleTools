from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, cast

from simpletools.responses.models import CronJobRow, HonchoCard, HonchoSearchRow, SessionIndexRow


class Store:
    """SQLite persistence for sessions, honcho, cron (memory/todos are Hermes-style elsewhere)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                  id TEXT PRIMARY KEY,
                  title TEXT,
                  summary TEXT,
                  body TEXT,
                  created REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS honcho_facts (
                  id TEXT PRIMARY KEY,
                  content TEXT NOT NULL,
                  created REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS honcho_profile (
                  id INTEGER PRIMARY KEY CHECK (id = 1),
                  card_json TEXT NOT NULL,
                  updated REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS cron_jobs (
                  id TEXT PRIMARY KEY,
                  spec TEXT NOT NULL,
                  payload_json TEXT NOT NULL,
                  enabled INTEGER NOT NULL DEFAULT 1,
                  last_run REAL,
                  next_run REAL
                );
                CREATE TABLE IF NOT EXISTS process_meta (
                  session_id TEXT PRIMARY KEY,
                  pid INTEGER,
                  cmd TEXT,
                  started REAL NOT NULL,
                  cwd TEXT
                );
                """
            )

    def session_add(self, sid: str, title: str, summary: str, body: str) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO sessions(id,title,summary,body,created) VALUES(?,?,?,?,?)",
                (sid, title, summary, body, time.time()),
            )

    def session_search(self, query: str, limit: int = 20) -> list[SessionIndexRow]:
        q = f"%{query}%"
        with self._conn() as c:
            rows = c.execute(
                """
                SELECT id, title, summary, body, created FROM sessions
                WHERE title LIKE ? OR summary LIKE ? OR body LIKE ?
                ORDER BY created DESC
                LIMIT ?
                """,
                (q, q, q, limit),
            ).fetchall()
            return [cast(SessionIndexRow, dict(r)) for r in rows]

    def honcho_profile_get(self) -> HonchoCard | None:
        with self._conn() as c:
            row = c.execute("SELECT card_json FROM honcho_profile WHERE id = 1").fetchone()
            if not row:
                return None
            return cast(HonchoCard, json.loads(str(row["card_json"])))

    def honcho_profile_set(self, card: HonchoCard) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO honcho_profile(id,card_json,updated) VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET card_json=excluded.card_json, updated=excluded.updated",
                (json.dumps(card), time.time()),
            )

    def honcho_fact_add(self, content: str) -> str:
        import uuid

        fid = str(uuid.uuid4())
        with self._conn() as c:
            c.execute(
                "INSERT INTO honcho_facts(id,content,created) VALUES(?,?,?)",
                (fid, content, time.time()),
            )
        return fid

    def honcho_search(self, query: str, limit: int = 20) -> list[HonchoSearchRow]:
        q = f"%{query}%"
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, content, created FROM honcho_facts WHERE content LIKE ? ORDER BY created DESC LIMIT ?",
                (q, limit),
            ).fetchall()
            return [cast(HonchoSearchRow, dict(r)) for r in rows]

    def cron_list(self) -> list[CronJobRow]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM cron_jobs ORDER BY id").fetchall()
            return [cast(CronJobRow, dict(r)) for r in rows]

    def cron_upsert(self, job: dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT INTO cron_jobs(id,spec,payload_json,enabled,last_run,next_run)
                   VALUES(:id,:spec,:payload_json,:enabled,:last_run,:next_run)
                   ON CONFLICT(id) DO UPDATE SET
                   spec=excluded.spec, payload_json=excluded.payload_json, enabled=excluded.enabled,
                   last_run=excluded.last_run, next_run=excluded.next_run""",
                job,
            )

    def cron_get(self, jid: str) -> CronJobRow | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM cron_jobs WHERE id = ?", (jid,)).fetchone()
            return cast(CronJobRow, dict(row)) if row else None

    def cron_delete(self, jid: str) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM cron_jobs WHERE id = ?", (jid,))
