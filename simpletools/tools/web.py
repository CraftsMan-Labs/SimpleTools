from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from simpletools.context import ToolContext
from simpletools.http_client import get as http_get
from simpletools.http_client import post as http_post

_BACKEND_ERRORS = (
    httpx.HTTPError,
    ValueError,
    KeyError,
    TypeError,
)


def _has_env(name: str) -> bool:
    v = os.environ.get(name)
    return bool(v and str(v).strip())


def _firecrawl_config() -> tuple[str | None, str | None]:
    key = (os.environ.get("FIRECRAWL_API_KEY") or "").strip()
    base = (os.environ.get("FIRECRAWL_API_URL") or "https://api.firecrawl.dev").strip().rstrip("/")
    return (key or None), (base or None)


def _backend_chain() -> list[str]:
    """Hermes-style priority: optional SIMPLETOOLS_WEB_BACKEND, else firecrawl→tavily→exa (Parallel needs SDK)."""
    cfg = (os.environ.get("SIMPLETOOLS_WEB_BACKEND") or "").lower().strip()
    chain = ["firecrawl", "tavily", "exa"]
    avail: list[str] = []
    fc_key, _ = _firecrawl_config()
    if fc_key:
        avail.append("firecrawl")
    if _has_env("TAVILY_API_KEY"):
        avail.append("tavily")
    if _has_env("EXA_API_KEY"):
        avail.append("exa")
    if cfg in chain and cfg in avail:
        return [cfg] + [b for b in avail if b != cfg]
    return avail


def web_search(_ctx: ToolContext, query: str, max_results: int = 5) -> dict[str, Any]:
    query = (query or "").strip()
    if not query:
        return {"ok": False, "error": "empty query"}
    tried: list[str] = []
    last_err = "no provider keys configured"
    for backend in _backend_chain():
        tried.append(backend)
        try:
            if backend == "tavily":
                return _search_tavily(query, max_results)
            if backend == "exa":
                return _search_exa(query, max_results)
            if backend == "firecrawl":
                return _search_firecrawl(query, max_results)
        except _BACKEND_ERRORS as err:  # pragma: no cover
            last_err = str(err)
            continue
    out = _ddg_instant_search(query, max_results)
    note = (out.get("note") or "").strip()
    extra = f" Providers tried: {tried or ['none']}. Fallback reason: {last_err}."
    out["note"] = (note + extra).strip()
    return out


def _search_tavily(query: str, max_results: int) -> dict[str, Any]:
    key = os.environ["TAVILY_API_KEY"]
    r = http_post(
        "https://api.tavily.com/search",
        json={"api_key": key, "query": query, "max_results": max_results},
        timeout=60.0,
    )
    r.raise_for_status()
    data = r.json()
    results = []
    for item in data.get("results", [])[:max_results]:
        results.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "content": (item.get("content") or "")[:2000],
            }
        )
    return {"ok": True, "provider": "tavily", "results": results}


def _search_exa(query: str, max_results: int) -> dict[str, Any]:
    key = os.environ["EXA_API_KEY"]
    r = http_post(
        "https://api.exa.ai/search",
        headers={"x-api-key": key, "Content-Type": "application/json"},
        json={"query": query, "numResults": min(max_results, 25)},
        timeout=60.0,
    )
    r.raise_for_status()
    data = r.json()
    results = []
    for i, item in enumerate(data.get("results", [])[:max_results]):
        results.append(
            {
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "content": (" ".join(item.get("highlights") or []) or item.get("text", ""))[:2000],
                "position": i + 1,
            }
        )
    return {"ok": True, "provider": "exa", "results": results}


def _search_firecrawl(query: str, max_results: int) -> dict[str, Any]:
    key, base = _firecrawl_config()
    if not key:
        msg = "firecrawl key missing"
        raise RuntimeError(msg)
    r = http_post(
        f"{base}/v1/search",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"query": query, "limit": min(max_results, 20)},
        timeout=60.0,
    )
    r.raise_for_status()
    data = r.json()
    raw = data.get("data") or data.get("results") or []
    results: list[dict[str, Any]] = []
    for item in raw[:max_results]:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or item.get("sourceURL") or ""
        title = item.get("title") or ""
        desc = item.get("description") or item.get("markdown") or ""[:2000]
        results.append({"title": title, "url": url, "content": str(desc)[:2000]})
    return {"ok": True, "provider": "firecrawl", "results": results}


def _ddg_instant_search(query: str, max_results: int) -> dict[str, Any]:
    url = "https://api.duckduckgo.com/?format=json&no_html=1&skip_disambig=1&q=" + quote_plus(query)
    r = http_get(url, timeout=20.0)
    r.raise_for_status()
    data = r.json()

    results: list[dict[str, Any]] = []
    abstract = data.get("Abstract") or ""
    aurl = data.get("AbstractURL") or ""
    atitle = data.get("Heading") or query
    if abstract or aurl:
        results.append({"title": atitle, "url": aurl, "content": abstract[:2000]})

    for t in data.get("RelatedTopics", [])[: max_results - len(results)]:
        if isinstance(t, dict) and "Text" in t:
            text = str(t.get("Text", ""))
            href = str(t.get("FirstURL", ""))
            results.append({"title": text[:120], "url": href, "content": text})
        elif isinstance(t, dict) and "Topics" in t:
            for sub in t.get("Topics", [])[:2]:
                if isinstance(sub, dict):
                    text = str(sub.get("Text", ""))
                    href = str(sub.get("FirstURL", ""))
                    results.append({"title": text[:120], "url": href, "content": text})
        if len(results) >= max_results:
            break

    return {
        "ok": True,
        "provider": "duckduckgo_instant",
        "note": "Configure FIRECRAWL_API_KEY, TAVILY_API_KEY, or EXA_API_KEY for provider-backed search.",
        "results": results[:max_results],
    }


def web_extract(_ctx: ToolContext, url: str, max_chars: int = 50_000) -> dict[str, Any]:
    url = (url or "").strip()
    if not url:
        return {"ok": False, "error": "empty url"}

    for _backend in _backend_chain():
        try:
            if _backend == "tavily":
                return _extract_tavily(url, max_chars)
            if _backend == "exa":
                return _extract_exa(url, max_chars)
            if _backend == "firecrawl":
                return _extract_firecrawl(url, max_chars)
        except _BACKEND_ERRORS:
            continue
    return _extract_html_direct(url, max_chars)


def _extract_tavily(u: str, max_chars: int) -> dict[str, Any]:
    key = os.environ["TAVILY_API_KEY"]
    r = http_post(
        "https://api.tavily.com/extract",
        json={"api_key": key, "urls": [u]},
        timeout=90.0,
    )
    r.raise_for_status()
    data = r.json()
    docs = data.get("results") or []
    if not docs:
        msg = "no tavily results"
        raise ValueError(msg)
    text = (docs[0].get("raw_content") or docs[0].get("content") or "")[:max_chars]
    return {
        "ok": True,
        "provider": "tavily",
        "url": u,
        "markdown": text,
        "truncated": len(text) >= max_chars,
    }


def _extract_exa(u: str, max_chars: int) -> dict[str, Any]:
    key = os.environ["EXA_API_KEY"]
    r = http_post(
        "https://api.exa.ai/contents",
        headers={"x-api-key": key, "Content-Type": "application/json"},
        json={"urls": [u], "text": True},
        timeout=90.0,
    )
    r.raise_for_status()
    data = r.json()
    res = (data.get("results") or [{}])[0]
    text = (res.get("text") or "")[:max_chars]
    return {
        "ok": True,
        "provider": "exa",
        "url": u,
        "markdown": text,
        "truncated": len(text) >= max_chars,
    }


def _extract_firecrawl(u: str, max_chars: int) -> dict[str, Any]:
    key, base = _firecrawl_config()
    if not key:
        msg = "firecrawl key missing"
        raise RuntimeError(msg)
    r = http_post(
        f"{base}/v1/scrape",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"url": u, "formats": ["markdown"]},
        timeout=90.0,
    )
    r.raise_for_status()
    data = r.json()
    doc = data.get("data") or data.get("result") or {}
    text = (doc.get("markdown") or doc.get("content") or "")[:max_chars]
    return {
        "ok": True,
        "provider": "firecrawl",
        "url": u,
        "markdown": text,
        "truncated": len(text) >= max_chars,
    }


def _extract_html_direct(url: str, max_chars: int) -> dict[str, Any]:
    r = http_get(
        url, timeout=45.0, follow_redirects=True, headers={"User-Agent": "simpletools/0.1"}
    )
    r.raise_for_status()
    ctype = r.headers.get("content-type", "")
    raw = r.content
    if "pdf" in ctype.lower() or url.lower().endswith(".pdf"):
        err = "PDF not supported without a web backend."
        return {
            "ok": False,
            "error": err,
            "content_type": ctype,
        }
    text = _html_to_text(raw.decode(r.encoding or "utf-8", errors="replace"))[:max_chars]
    return {
        "ok": True,
        "provider": "direct_html",
        "url": url,
        "content_type": ctype,
        "markdown": text,
        "truncated": len(text) >= max_chars,
    }


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
