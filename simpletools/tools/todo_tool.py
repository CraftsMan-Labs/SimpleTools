from __future__ import annotations

from collections import OrderedDict
from typing import Any

from simpletools.context import ToolContext

VALID_STATUSES = frozenset({"pending", "in_progress", "completed", "cancelled"})


def _normalize_item(item: dict[str, Any]) -> dict[str, str]:
    item_id = str(item.get("id", "")).strip() or "?"
    text = (
        str(item.get("content", "")).strip()
        or str(item.get("label", "")).strip()
        or "(no description)"
    )
    status = str(item.get("status", "pending")).strip().lower()
    if status not in VALID_STATUSES:
        status = "pending"
    return {"id": item_id, "content": text, "status": status}


def _store(ctx: ToolContext) -> list[dict[str, str]]:
    return ctx.todo_items


def _write(ctx: ToolContext, todos: list[dict[str, Any]], merge: bool) -> list[dict[str, str]]:
    items = _store(ctx)
    if not merge:
        items.clear()
        items.extend(_normalize_item(t) for t in todos)
        return [i.copy() for i in items]

    od: OrderedDict[str, dict[str, str]] = OrderedDict((i["id"], i.copy()) for i in items)
    for t in todos:
        tid = str(t.get("id", "")).strip()
        if not tid:
            continue
        if tid in od:
            cur = od[tid]
            if t.get("content"):
                cur["content"] = str(t["content"]).strip()
            if t.get("status"):
                s = str(t["status"]).strip().lower()
                if s in VALID_STATUSES:
                    cur["status"] = s
        else:
            od[tid] = _normalize_item(t)
    items.clear()
    items.extend(od.values())
    return [i.copy() for i in items]


def todo(
    ctx: ToolContext,
    todos: list[dict[str, Any]] | None = None,
    merge: bool = False,
) -> dict[str, Any]:
    """Session todo list (Hermes-style: id, content, status; merge updates by id)."""
    if todos is None:
        items = [i.copy() for i in _store(ctx)]
    else:
        items = _write(ctx, todos, merge=merge)
    pending = sum(1 for i in items if i["status"] == "pending")
    inprog = sum(1 for i in items if i["status"] == "in_progress")
    done = sum(1 for i in items if i["status"] == "completed")
    cancelled = sum(1 for i in items if i["status"] == "cancelled")
    return {
        "ok": True,
        "todos": items,
        "summary": {
            "total": len(items),
            "pending": pending,
            "in_progress": inprog,
            "completed": done,
            "cancelled": cancelled,
        },
    }
