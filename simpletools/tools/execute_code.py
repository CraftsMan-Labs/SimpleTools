from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from contextlib import suppress
from pathlib import Path

from simpletools.context import ToolContext
from simpletools.responses.models import ExecuteCodeOk, ExecuteCodeResult, TerminalTimeout


def execute_code(ctx: ToolContext, code: str, timeout: float = 120.0) -> ExecuteCodeResult:
    """Run Python in a subprocess (isolated from caller). No tool bridge inside the snippet."""
    code = (code or "").strip()
    if not code:
        return {"ok": False, "error": "empty code"}
    path: str | None = None
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        path = f.name
    try:
        proc = subprocess.run(
            [sys.executable, path],
            cwd=str(ctx.cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ},
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        tout: TerminalTimeout = {
            "ok": False,
            "error": "timeout",
            "stdout": str(e.stdout or ""),
            "stderr": str(e.stderr or ""),
        }
        return tout
    else:
        ok: ExecuteCodeOk = {
            "ok": True,
            "exit_code": proc.returncode,
            "stdout": str(proc.stdout or "")[-200_000:],
            "stderr": str(proc.stderr or "")[-200_000:],
        }
        return ok
    finally:
        if path:
            with suppress(OSError):
                Path(path).unlink(missing_ok=True)
