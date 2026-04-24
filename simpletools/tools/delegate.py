from __future__ import annotations

from simpletools.context import ToolContext
from simpletools.responses.models import DelegateResult, DelegateRow


def delegate_task(ctx: ToolContext, tasks: list[str]) -> DelegateResult:
    """Run each subtask in an isolated ToolContext; results come from ctx.on_delegate if set."""
    if not tasks:
        return {"ok": False, "error": "no tasks"}
    handler = ctx.on_delegate
    if handler is None:
        return {
            "ok": False,
            "error": "on_delegate not configured",
            "hint": "Set ToolContext.on_delegate or ToolRunner(..., on_delegate=...) to a callable(prompt, child_ctx) -> dict.",
        }
    results: list[DelegateRow] = []
    for t in tasks:
        child = ctx.fork()
        results.append({"task": t, "result": handler(t, child)})
    return {"ok": True, "results": results}
