from __future__ import annotations

from simpletools.context import ToolContext
from simpletools.responses.models import MemoryToolResult


def memory(
    ctx: ToolContext,
    action: str,
    target: str = "memory",
    content: str | None = None,
    old_text: str | None = None,
    new_content: str | None = None,
) -> MemoryToolResult:
    """
    Curated file-backed memory: MEMORY.md / USER.md (§-delimited) under data_dir/memories.

    Actions: add, replace, remove, read. Targets: memory | user.
    """
    action = (action or "").lower().strip()
    target = (target or "memory").lower().strip()
    if target not in ("memory", "user"):
        return {"ok": False, "error": "target must be 'memory' or 'user'"}
    st = ctx.get_memory_store()

    if action == "read":
        mem = st.read("memory")
        usr = st.read("user")
        return {"ok": True, "memory": mem["entries"], "user": usr["entries"]}

    if action == "add":
        if not content:
            return {"ok": False, "error": "content required for add"}
        return st.add(target, content)

    if action == "replace":
        nc = new_content if new_content is not None else content
        if not old_text or not nc:
            return {"ok": False, "error": "old_text and new_content (or content) required"}
        return st.replace(target, old_text, nc)

    if action == "remove":
        if not old_text:
            return {"ok": False, "error": "old_text required for remove"}
        return st.remove(target, old_text)

    return {"ok": False, "error": f"unknown action {action!r}; use add|replace|remove|read"}
