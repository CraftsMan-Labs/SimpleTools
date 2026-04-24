from __future__ import annotations

import os
import queue
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any, cast

from simpletools.context import ToolContext


@dataclass
class _Proc:
    session_id: str
    popen: subprocess.Popen[str]
    cmd: str
    cwd: str
    started: float
    q: queue.Queue[str | None] = field(default_factory=queue.Queue)
    out_buf: list[str] = field(default_factory=list)
    err_buf: list[str] = field(default_factory=list)
    pump_threads: list[threading.Thread] = field(default_factory=list)


def _registry(ctx: ToolContext) -> dict[str, _Proc]:
    return cast(dict[str, _Proc], ctx.process_registry)


def terminal(
    ctx: ToolContext,
    command: str,
    cwd: str | None = None,
    timeout: float = 180.0,
    background: bool = False,
) -> dict[str, Any]:
    """Run a shell command. Optional background mode returns session_id for `process`."""
    work = Path(cwd or ctx.cwd).resolve()
    if not str(work).startswith(str(ctx.cwd.resolve())):
        return {"ok": False, "error": "cwd escapes session cwd"}

    if not background:
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(work),
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ},
                check=False,
            )
            return {
                "ok": True,
                "exit_code": proc.returncode,
                "stdout": proc.stdout[-200_000:],
                "stderr": proc.stderr[-200_000:],
            }
        except subprocess.TimeoutExpired as e:
            return {
                "ok": False,
                "error": "timeout",
                "stdout": e.stdout or "",
                "stderr": e.stderr or "",
            }

    sid = "proc_" + uuid.uuid4().hex[:12]
    p = subprocess.Popen(
        command,
        shell=True,
        cwd=str(work),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env={**os.environ},
    )
    rec = _Proc(session_id=sid, popen=p, cmd=command, cwd=str(work), started=time.time())
    reg = _registry(ctx)

    def pump(stream: IO[str] | None, buf: list[str], label: str) -> None:
        if stream is None:
            return
        for line in iter(stream.readline, ""):
            if not line:
                break
            buf.append(line)
            rec.q.put(f"{label}:{line}")
        stream.close()

    t_out = threading.Thread(target=pump, args=(p.stdout, rec.out_buf, "stdout"), daemon=True)
    t_err = threading.Thread(target=pump, args=(p.stderr, rec.err_buf, "stderr"), daemon=True)
    t_out.start()
    t_err.start()
    rec.pump_threads.extend([t_out, t_err])
    reg[sid] = rec
    return {"ok": True, "session_id": sid, "pid": p.pid, "background": True}


def process(
    ctx: ToolContext,
    action: str,
    session_id: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Manage background processes: list, poll, log, wait, kill."""
    reg = _registry(ctx)
    action = (action or "").lower().strip()

    if action == "list":
        return {
            "ok": True,
            "processes": [
                {
                    "session_id": sid,
                    "pid": r.popen.pid,
                    "cmd": r.cmd,
                    "running": r.popen.poll() is None,
                }
                for sid, r in reg.items()
            ],
        }

    if not session_id:
        return {"ok": False, "error": "session_id required"}

    rec = reg.get(session_id)
    if not rec:
        return {"ok": False, "error": "unknown session_id"}

    if action == "poll":
        chunks: list[str] = []
        try:
            while True:
                item = rec.q.get_nowait()
                if item is not None:
                    chunks.append(item)
        except queue.Empty:
            pass
        return {
            "ok": True,
            "running": rec.popen.poll() is None,
            "exit_code": rec.popen.poll(),
            "new_output": "".join(chunks),
        }

    if action == "log":
        return {
            "ok": True,
            "stdout": "".join(rec.out_buf)[-200_000:],
            "stderr": "".join(rec.err_buf)[-200_000:],
            "exit_code": rec.popen.poll(),
        }

    if action == "wait":
        code = rec.popen.wait(timeout=timeout)
        return {
            "ok": True,
            "exit_code": code,
            "stdout": "".join(rec.out_buf),
            "stderr": "".join(rec.err_buf),
        }

    if action == "kill":
        rec.popen.kill()
        return {"ok": True, "killed": True}

    return {"ok": False, "error": f"unknown action: {action}"}
