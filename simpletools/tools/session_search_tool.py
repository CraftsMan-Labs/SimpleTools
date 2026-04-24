from __future__ import annotations

from simpletools.context import ToolContext
from simpletools.responses.models import SessionIndexOk, SessionSearchResultOk


def session_search(ctx: ToolContext, query: str, limit: int = 20) -> SessionSearchResultOk:
    """Search stored past session summaries (must be indexed via index_session)."""
    rows = ctx.store.session_search(query, limit=limit)
    return {"ok": True, "matches": rows}


def index_session(ctx: ToolContext, title: str, summary: str, body: str) -> SessionIndexOk:
    """Persist this session for later session_search."""
    ctx.store.session_add(ctx.session_id, title, summary, body)
    return {"ok": True, "id": ctx.session_id}
