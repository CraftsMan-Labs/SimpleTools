"""V4A unified-diff-style patch parse/apply (subset of Hermes patch_parser behavior)."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from simpletools.responses.models import V4ApplyResult


class OpKind(str, Enum):
    UPDATE = "update"
    ADD = "add"
    DELETE = "delete"
    MOVE = "move"


@dataclass
class HunkLine:
    prefix: str
    text: str


@dataclass
class Hunk:
    context_hint: str | None = None
    lines: list[HunkLine] = field(default_factory=list)


@dataclass
class PatchOp:
    kind: OpKind
    path: str
    new_path: str | None = None
    hunks: list[Hunk] = field(default_factory=list)


def parse_v4a(patch_text: str) -> tuple[list[PatchOp], str | None]:
    lines = patch_text.split("\n")
    start_idx = next(
        (i for i, ln in enumerate(lines) if "*** Begin Patch" in ln or "***Begin Patch" in ln), -1
    )
    end_idx = next(
        (i for i, ln in enumerate(lines) if "*** End Patch" in ln or "***End Patch" in ln),
        len(lines),
    )
    body = lines[start_idx + 1 : end_idx] if start_idx >= 0 else lines

    ops: list[PatchOp] = []
    cur: PatchOp | None = None
    hunk: Hunk | None = None
    i = 0
    while i < len(body):
        ln = body[i]
        um = re.match(r"\*\*\*\s*Update\s+File:\s*(.+)", ln, re.I)
        am = re.match(r"\*\*\*\s*Add\s+File:\s*(.+)", ln, re.I)
        dm = re.match(r"\*\*\*\s*Delete\s+File:\s*(.+)", ln, re.I)
        mm = re.match(r"\*\*\*\s*Move\s+File:\s*(.+?)\s*->\s*(.+)", ln, re.I)
        if um:
            if cur and hunk and hunk.lines:
                cur.hunks.append(hunk)
            if cur:
                ops.append(cur)
            cur = PatchOp(kind=OpKind.UPDATE, path=um.group(1).strip())
            hunk = None
        elif am:
            if cur and hunk and hunk.lines:
                cur.hunks.append(hunk)
            if cur:
                ops.append(cur)
            cur = PatchOp(kind=OpKind.ADD, path=am.group(1).strip())
            hunk = Hunk()
        elif dm:
            if cur and hunk and hunk.lines:
                cur.hunks.append(hunk)
            if cur:
                ops.append(cur)
            ops.append(PatchOp(kind=OpKind.DELETE, path=dm.group(1).strip()))
            cur = None
            hunk = None
        elif mm:
            if cur and hunk and hunk.lines:
                cur.hunks.append(hunk)
            if cur:
                ops.append(cur)
            ops.append(
                PatchOp(kind=OpKind.MOVE, path=mm.group(1).strip(), new_path=mm.group(2).strip())
            )
            cur = None
            hunk = None
        elif ln.startswith("@@") and cur:
            if hunk and hunk.lines:
                cur.hunks.append(hunk)
            hm = re.match(r"@@\s*(.+?)\s*@@", ln)
            hunk = Hunk(context_hint=hm.group(1) if hm else None)
        elif cur and ln and not ln.startswith("***"):
            if hunk is None:
                hunk = Hunk()
            if ln.startswith("+"):
                hunk.lines.append(HunkLine("+", ln[1:]))
            elif ln.startswith("-"):
                hunk.lines.append(HunkLine("-", ln[1:]))
            elif ln.startswith(" "):
                hunk.lines.append(HunkLine(" ", ln[1:]))
            elif ln.startswith("\\"):
                pass
            else:
                hunk.lines.append(HunkLine(" ", ln))
        i += 1
    if cur:
        if hunk and hunk.lines:
            cur.hunks.append(hunk)
        ops.append(cur)
    return ops, None


def apply_v4a(ops: list[PatchOp], cwd: Path) -> V4ApplyResult:
    from simpletools.fuzzy_patch import fuzzy_find_and_replace

    diffs: list[str] = []
    touched: list[str] = []
    errors: list[str] = []

    def resolve(p: str) -> Path:
        r = (cwd / p).resolve()
        if not str(r).startswith(str(cwd.resolve())):
            msg = "path escapes cwd"
            raise ValueError(msg)
        return r

    for op in ops:
        try:
            if op.kind == OpKind.ADD:
                lines = [ln.text for h in op.hunks for ln in h.lines if ln.prefix == "+"]
                rp = resolve(op.path)
                rp.parent.mkdir(parents=True, exist_ok=True)
                rp.write_text("\n".join(lines), encoding="utf-8")
                touched.append(op.path)
                diffs.append(f"+++ {op.path} (created)")
            elif op.kind == OpKind.DELETE:
                rp = resolve(op.path)
                if rp.is_file():
                    rp.unlink()
                touched.append(op.path)
            elif op.kind == OpKind.MOVE:
                a, b = resolve(op.path), resolve(op.new_path or "")
                b.parent.mkdir(parents=True, exist_ok=True)
                a.replace(b)
                touched.append(f"{op.path}->{op.new_path}")
            elif op.kind == OpKind.UPDATE:
                rp = resolve(op.path)
                if not rp.is_file():
                    errors.append(f"missing file {op.path}")
                    continue
                current = rp.read_text(encoding="utf-8", errors="replace")
                new_content = current
                for h in op.hunks:
                    search_lines: list[str] = []
                    replace_lines: list[str] = []
                    for ln in h.lines:
                        if ln.prefix == " ":
                            search_lines.append(ln.text)
                            replace_lines.append(ln.text)
                        elif ln.prefix == "-":
                            search_lines.append(ln.text)
                        elif ln.prefix == "+":
                            replace_lines.append(ln.text)
                    if search_lines:
                        sp = "\n".join(search_lines)
                        repl = "\n".join(replace_lines)
                        new_content, count, err = fuzzy_find_and_replace(
                            new_content, sp, repl, replace_all=False
                        )
                        if err and count == 0 and h.context_hint:
                            hint = h.context_hint
                            pos = new_content.find(hint)
                            if pos != -1:
                                ws, we = max(0, pos - 500), min(len(new_content), pos + 2000)
                                win = new_content[ws:we]
                                win2, c2, _ = fuzzy_find_and_replace(
                                    win, sp, repl, replace_all=False
                                )
                                if c2 > 0:
                                    new_content = new_content[:ws] + win2 + new_content[we:]
                                    err = None
                        if err:
                            errors.append(str(err))
                            break
                    else:
                        ins = "\n".join(replace_lines)
                        if h.context_hint and h.context_hint in new_content:
                            p = new_content.find(h.context_hint)
                            eol = new_content.find("\n", p)
                            if eol != -1:
                                new_content = (
                                    new_content[: eol + 1] + ins + "\n" + new_content[eol + 1 :]
                                )
                            else:
                                new_content = new_content.rstrip("\n") + "\n" + ins + "\n"
                        else:
                            new_content = new_content.rstrip("\n") + "\n" + ins + "\n"
                if errors:
                    break
                diff = "\n".join(
                    difflib.unified_diff(
                        current.splitlines(keepends=True),
                        new_content.splitlines(keepends=True),
                        fromfile=f"a/{op.path}",
                        tofile=f"b/{op.path}",
                    )
                )
                rp.write_text(new_content, encoding="utf-8")
                touched.append(op.path)
                diffs.append(diff)
        except (OSError, ValueError, RuntimeError) as err:  # pragma: no cover
            errors.append(f"{op.path}: {err}")
    return {"ok": not errors, "errors": errors, "files": touched, "diff": "\n".join(diffs)}
