# SimpleTools

Python equivalents of common Hermes-style agent tool names: web, browser (optional Playwright), terminal, files, vision (OpenAI-compatible), todo, clarify, code execution, delegation (callback), memory, session search, cron, messaging hooks, Honcho-like local profile, and skills on disk.

**Excluded** (per request): image generation, TTS, Home Assistant, mixture-of-agents, RL.

This repository is a **normal Python package** published to PyPI as [`simpletools`](https://pypi.org/project/simpletools/). Builds and installs are driven by **[uv](https://docs.astral.sh/uv/)**.

## Development with uv

```bash
git clone <repo-url> && cd SimpleTools
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
uv tool install simpletools
# or
uv pip install simpletools
# optional browser automation
uv pip install "simpletools[browser]"
playwright install chromium
```

## PyPI release

1. Bump `version` in [`pyproject.toml`](pyproject.toml).
2. Run `uv lock` (if dependencies changed) and `uv build`.
3. **Local publish:** `uv publish` with `UV_PUBLISH_TOKEN` set to a [PyPI API token](https://pypi.org/manage/account/token/) (scope: project `simpletools`).
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
simpletools list
simpletools call memory --args '{"action":"read"}'
```

## Configuration

Environment highlights: `FIRECRAWL_API_KEY` / `FIRECRAWL_API_URL`, `TAVILY_API_KEY`, `EXA_API_KEY`, optional `SIMPLETOOLS_WEB_BACKEND` (`firecrawl`, `tavily`, or `exa`), `OPENAI_*` for vision, `SIMPLETOOLS_DATA_DIR`, `SIMPLETOOLS_FILE_READ_MAX_CHARS`, `SIMPLETOOLS_SKILLS_DIR`.

**Hermes-style behavior (reimplemented, not copied):** multi-strategy fuzzy `patch` replace, optional `mode="patch"` V4A hunks, file read guards (device blocklist, char cap, repeat-read loop), web backend priority similar to Hermes, file-backed `memory` (`memories/MEMORY.md` + `USER.md`, `§` entries), session todos with `content`/`status`.

See [`simpletools/registry.py`](simpletools/registry.py) for the full tool name list.

## Code quality (Cursor skills)

Project-local guidance lives under [`.cursor/skills/`](.cursor/skills/) (e.g. `python-project-structure`, `python-type-safety`, `python-anti-patterns`). **Ruff** in [`pyproject.toml`](pyproject.toml) enforces a consistent style in CI and locally via `uv run ruff …`.
