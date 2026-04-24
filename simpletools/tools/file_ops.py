from __future__ import annotations

import difflib
import json
import os
import re
import subprocess
from contextlib import suppress
from pathlib import Path

from simpletools.context import ToolContext
from simpletools.file_safety import is_blocked_device_path, sensitive_write_error
from simpletools.fuzzy_patch import fuzzy_find_and_replace
from simpletools.responses.models import (
    FileReadTrackerState,
    PatchReplaceOk,
    PatchResult,
    PyCompileLint,
    ReadFileOk,
    ReadFileResult,
    SearchFilesOk,
    SearchFilesResult,
    SearchMatch,
    ToolError,
    WriteFileOk,
    WriteFileResult,
)

_DEFAULT_MAX_READ_CHARS = 100_000
_LARGE_FILE_HINT_BYTES = 512_000
_READ_BLOCK_CONSECUTIVE = 4
_READ_WARN_CONSECUTIVE = 3
_LARGE_FILE_MIN_LINE_LIMIT = 200


def _max_read_chars() -> int:
    raw = os.environ.get("SIMPLETOOLS_FILE_READ_MAX_CHARS", "")
    try:
        v = int(raw)
    except ValueError:
        return _DEFAULT_MAX_READ_CHARS
    else:
        return v if v > 0 else _DEFAULT_MAX_READ_CHARS


def _tracker(ctx: ToolContext) -> FileReadTrackerState:
    return ctx.file_read_tracker


def reset_file_read_loops(ctx: ToolContext) -> None:
    """Reset consecutive read counter when non-read/search tools run."""
    t = _tracker(ctx)
    t["last_key"] = None
    t["consecutive"] = 0


def _resolve_under_cwd(ctx: ToolContext, rel: str) -> Path | None:
    p = (ctx.cwd / rel).resolve()
    if not str(p).startswith(str(ctx.cwd.resolve())):
        return None
    return p


def read_file(
    ctx: ToolContext,
    path: str,
    offset: int = 1,
    limit: int = 500,
) -> ReadFileResult:
    if is_blocked_device_path(path):
        return {
            "ok": False,
            "error": f"Cannot read {path!r}: device path would block or stream unbounded output.",
        }
    p = _resolve_under_cwd(ctx, path)
    if p is None:
        return {"ok": False, "error": "path escapes cwd"}
    if not p.is_file():
        return {"ok": False, "error": f"not found: {path}"}

    key = (str(p), offset, limit)
    tr = _tracker(ctx)
    cached = tr["dedup"].get(key)
    try:
        mtime_now = p.stat().st_mtime
    except OSError:
        mtime_now = None
    if cached is not None and mtime_now is not None and cached == mtime_now:
        return {
            "ok": True,
            "path": path,
            "dedup": True,
            "content": (
                "File unchanged since last read — reuse the earlier read_file output in this session."
            ),
        }

    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(0, offset - 1)
    chunk = lines[start : start + limit]
    out = "\n".join(f"{i + start + 1}|{line}" for i, line in enumerate(chunk))
    truncated = start + len(chunk) < len(lines)
    try:
        fsize = p.stat().st_size
    except OSError:
        fsize = 0

    maxc = _max_read_chars()
    if len(out) > maxc:
        return {
            "ok": False,
            "error": (
                f"Read produced {len(out):,} chars (limit {maxc:,}). Narrow with offset and limit."
            ),
            "total_lines": len(lines),
            "path": path,
        }

    read_key = ("read", path, offset, limit)
    if tr["last_key"] == read_key:
        tr["consecutive"] += 1
    else:
        tr["last_key"] = read_key
        tr["consecutive"] = 1
    cnt = tr["consecutive"]

    if mtime_now is not None:
        tr["dedup"][key] = mtime_now
        tr["read_ts"][str(p)] = mtime_now

    if cnt >= _READ_BLOCK_CONSECUTIVE:
        return {
            "ok": False,
            "error": (
                f"Blocked: same file region read {cnt} times consecutively without change. "
                "Use data you already have."
            ),
            "path": path,
        }

    result: ReadFileOk = {
        "ok": True,
        "path": str(p.relative_to(ctx.cwd)) if p.is_relative_to(ctx.cwd) else str(p),
        "content": out,
        "total_lines": len(lines),
        "truncated": truncated,
        "file_size": fsize,
    }
    if cnt >= _READ_WARN_CONSECUTIVE:
        result["_warning"] = (
            f"Same read ({path} lines {offset}-{offset + len(chunk) - 1}) repeated {cnt} times."
        )
    if fsize > _LARGE_FILE_HINT_BYTES and limit > _LARGE_FILE_MIN_LINE_LIMIT and truncated:
        result["_hint"] = (
            f"Large file (~{fsize:,} bytes). Prefer smaller offset/limit windows when possible."
        )
    return result


def write_file(ctx: ToolContext, path: str, content: str) -> WriteFileResult:
    se = sensitive_write_error(path)
    if se:
        return {"ok": False, "error": se}
    p = _resolve_under_cwd(ctx, path)
    if p is None:
        return {"ok": False, "error": "path escapes cwd"}
    msg = _stale_warning(ctx, p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    _bump_read_ts(ctx, p)
    out: WriteFileOk = {"ok": True, "path": str(p.relative_to(ctx.cwd))}
    if msg:
        out["_warning"] = msg
    return out


def _stale_warning(ctx: ToolContext, p: Path) -> str | None:
    tr = _tracker(ctx)
    prev = tr["read_ts"].get(str(p))
    if prev is None:
        return None
    try:
        cur = p.stat().st_mtime
    except OSError:
        return None
    if cur != prev:
        return (
            f"File {p.name} changed on disk since the last read_file in this session; "
            "content you saw may be stale."
        )
    return None


def _bump_read_ts(ctx: ToolContext, p: Path) -> None:
    with suppress(OSError):
        _tracker(ctx)["read_ts"][str(p)] = p.stat().st_mtime


def _lint_python(path: Path) -> PyCompileLint | None:
    if path.suffix != ".py":
        return None
    proc = subprocess.run(
        [os.environ.get("PYTHON_EXECUTABLE", "python3"), "-m", "py_compile", str(path)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return {
        "cmd": "py_compile",
        "exit_code": proc.returncode,
        "stderr": (proc.stderr or "")[-4000:],
    }


def patch(
    ctx: ToolContext,
    mode: str = "replace",
    path: str | None = None,
    old_string: str | None = None,
    new_string: str | None = None,
    replace_all: bool = False,
    patch: str | None = None,
    # legacy kwargs from earlier SimpleTools API
    old: str | None = None,
    new: str | None = None,
    count: int | None = None,
) -> PatchResult:
    mode = (mode or "replace").lower()
    if old_string is None and old is not None:
        old_string = old
    if new_string is None and new is not None:
        new_string = new
    if count is not None and count < 0:
        replace_all = True

    if mode == "patch":
        if not patch:
            return {"ok": False, "error": "patch content required"}
        from simpletools.v4a_patch import apply_v4a, parse_v4a

        for m in re.finditer(
            r"^\*\*\*\s+(?:Update|Add|Delete)\s+File:\s*(.+)$", patch, re.MULTILINE
        ):
            se = sensitive_write_error(m.group(1).strip())
            if se:
                return {"ok": False, "error": se}
        ops, err = parse_v4a(patch)
        if err:
            return {"ok": False, "error": err}
        res = apply_v4a(ops, ctx.cwd)
        if not res["ok"]:
            hint = ""
            if res["errors"] and any("Could not find" in e for e in res["errors"]):
                hint = "\n\n[Hint: re-read the file or widen the hunk context.]"
            return {
                "ok": False,
                "error": "; ".join(res["errors"]) + hint,
                "partial_diff": res.get("diff"),
            }
        return {"ok": True, "diff": res.get("diff"), "files": res.get("files")}

    if mode != "replace":
        return {"ok": False, "error": f"unknown mode {mode!r}"}
    if not path or old_string is None or new_string is None:
        return {"ok": False, "error": "path, old_string, and new_string required"}
    se = sensitive_write_error(path)
    if se:
        return {"ok": False, "error": se}
    p = _resolve_under_cwd(ctx, path)
    if p is None:
        return {"ok": False, "error": "path escapes cwd"}
    if not p.is_file():
        return {"ok": False, "error": f"not found: {path}"}

    text = p.read_text(encoding="utf-8", errors="replace")
    warn = _stale_warning(ctx, p)
    new_text, n, err = fuzzy_find_and_replace(text, old_string, new_string, replace_all=replace_all)
    if err:
        err_payload: ToolError = {"ok": False, "error": err}
        if "Could not find" in err or "matches" in err:
            err_payload["hint"] = "Re-read the file or use search_files to locate the text."
        return err_payload
    diff = "\n".join(
        difflib.unified_diff(
            text.splitlines(),
            new_text.splitlines(),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="",
        )
    )
    p.write_text(new_text, encoding="utf-8")
    _bump_read_ts(ctx, p)
    success_payload: PatchReplaceOk = {
        "ok": True,
        "path": path,
        "replacements": n,
        "diff": diff,
        "lint": _lint_python(p),
    }
    if warn:
        success_payload["_warning"] = warn
    return success_payload


def _require_rg_exit_ok(proc: subprocess.CompletedProcess[str]) -> None:
    if proc.returncode not in (0, 1):
        msg = proc.stderr or proc.stdout or ""
        raise RuntimeError(msg)


def search_files(
    ctx: ToolContext,
    pattern: str,
    target: str = "content",
    path: str = ".",
    glob: str | None = None,
    max_matches: int = 200,
) -> SearchFilesResult:
    root = _resolve_under_cwd(ctx, path)
    if root is None:
        return {"ok": False, "error": "path escapes cwd"}
    if not root.exists():
        return {"ok": False, "error": "search root missing"}

    if target == "name":
        name_hits: list[SearchMatch] = []
        for f in root.rglob(glob or "*"):
            if len(name_hits) >= max_matches:
                break
            if not f.is_file():
                continue
            if re.search(pattern, f.name, re.I):
                name_hits.append({"path": str(f.relative_to(ctx.cwd))})
        return {"ok": True, "mode": "name", "matches": name_hits}

    rg_hits: list[SearchMatch] = []
    try:
        cmd = ["rg", "--json", "--max-count", str(max_matches), pattern, str(root)]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        _require_rg_exit_ok(proc)
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") != "match":
                continue
            d = obj.get("data", {})
            ptext = d.get("path", {}).get("text", "")
            lines_data = d.get("lines", {})
            text = lines_data.get("text", "") if isinstance(lines_data, dict) else ""
            ln = d.get("line_number")
            rg_hits.append({"path": ptext, "line": ln, "text": text})
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError):
        return _search_files_python(root, ctx.cwd, pattern, glob, max_matches)
    else:
        return {"ok": True, "mode": "rg", "matches": rg_hits}


def _search_files_python(
    root: Path, cwd: Path, pattern: str, glob_pat: str | None, max_matches: int
) -> SearchFilesOk:
    rx = re.compile(pattern)
    matches: list[SearchMatch] = []
    for f in root.rglob(glob_pat or "*"):
        if len(matches) >= max_matches:
            break
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if rx.search(line):
                matches.append({"path": str(f.relative_to(cwd)), "line": i, "text": line[:500]})
                if len(matches) >= max_matches:
                    return {"ok": True, "mode": "python", "matches": matches}
    return {"ok": True, "mode": "python", "matches": matches}
