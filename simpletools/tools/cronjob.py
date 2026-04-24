from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, cast

from croniter import croniter

from simpletools.context import ToolContext


def cronjob(
    ctx: ToolContext,
    action: str,
    job_id: str | None = None,
    spec: str | None = None,
    payload: dict[str, Any] | None = None,
    enabled: bool | None = None,
) -> dict[str, Any]:
    action = (action or "").lower()
    if action == "list":
        return {"ok": True, "jobs": ctx.store.cron_list()}

    if action == "create":
        jid = job_id or str(uuid.uuid4())
        if not spec or payload is None:
            return {"ok": False, "error": "spec and payload required"}
        itr = croniter(spec, datetime.now(tz=timezone.utc))
        nxt = itr.get_next(datetime).timestamp()
        ctx.store.cron_upsert(
            {
                "id": jid,
                "spec": spec,
                "payload_json": json.dumps(payload),
                "enabled": 1,
                "last_run": None,
                "next_run": nxt,
            }
        )
        return {"ok": True, "id": jid, "next_run": nxt}

    if action == "update":
        if not job_id:
            return {"ok": False, "error": "job_id required"}
        cur = ctx.store.cron_get(job_id)
        if not cur:
            return {"ok": False, "error": "not found"}
        effective_spec: str = str(spec or cur["spec"])
        payload = (
            payload
            if payload is not None
            else cast(dict[str, Any], json.loads(cur["payload_json"]))
        )
        en = enabled if enabled is not None else bool(cur["enabled"])
        itr = croniter(effective_spec, datetime.now(tz=timezone.utc))
        nxt = itr.get_next(datetime).timestamp()
        ctx.store.cron_upsert(
            {
                "id": job_id,
                "spec": effective_spec,
                "payload_json": json.dumps(payload),
                "enabled": 1 if en else 0,
                "last_run": cur.get("last_run"),
                "next_run": nxt if en else None,
            }
        )
        return {"ok": True, "id": job_id}

    if action in ("pause", "resume"):
        if not job_id:
            return {"ok": False, "error": "job_id required"}
        cur = ctx.store.cron_get(job_id)
        if not cur:
            return {"ok": False, "error": "not found"}
        en = action == "resume"
        nxt = None
        if en:
            itr = croniter(str(cur["spec"]), datetime.now(tz=timezone.utc))
            nxt = itr.get_next(datetime).timestamp()
        ctx.store.cron_upsert(
            {
                "id": job_id,
                "spec": cur["spec"],
                "payload_json": cur["payload_json"],
                "enabled": 1 if en else 0,
                "last_run": cur.get("last_run"),
                "next_run": nxt,
            }
        )
        return {"ok": True, "id": job_id, "enabled": en}

    if action == "remove":
        if not job_id:
            return {"ok": False, "error": "job_id required"}
        ctx.store.cron_delete(job_id)
        return {"ok": True, "removed": job_id}

    if action == "run":
        if not job_id:
            return {"ok": False, "error": "job_id required"}
        cur = ctx.store.cron_get(job_id)
        if not cur:
            return {"ok": False, "error": "not found"}
        raw_payload = json.loads(cur["payload_json"])
        if not isinstance(raw_payload, dict):
            return {"ok": False, "error": "invalid job payload"}
        return _run_payload(ctx, raw_payload)

    return {"ok": False, "error": f"unknown action {action}"}


def _run_payload(ctx: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    kind = payload.get("kind", "python")
    if kind == "python":
        from simpletools.tools.execute_code import execute_code

        return execute_code(ctx, str(payload.get("code", "")))
    if kind == "shell":
        from simpletools.tools.terminal import terminal

        return terminal(ctx, command=str(payload.get("command", "")))
    return {"ok": False, "error": f"unknown payload kind {kind}"}
