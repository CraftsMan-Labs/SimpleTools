from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from simpletools.context import ToolContext
from simpletools.registry import call_tool
from simpletools.responses.models import ToolResult

_LOG = logging.getLogger(__name__)


class ToolRunner:
    """Dispatches Hermes-style tools (subset) on a shared ToolContext."""

    def __init__(
        self,
        cwd: Path | None = None,
        data_dir: Path | None = None,
        on_delegate: Callable[[str, ToolContext], ToolResult] | None = None,
        message_senders: dict[str, Callable[[str, str, dict[str, Any]], ToolResult]] | None = None,
        enable_cron_scheduler: bool = False,
    ) -> None:
        self.ctx = ToolContext.default(cwd=cwd, data_dir=data_dir)
        self.ctx.on_delegate = on_delegate
        self.ctx.message_senders = message_senders or {}
        self._cron_stop = threading.Event()
        self._cron_thread: threading.Thread | None = None
        if enable_cron_scheduler:
            self._cron_thread = threading.Thread(target=self._cron_loop, daemon=True)
            self._cron_thread.start()

    def close(self) -> None:
        self._cron_stop.set()
        if self._cron_thread:
            self._cron_thread.join(timeout=2.0)

    def call(self, name: str, **kwargs: Any) -> ToolResult:
        if name not in ("read_file", "search_files"):
            from simpletools.tools import file_ops as _fo

            _fo.reset_file_read_loops(self.ctx)
        return call_tool(self.ctx, name, **kwargs)

    def _cron_loop(self) -> None:
        from simpletools.tools import cronjob as cronjob_mod

        while not self._cron_stop.wait(30.0):
            now = time.time()
            for job in self.ctx.store.cron_list():
                if not job.get("enabled"):
                    continue
                nxt = job.get("next_run")
                if nxt is None or float(nxt) > now:
                    continue
                try:
                    cronjob_mod.cronjob(self.ctx, action="run", job_id=str(job["id"]))
                except Exception:  # noqa: BLE001  # pragma: no cover — scheduler must survive arbitrary tool failures
                    _LOG.exception("cron job run failed", extra={"job_id": job.get("id")})
                # reschedule
                from datetime import datetime, timezone

                from croniter import croniter

                itr = croniter(str(job["spec"]), datetime.fromtimestamp(now, tz=timezone.utc))
                nxt2 = itr.get_next(datetime).timestamp()

                self.ctx.store.cron_upsert(
                    {
                        "id": job["id"],
                        "spec": job["spec"],
                        "payload_json": job["payload_json"],
                        "enabled": job["enabled"],
                        "last_run": now,
                        "next_run": nxt2,
                    }
                )
