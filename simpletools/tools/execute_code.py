from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

from simpletools.context import ToolContext


def execute_code(ctx: ToolContext, code: str, timeout: float = 120.0) -> dict[str, Any]:
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
        return {
            "ok": True,
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-200_000:],
            "stderr": proc.stderr[-200_000:],
        }
    except subprocess.TimeoutExpired as e:
        return {"ok": False, "error": "timeout", "stdout": e.stdout or "", "stderr": e.stderr or ""}
    finally:
        if path:
            with suppress(OSError):
                Path(path).unlink(missing_ok=True)
