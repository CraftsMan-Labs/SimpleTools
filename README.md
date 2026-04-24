# simpleAgentTools

[![GitHub Stars](https://img.shields.io/github/stars/CraftsMan-Labs/SimpleTools?style=flat-square)](https://github.com/CraftsMan-Labs/SimpleTools/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/CraftsMan-Labs/SimpleTools?style=flat-square)](https://github.com/CraftsMan-Labs/SimpleTools/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/CraftsMan-Labs/SimpleTools?style=flat-square)](https://github.com/CraftsMan-Labs/SimpleTools/issues)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](LICENSE)

[![PyPI Version](https://img.shields.io/pypi/v/simpleagenttools?style=flat-square&logo=python)](https://pypi.org/project/simpleagenttools/)
[![PyPI - Python](https://img.shields.io/pypi/pyversions/simpleagenttools?style=flat-square&logo=python)](https://pypi.org/project/simpleagenttools/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/simpleagenttools?style=flat-square)](https://pypi.org/project/simpleagenttools/)

**Stats:** **36** built-in tools (see [Agent toolkit](#agent-toolkit)) · **Python 3.10+** · **Apache-2.0** · PyPI [`simpleagenttools`](https://pypi.org/project/simpleagenttools/) · `pip install simpleAgentTools`

Python agent tools: web, browser (optional Playwright), terminal, files, vision (OpenAI-compatible), todo, clarify, code execution, delegation (callback), memory, session search, cron, messaging hooks, Honcho-like local profile, and skills on disk.

This repository is the **simpleAgentTools** distribution on PyPI ([project page](https://pypi.org/project/simpleagenttools/) — PyPI normalizes the name to lowercase in URLs). The importable Python package is **`simpletools`**. Builds and installs are driven by **[uv](https://docs.astral.sh/uv/)**.

## Agent toolkit

Tools are registered in [`simpletools/registry.py`](simpletools/registry.py) (`TOOLS`). Host code wires a [`ToolContext`](simpletools/context.py) and calls [`ToolRunner.call`](simpletools/runner.py) or [`registry.call_tool`](simpletools/registry.py). The CLI can list the same names: `simpleAgentTools list` (the `simpletools` command is an alias).

| Tool | What it does |
| --- | --- |
| `browser_back` | History back. |
| `browser_click` | Click element by `@ref`. |
| `browser_close` | Close browser. |
| `browser_console` | Console messages since navigate. |
| `browser_get_images` | List images on page. |
| `browser_navigate` | Open URL (Playwright). |
| `browser_press` | Press key. |
| `browser_scroll` | Scroll page. |
| `browser_snapshot` | Accessibility-ish snapshot with `@refs`. |
| `browser_type` | Fill input by `@ref`. |
| `browser_vision` | Screenshot + vision model. |
| `clarify` | Ask user (TTY) or return non-interactive payload. |
| `cronjob` | Cron create/list/update/run/remove. |
| `delegate_task` | Subtasks via `on_delegate` callback. |
| `execute_code` | Run Python in subprocess. |
| `honcho_conclude` | Append conclusion to facts/profile. |
| `honcho_context` | Concatenate matching facts. |
| `honcho_profile` | Peer card JSON. |
| `honcho_search` | Search stored facts. |
| `memory` | File-backed `MEMORY.md`/`USER.md` (add/replace/remove/read). |
| `patch` | Replace mode: fuzzy multi-strategy match or V4A `mode=patch`. |
| `process` | Manage background processes. |
| `read_file` | Read file with line numbers. |
| `search_files` | Search by content or filename. |
| `send_message` | Pluggable outbound messaging. |
| `session_index` | Store session title/summary/body for `session_search`. |
| `session_search` | Search indexed sessions. |
| `skill_manage` | Create/update/delete skill. |
| `skill_view` | Read `SKILL.md` or file. |
| `skills_list` | List skills. |
| `terminal` | Run shell command (optional background). |
| `todo` | Session todo list. |
| `vision_analyze` | Vision on image file or base64. |
| `web_extract` | Fetch URL and return stripped text. |
| `web_search` | Search the web (Tavily if `TAVILY_API_KEY` else DuckDuckGo instant). |
| `write_file` | Write file (overwrite). |

## Development with uv

```bash
git clone <repo-url> && cd <repo-directory>
uv sync --all-extras          # install runtime + browser extra + dev (pytest, ruff)
uv run python -m unittest discover -s tests -v
uv run ruff check simpletools tests
uv run ruff format simpletools tests
```

Lockfile: **`uv.lock`** is committed so CI and installs stay reproducible. Refresh after dependency edits:

```bash
uv lock
```

## Install (users)

```bash
pip install simpleAgentTools
```

`pip` treats the PyPI name case-insensitively; the same package is available as `pip install simpleagenttools`.

```bash
uv tool install simpleAgentTools
# or
uv pip install simpleAgentTools
# optional browser automation
uv pip install "simpleAgentTools[browser]"
playwright install chromium
```

## Usage

```python
from pathlib import Path
from simpletools import ToolRunner

r = ToolRunner(cwd=Path("."))
print(r.call("web_search", query="Python 3.12"))
print(r.call("memory", action="add", target="memory", content="Uses uv for packaging"))
```

CLI:

```bash
simpleAgentTools list
simpleAgentTools call memory --args '{"action":"read"}'
```

## Configuration

Environment highlights: `FIRECRAWL_API_KEY` / `FIRECRAWL_API_URL`, `TAVILY_API_KEY`, `EXA_API_KEY`, optional `SIMPLETOOLS_WEB_BACKEND` (`firecrawl`, `tavily`, or `exa`), `OPENAI_*` for vision, `SIMPLETOOLS_DATA_DIR`, `SIMPLETOOLS_FILE_READ_MAX_CHARS`, `SIMPLETOOLS_SKILLS_DIR`.

**Behavior notes:** multi-strategy fuzzy `patch` replace, optional `mode="patch"` V4A hunks, file read guards (device blocklist, char cap, repeat-read loop), configurable web search backends, file-backed `memory` (`memories/MEMORY.md` + `USER.md`, `§` entries), session todos with `content`/`status`.

## Acknowledgments

**All of the tools in this repository are inspired by Hermes from [NousResearch](https://nousresearch.com/). The intent of this project is to simplify tool usage for external agents as well.**

Nothing but love to the NousResearch team.
