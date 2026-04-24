from __future__ import annotations

from typing import Any

from simpletools.context import ToolContext


def session_search(ctx: ToolContext, query: str, limit: int = 20) -> dict[str, Any]:
    """Search stored past session summaries (must be indexed via index_session)."""
    rows = ctx.store.session_search(query, limit=limit)
    return {"ok": True, "matches": rows}


def index_session(ctx: ToolContext, title: str, summary: str, body: str) -> dict[str, Any]:
    """Helper (not Hermes-named): persist this session for later session_search."""
    ctx.store.session_add(ctx.session_id, title, summary, body)
    return {"ok": True, "id": ctx.session_id}
