from __future__ import annotations

from collections.abc import Callable
from typing import Any

from simpletools.context import ToolContext

SenderFn = Callable[[str, str, dict[str, Any]], dict[str, Any]]


def send_message(
    ctx: ToolContext,
    action: str = "list",
    target: str | None = None,
    message: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    action=list -> registered channels.
    action=send -> dispatch via ctx.message_senders[target] if configured.
    """
    action = (action or "list").lower()
    senders: dict[str, SenderFn] = ctx.message_senders or {}

    if action == "list":
        return {
            "ok": True,
            "targets": sorted(senders.keys()),
            "note": "Register senders on ToolRunner(..., message_senders={'slack': fn})",
        }
    if action != "send":
        return {"ok": False, "error": f"unknown action {action}"}
    if not target or message is None:
        return {"ok": False, "error": "target and message required"}
    fn = senders.get(target)
    if not fn:
        return {
            "ok": False,
            "error": f"unknown target {target!r}",
            "targets": sorted(senders.keys()),
        }
    return {"ok": True, "delivery": fn(target, message, kwargs)}
