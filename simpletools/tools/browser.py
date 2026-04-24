from __future__ import annotations

import base64
import logging
from typing import Any, cast

from simpletools.context import ToolContext
from simpletools.responses.models import BrowserImageRow, BrowserResult, BrowserSessionState

_LOG = logging.getLogger(__name__)
_NAVIGATE_FIRST_MSG = "call browser_navigate first"
_GOTO_TIMEOUT_MS = 60_000
_CLICK_FILL_TIMEOUT_MS = 15_000
_DEFAULT_SCROLL_PX = 400


def _session(ctx: ToolContext) -> BrowserSessionState:
    return ctx.browser_session


def _require_playwright() -> Any:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as err:  # pragma: no cover
        msg = "Install browser extra: pip install 'simpletools[browser]' && playwright install chromium"
        raise RuntimeError(msg) from err
    return sync_playwright


def _ensure_page(ctx: ToolContext) -> Any:
    s = _session(ctx)
    if s.get("page") is not None:
        return s["page"]
    sync_playwright = _require_playwright()
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()

    def on_console(msg: object) -> None:
        mtype = getattr(msg, "type", "")
        mtext = getattr(msg, "text", "")
        s["console"].append({"type": mtype, "text": mtext})

    page.on("console", on_console)
    s.update({"pw": pw, "browser": browser, "page": page, "console": []})
    return page


def browser_navigate(ctx: ToolContext, url: str) -> BrowserResult:
    page = _ensure_page(ctx)
    page.goto(url, wait_until="domcontentloaded", timeout=_GOTO_TIMEOUT_MS)
    return {"ok": True, "url": page.url, "title": page.title()}


def browser_snapshot(ctx: ToolContext, full: bool = False) -> BrowserResult:
    s = _session(ctx)
    page = s.get("page")
    if page is None:
        return {"ok": False, "error": _NAVIGATE_FIRST_MSG}
    raw_items = page.evaluate(
        """(full) => {
  const sel = full
    ? 'a,button,input,textarea,select,[role="button"],[tabindex]:not([tabindex="-1"])'
    : 'a,button,input,textarea,select,[role="button"]';
  const nodes = Array.from(document.querySelectorAll(sel));
  let i = 0;
  return nodes.map(el => {
    const ref = 'e' + (++i);
    el.dataset.stRef = ref;
    const name = (el.getAttribute('aria-label') || el.innerText || el.getAttribute('placeholder') || '').trim().slice(0, 200);
    return { ref, tag: el.tagName.toLowerCase(), type: el.getAttribute('type')||'', name };
  });
}""",
        full,
    )
    items = cast(list[dict[str, Any]], raw_items)
    lines = [
        f"[{it['tag']}{('#' + it['type']) if it['type'] else ''}] @{it['ref']} {it['name']}".strip()
        for it in items
    ]
    return {"ok": True, "snapshot": "\n".join(lines)}


def browser_click(ctx: ToolContext, ref: str) -> BrowserResult:
    page = _session(ctx).get("page")
    if page is None:
        return {"ok": False, "error": _NAVIGATE_FIRST_MSG}
    ref_clean = ref.removeprefix("@")
    page.locator(f"[data-st-ref='{ref_clean}']").click(timeout=_CLICK_FILL_TIMEOUT_MS)
    return {"ok": True}


def browser_type(ctx: ToolContext, ref: str, text: str) -> BrowserResult:
    page = _session(ctx).get("page")
    if page is None:
        return {"ok": False, "error": _NAVIGATE_FIRST_MSG}
    ref_clean = ref.removeprefix("@")
    loc = page.locator(f"[data-st-ref='{ref_clean}']")
    loc.fill("")
    loc.fill(text, timeout=_CLICK_FILL_TIMEOUT_MS)
    return {"ok": True}


def browser_press(ctx: ToolContext, key: str) -> BrowserResult:
    page = _session(ctx).get("page")
    if page is None:
        return {"ok": False, "error": _NAVIGATE_FIRST_MSG}
    page.keyboard.press(key)
    return {"ok": True}


def browser_scroll(
    ctx: ToolContext, direction: str = "down", amount: int = _DEFAULT_SCROLL_PX
) -> BrowserResult:
    page = _session(ctx).get("page")
    if page is None:
        return {"ok": False, "error": _NAVIGATE_FIRST_MSG}
    dy = amount if direction.lower() == "down" else -amount
    page.mouse.wheel(0, dy)
    return {"ok": True}


def browser_back(ctx: ToolContext) -> BrowserResult:
    page = _session(ctx).get("page")
    if page is None:
        return {"ok": False, "error": _NAVIGATE_FIRST_MSG}
    page.go_back()
    return {"ok": True, "url": page.url}


def browser_console(ctx: ToolContext) -> BrowserResult:
    s = _session(ctx)
    if s.get("page") is None:
        return {"ok": False, "error": _NAVIGATE_FIRST_MSG}
    return {"ok": True, "messages": list(s.get("console", []))}


def browser_get_images(ctx: ToolContext) -> BrowserResult:
    page = _session(ctx).get("page")
    if page is None:
        return {"ok": False, "error": _NAVIGATE_FIRST_MSG}
    raw = page.evaluate(
        """() => Array.from(document.images).map(i => ({src: i.currentSrc || i.src, alt: i.alt || ''}))"""
    )
    data = cast(list[BrowserImageRow], raw)
    return {"ok": True, "images": data}


def browser_vision(ctx: ToolContext, question: str) -> BrowserResult:
    from simpletools.tools import vision as vision_mod

    page = _session(ctx).get("page")
    if page is None:
        return {"ok": False, "error": _NAVIGATE_FIRST_MSG}
    png = page.screenshot(type="png")
    b64 = base64.b64encode(png).decode("ascii")
    return vision_mod.vision_analyze(ctx, image_base64=b64, question=question)


def browser_close(ctx: ToolContext) -> BrowserResult:
    s = _session(ctx)
    try:
        if s.get("page"):
            s["page"].close()
        if s.get("browser"):
            s["browser"].close()
        if s.get("pw"):
            s["pw"].stop()
    except (OSError, RuntimeError) as err:
        _LOG.warning("browser_close cleanup: %s", err)
    finally:
        ctx.reset_browser_session()
    return {"ok": True}
