from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

from simpletools.context import ToolContext
from simpletools.http_client import post as http_post

_HTTP_CLIENT_ERROR = 400


def vision_analyze(
    ctx: ToolContext,
    question: str,
    image_path: str | None = None,
    image_base64: str | None = None,
) -> dict[str, Any]:
    """Analyze an image with an OpenAI-compatible vision endpoint."""
    key = os.environ.get("OPENAI_API_KEY")
    base = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
    model = os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini")
    if not key:
        return {"ok": False, "error": "Set OPENAI_API_KEY for vision_analyze."}

    if image_base64:
        b64 = image_base64
        mime = "image/png"
    elif image_path:
        p = (ctx.cwd / image_path).resolve()
        if not str(p).startswith(str(ctx.cwd.resolve())):
            return {"ok": False, "error": "path escapes cwd"}
        raw = Path(p).read_bytes()
        b64 = base64.b64encode(raw).decode("ascii")
        mime = "image/jpeg" if str(p).lower().endswith((".jpg", ".jpeg")) else "image/png"
    else:
        return {"ok": False, "error": "provide image_path or image_base64"}

    url = base.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            }
        ],
        "max_tokens": 1024,
    }
    r = http_post(
        url,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=120.0,
    )
    if r.status_code >= _HTTP_CLIENT_ERROR:
        return {"ok": False, "error": r.text, "status": r.status_code}
    data = r.json()
    text = data["choices"][0]["message"]["content"]
    return {"ok": True, "answer": text}
