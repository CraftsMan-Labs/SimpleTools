from __future__ import annotations

import os
import re
from pathlib import Path
from typing import cast

from simpletools.context import ToolContext
from simpletools.responses.models import SkillRow, SkillsResult


def _skills_dir(ctx: ToolContext) -> Path:
    raw = os.environ.get("SIMPLETOOLS_SKILLS_DIR", str(ctx.data_dir / "skills"))
    p = Path(raw).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def skills_list(ctx: ToolContext) -> SkillsResult:
    root = _skills_dir(ctx)
    out: list[dict[str, str]] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        md = d / "SKILL.md"
        desc = ""
        if md.is_file():
            head = md.read_text(encoding="utf-8", errors="replace")[:800]
            m = re.search(r"description:\s*(.+)", head, re.I)
            if m:
                desc = m.group(1).strip()
        out.append({"name": d.name, "description": desc})
    return {"ok": True, "skills": cast(list[SkillRow], out)}


def skill_view(ctx: ToolContext, name: str, file: str | None = None) -> SkillsResult:
    root = _skills_dir(ctx) / name
    if not root.is_dir():
        return {"ok": False, "error": f"unknown skill {name!r}"}
    if file:
        p = (root / file).resolve()
        if not str(p).startswith(str(root.resolve())):
            return {"ok": False, "error": "path escapes skill dir"}
        return {
            "ok": True,
            "path": file,
            "content": p.read_text(encoding="utf-8", errors="replace"),
        }
    md = root / "SKILL.md"
    if not md.is_file():
        return {"ok": False, "error": "SKILL.md missing"}
    return {"ok": True, "skill": name, "SKILL.md": md.read_text(encoding="utf-8", errors="replace")}


def skill_manage(
    ctx: ToolContext,
    action: str,
    name: str,
    content: str | None = None,
) -> SkillsResult:
    action = (action or "").lower()
    root = _skills_dir(ctx) / name
    if action == "create":
        if root.exists():
            return {"ok": False, "error": "already exists"}
        root.mkdir(parents=True)
        body = content or "---\nname: " + name + "\ndescription: New skill\n---\n\n# " + name + "\n"
        (root / "SKILL.md").write_text(body, encoding="utf-8")
        return {"ok": True, "skill": name}
    if action == "update":
        if not root.is_dir():
            return {"ok": False, "error": "not found"}
        if content is None:
            return {"ok": False, "error": "content required"}
        (root / "SKILL.md").write_text(content, encoding="utf-8")
        return {"ok": True, "skill": name}
    if action == "delete":
        if not root.is_dir():
            return {"ok": False, "error": "not found"}
        import shutil

        shutil.rmtree(root)
        return {"ok": True, "deleted": name}
    return {"ok": False, "error": f"unknown action {action}"}
