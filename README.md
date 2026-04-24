# simpleTools

Python agent tools: web, browser (optional Playwright), terminal, files, vision (OpenAI-compatible), todo, clarify, code execution, delegation (callback), memory, session search, cron, messaging hooks, Honcho-like local profile, and skills on disk.

**Excluded** (per request): image generation, TTS, Home Assistant, mixture-of-agents, RL.

This repository is the **simpleTools** distribution on PyPI ([project page](https://pypi.org/project/simpletools/) — PyPI normalizes the name to lowercase in URLs). The importable Python package is **`simpletools`**. Builds and installs are driven by **[uv](https://docs.astral.sh/uv/)**.

## Agent toolkit

Tools are registered in [`simpletools/registry.py`](simpletools/registry.py) (`TOOLS`). Host code wires a [`ToolContext`](simpletools/context.py) and calls [`ToolRunner.call`](simpletools/runner.py) or [`registry.call_tool`](simpletools/registry.py). The CLI can list the same names: `simpleTools list` (the `simpletools` command is an alias).

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
uv tool install simpleTools
# or
uv pip install simpleTools
# optional browser automation
uv pip install "simpleTools[browser]"
playwright install chromium
```

## PyPI release

1. Bump `version` in [`pyproject.toml`](pyproject.toml).
2. Run `uv lock` (if dependencies changed) and `uv build`.
3. **Local publish:** `uv publish` with `UV_PUBLISH_TOKEN` set to a [PyPI API token](https://pypi.org/manage/account/token/) (scope: project **simpleTools** / `simpletools` on PyPI).
4. **CI publish:** GitHub Actions [`.github/workflows/publish.yml`](.github/workflows/publish.yml) runs on **release published** and expects a repo secret `PYPI_API_TOKEN`.

Trusted publishing (OIDC) can be enabled later via `uv publish --trusted-publishing always` once the PyPI project is configured for it.

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
simpleTools list
simpleTools call memory --args '{"action":"read"}'
```

## Configuration

Environment highlights: `FIRECRAWL_API_KEY` / `FIRECRAWL_API_URL`, `TAVILY_API_KEY`, `EXA_API_KEY`, optional `SIMPLETOOLS_WEB_BACKEND` (`firecrawl`, `tavily`, or `exa`), `OPENAI_*` for vision, `SIMPLETOOLS_DATA_DIR`, `SIMPLETOOLS_FILE_READ_MAX_CHARS`, `SIMPLETOOLS_SKILLS_DIR`.

**Behavior notes:** multi-strategy fuzzy `patch` replace, optional `mode="patch"` V4A hunks, file read guards (device blocklist, char cap, repeat-read loop), configurable web search backends, file-backed `memory` (`memories/MEMORY.md` + `USER.md`, `§` entries), session todos with `content`/`status`.

## Code quality (Cursor skills)

Project-local guidance lives under [`.cursor/skills/`](.cursor/skills/) (e.g. `python-project-structure`, `python-type-safety`, `python-anti-patterns`). **Ruff** in [`pyproject.toml`](pyproject.toml) enforces a consistent style in CI and locally via `uv run ruff …`.

## Acknowledgments

**All of the tools in this repository are inspired by Hermes from [NousResearch](https://nousresearch.com/). The intent of this project is to simplify tool usage for external agents as well.**

Nothing but love to the NousResearch team.
