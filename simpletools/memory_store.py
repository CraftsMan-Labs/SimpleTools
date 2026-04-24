"""File-backed curated memory (MEMORY.md / USER.md, §-delimited entries)."""

from __future__ import annotations

import fcntl
import os
import re
import tempfile
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any

from simpletools.responses.models import (
    MemoryStoreMutation,
    MemoryStoreReadOk,
)

ENTRY = "\n§\n"

_THREATS: list[tuple[str, str]] = [
    (r"ignore\s+(previous|all|above|prior)\s+instructions", "prompt_injection"),
    (r"you\s+are\s+now\s+", "role_hijack"),
    (r"do\s+not\s+tell\s+the\s+user", "deception_hide"),
    (r"system\s+prompt\s+override", "sys_prompt_override"),
    (r"disregard\s+(your|all|any)\s+(instructions|rules|guidelines)", "disregard_rules"),
    (r"curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)", "exfil_curl"),
    (r"wget\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)", "exfil_wget"),
    (r"cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass|\.npmrc|\.pypirc)", "read_secrets"),
    (r"authorized_keys", "ssh_backdoor"),
    (r"\$HOME/\.ssh|\~/\.ssh", "ssh_access"),
]

_INVISIBLE = {
    "\u200b",
    "\u200c",
    "\u200d",
    "\u2060",
    "\ufeff",
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",
}


def _scan(content: str) -> str | None:
    for ch in _INVISIBLE:
        if ch in content:
            return f"Blocked: invisible unicode U+{ord(ch):04X}."
    for pat, pid in _THREATS:
        if re.search(pat, content, re.I):
            return f"Blocked: pattern '{pid}'."
    return None


class FileMemoryStore:
    def __init__(self, base_dir: Path, memory_limit: int = 2200, user_limit: int = 1375) -> None:
        self._dir = base_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._mem_limit = memory_limit
        self._user_limit = user_limit

    def _path(self, target: str) -> Path:
        return self._dir / ("USER.md" if target == "user" else "MEMORY.md")

    @staticmethod
    @contextmanager
    def _lock(path: Path) -> Any:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_suffix(path.suffix + ".lock")
        with lock_path.open("w") as lock_fh:
            fd = lock_fh.fileno()
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)

    @staticmethod
    def _read_entries(path: Path) -> list[str]:
        if not path.is_file():
            return []
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
        if not raw:
            return []
        parts = [p.strip() for p in raw.split(ENTRY) if p.strip()]
        return list(dict.fromkeys(parts))

    @staticmethod
    def _write_entries(path: Path, entries: list[str]) -> None:
        body = ENTRY.join(entries) if entries else ""
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp", prefix=".mem_")
        tmp_path = Path(tmp)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(body)
                fh.flush()
                os.fsync(fh.fileno())
            tmp_path.replace(path)
        except BaseException:
            with suppress(OSError):
                tmp_path.unlink(missing_ok=True)
            raise

    def _limit(self, target: str) -> int:
        return self._user_limit if target == "user" else self._mem_limit

    def read(self, target: str) -> MemoryStoreReadOk:
        path = self._path(target)
        entries = self._read_entries(path)
        return {"ok": True, "target": target, "entries": entries, "rendered": ENTRY.join(entries)}

    def add(self, target: str, content: str) -> MemoryStoreMutation:
        content = content.strip()
        if not content:
            return {"ok": False, "error": "empty content"}
        err = _scan(content)
        if err:
            return {"ok": False, "error": err}
        path = self._path(target)
        with self._lock(path):
            entries = self._read_entries(path)
            if content in entries:
                return {"ok": True, "message": "duplicate skipped", "entries": entries}
            trial = [*entries, content]
            total = len(ENTRY.join(trial))
            if total > self._limit(target):
                return {
                    "ok": False,
                    "error": f"Would exceed {self._limit(target)} chars (currently ~{len(ENTRY.join(entries))}).",
                }
            self._write_entries(path, trial)
            entries = trial
        return {"ok": True, "entries": entries}

    def replace(self, target: str, old_text: str, new_content: str) -> MemoryStoreMutation:
        old_text = old_text.strip()
        new_content = new_content.strip()
        if not old_text or not new_content:
            return {"ok": False, "error": "old_text and new_content required"}
        err = _scan(new_content)
        if err:
            return {"ok": False, "error": err}
        path = self._path(target)
        with self._lock(path):
            entries = self._read_entries(path)
            matches = [(i, e) for i, e in enumerate(entries) if old_text in e]
            if not matches:
                return {"ok": False, "error": f"No entry matched {old_text!r}."}
            if len({e for _, e in matches}) > 1:
                return {
                    "ok": False,
                    "error": "Multiple distinct entries matched.",
                    "matches": [e[:80] for _, e in matches],
                }
            idx = matches[0][0]
            trial = entries.copy()
            trial[idx] = new_content
            if len(ENTRY.join(trial)) > self._limit(target):
                return {"ok": False, "error": "Replacement exceeds char budget."}
            self._write_entries(path, trial)
            entries = trial
        return {"ok": True, "entries": entries}

    def remove(self, target: str, old_text: str) -> MemoryStoreMutation:
        old_text = old_text.strip()
        if not old_text:
            return {"ok": False, "error": "old_text required"}
        path = self._path(target)
        with self._lock(path):
            entries = self._read_entries(path)
            matches = [(i, e) for i, e in enumerate(entries) if old_text in e]
            if not matches:
                return {"ok": False, "error": f"No entry matched {old_text!r}."}
            if len({e for _, e in matches}) > 1:
                return {"ok": False, "error": "Multiple distinct entries matched."}
            entries.pop(matches[0][0])
            self._write_entries(path, entries)
        return {"ok": True, "entries": entries}
