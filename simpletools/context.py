from __future__ import annotations

import os
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from simpletools.store import Store

if TYPE_CHECKING:
    from simpletools.memory_store import FileMemoryStore


SenderFn = Callable[[str, str, dict[str, Any]], dict[str, Any]]


def _default_read_tracker() -> dict[str, Any]:
    return {"last_key": None, "consecutive": 0, "dedup": {}, "read_ts": {}}


@dataclass
class ToolContext:
    """Per-session state: cwd, persistence, optional delegation fork."""

    cwd: Path
    data_dir: Path
    store: Store
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    on_delegate: Callable[[str, ToolContext], dict[str, Any]] | None = None
    _todo_items: list[dict[str, str]] = field(default_factory=list, repr=False)
    _process_registry: dict[str, Any] = field(default_factory=dict, repr=False)
    _file_read_tracker: dict[str, Any] = field(default_factory=_default_read_tracker, repr=False)
    _file_memory_store: FileMemoryStore | None = field(default=None, repr=False)
    _browser_session: dict[str, Any] = field(
        default_factory=lambda: {"page": None, "browser": None, "pw": None, "console": []},
        repr=False,
    )
    _message_senders: dict[str, SenderFn] = field(default_factory=dict, repr=False)

    @property
    def todo_items(self) -> list[dict[str, str]]:
        return self._todo_items

    @property
    def process_registry(self) -> dict[str, Any]:
        return self._process_registry

    @property
    def file_read_tracker(self) -> dict[str, Any]:
        return self._file_read_tracker

    @property
    def browser_session(self) -> dict[str, Any]:
        return self._browser_session

    def reset_browser_session(self) -> None:
        self._browser_session = {"page": None, "browser": None, "pw": None, "console": []}

    @property
    def message_senders(self) -> dict[str, SenderFn]:
        return self._message_senders

    @message_senders.setter
    def message_senders(self, value: dict[str, SenderFn]) -> None:
        self._message_senders = value

    def get_memory_store(self) -> FileMemoryStore:
        from simpletools.memory_store import FileMemoryStore

        if self._file_memory_store is None:
            self._file_memory_store = FileMemoryStore(self.data_dir / "memories")
        return self._file_memory_store

    @classmethod
    def default(cls, cwd: Path | None = None, data_dir: Path | None = None) -> ToolContext:
        root = Path(cwd or Path.cwd()).resolve()
        dd = (
            data_dir
            or Path(os.environ.get("SIMPLETOOLS_DATA_DIR", str(root / ".simpletools"))).resolve()
        )
        dd.mkdir(parents=True, exist_ok=True)
        store = Store(dd / "state.sqlite3")
        return cls(cwd=root, data_dir=dd, store=store)

    def fork(self, cwd: Path | None = None) -> ToolContext:
        """Isolated context for delegation (separate session_id, optional cwd)."""
        base = cwd or Path(tempfile.mkdtemp(prefix="simpletools-delegate-"))
        base.mkdir(parents=True, exist_ok=True)
        return ToolContext(
            cwd=Path(base).resolve(),
            data_dir=self.data_dir,
            store=self.store,
            session_id=str(uuid.uuid4()),
            on_delegate=self.on_delegate,
            _message_senders=dict(self._message_senders),
        )
