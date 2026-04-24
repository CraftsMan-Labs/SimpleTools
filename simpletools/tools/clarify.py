from __future__ import annotations

from typing import Any

from simpletools.context import ToolContext


def clarify(
    ctx: ToolContext,
    prompt: str,
    choices: list[str] | None = None,
) -> dict[str, Any]:
    """CLI: prompt user on stdin. Non-interactive: return pending payload (caller must supply answer out-of-band)."""
    import sys

    if not sys.stdin.isatty():
        return {
            "ok": False,
            "mode": "non_interactive",
            "prompt": prompt,
            "choices": choices,
            "message": "stdin is not a TTY; integrate clarify in your host UI.",
        }
    print(prompt)
    if choices:
        for i, c in enumerate(choices[:4], start=1):
            print(f"  {i}. {c}")
        raw = input("Pick number or type answer: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return {"ok": True, "answer": choices[int(raw) - 1]}
        return {"ok": True, "answer": raw}
    return {"ok": True, "answer": input("> ").strip()}
