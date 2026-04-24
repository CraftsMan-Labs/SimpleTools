from __future__ import annotations

from collections.abc import Callable
from typing import Any

from simpletools.context import ToolContext
from simpletools.responses.models import ToolListingRow, ToolResult, UnknownToolResponse
from simpletools.tools import browser as browser_mod
from simpletools.tools import clarify as clarify_mod
from simpletools.tools import cronjob as cronjob_mod
from simpletools.tools import delegate as delegate_mod
from simpletools.tools import execute_code as execute_code_mod
from simpletools.tools import file_ops as file_ops_mod
from simpletools.tools import honcho_tools as honcho_mod
from simpletools.tools import memory_tool as memory_mod
from simpletools.tools import messaging as messaging_mod
from simpletools.tools import session_search_tool as session_mod
from simpletools.tools import skills_tools as skills_mod
from simpletools.tools import terminal as terminal_mod
from simpletools.tools import todo_tool as todo_mod
from simpletools.tools import vision as vision_mod
from simpletools.tools import web as web_mod

ToolFn = Callable[..., ToolResult]

TOOLS: dict[str, tuple[ToolFn, str]] = {
    "web_search": (
        web_mod.web_search,
        "Search the web (Tavily if TAVILY_API_KEY else DuckDuckGo instant).",
    ),
    "web_extract": (web_mod.web_extract, "Fetch URL and return stripped text."),
    "read_file": (file_ops_mod.read_file, "Read file with line numbers."),
    "write_file": (file_ops_mod.write_file, "Write file (overwrite)."),
    "search_files": (file_ops_mod.search_files, "Search by content or filename."),
    "patch": (
        file_ops_mod.patch,
        "Replace mode: fuzzy multi-strategy match (Hermes-style) or V4A patch mode=patch.",
    ),
    "terminal": (terminal_mod.terminal, "Run shell command (optional background)."),
    "process": (terminal_mod.process, "Manage background processes."),
    "browser_navigate": (browser_mod.browser_navigate, "Open URL (Playwright)."),
    "browser_snapshot": (browser_mod.browser_snapshot, "Accessibility-ish snapshot with @refs."),
    "browser_click": (browser_mod.browser_click, "Click element by @ref."),
    "browser_type": (browser_mod.browser_type, "Fill input by @ref."),
    "browser_press": (browser_mod.browser_press, "Press key."),
    "browser_scroll": (browser_mod.browser_scroll, "Scroll page."),
    "browser_back": (browser_mod.browser_back, "History back."),
    "browser_console": (browser_mod.browser_console, "Console messages since navigate."),
    "browser_get_images": (browser_mod.browser_get_images, "List images on page."),
    "browser_vision": (browser_mod.browser_vision, "Screenshot + vision model."),
    "browser_close": (browser_mod.browser_close, "Close browser."),
    "vision_analyze": (vision_mod.vision_analyze, "Vision on image file or base64."),
    "todo": (todo_mod.todo, "Session todo list."),
    "clarify": (clarify_mod.clarify, "Ask user (TTY) or return non-interactive payload."),
    "execute_code": (execute_code_mod.execute_code, "Run Python in subprocess."),
    "delegate_task": (delegate_mod.delegate_task, "Subtasks via on_delegate callback."),
    "memory": (
        memory_mod.memory,
        "File-backed MEMORY.md/USER.md (Hermes-style add/replace/remove/read).",
    ),
    "session_search": (session_mod.session_search, "Search indexed sessions."),
    "session_index": (
        session_mod.index_session,
        "Store session title/summary/body for session_search.",
    ),
    "cronjob": (cronjob_mod.cronjob, "Cron create/list/update/run/remove."),
    "send_message": (messaging_mod.send_message, "Pluggable outbound messaging."),
    "honcho_profile": (honcho_mod.honcho_profile, "Peer card JSON."),
    "honcho_search": (honcho_mod.honcho_search, "Search stored facts."),
    "honcho_context": (honcho_mod.honcho_context, "Concatenate matching facts."),
    "honcho_conclude": (honcho_mod.honcho_conclude, "Append conclusion to facts/profile."),
    "skills_list": (skills_mod.skills_list, "List skills."),
    "skill_view": (skills_mod.skill_view, "Read SKILL.md or file."),
    "skill_manage": (skills_mod.skill_manage, "Create/update/delete skill."),
}


def list_tools() -> list[ToolListingRow]:
    return [{"name": k, "description": v[1]} for k, v in sorted(TOOLS.items())]


def call_tool(ctx: ToolContext, name: str, **kwargs: Any) -> ToolResult:
    if name not in TOOLS:
        err: UnknownToolResponse = {"ok": False, "error": f"unknown tool: {name}"}
        return err
    fn = TOOLS[name][0]
    return fn(ctx, **kwargs)
