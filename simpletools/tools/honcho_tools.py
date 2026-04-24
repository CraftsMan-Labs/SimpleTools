from __future__ import annotations

from simpletools.context import ToolContext
from simpletools.responses.models import HonchoResult


def honcho_profile(ctx: ToolContext) -> HonchoResult:
    card = ctx.store.honcho_profile_get()
    if not card:
        return {"ok": True, "card": {"facts": []}, "note": "empty profile"}
    return {"ok": True, "card": card}


def honcho_search(ctx: ToolContext, query: str, limit: int = 20) -> HonchoResult:
    rows = ctx.store.honcho_search(query, limit=limit)
    return {"ok": True, "excerpts": rows}


def honcho_context(ctx: ToolContext, query: str, limit: int = 8) -> HonchoResult:
    """Return concatenated excerpts (no extra LLM synthesis)."""
    rows = ctx.store.honcho_search(query, limit=limit)
    text = "\n---\n".join(r["content"] for r in rows)
    return {"ok": True, "synthesized_from_excerpts": text, "count": len(rows)}


def honcho_conclude(ctx: ToolContext, conclusion: str) -> HonchoResult:
    fid = ctx.store.honcho_fact_add(conclusion)
    # also merge into profile card list
    card = ctx.store.honcho_profile_get() or {"facts": []}
    facts = list(card.get("facts", []))
    facts.append(conclusion)
    card["facts"] = facts[-200:]
    ctx.store.honcho_profile_set(card)
    return {"ok": True, "id": fid}
