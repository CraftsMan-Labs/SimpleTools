# Hermes Agent: user-available tools (from repo docs)

This inventory is derived from the **hermes-agent** repository documentation under `website/docs/` (e.g. clone at `~/Desktop/projects/rishub/hermes-agent`). It is not generated from a live `hermes` install on this machine.

**Canonical sources**

- Built-in tools: `hermes-agent/website/docs/reference/tools-reference.md`
- Toolsets: `hermes-agent/website/docs/reference/toolsets-reference.md`
- Overview: `hermes-agent/website/docs/user-guide/features/tools.md`

## How to discover tools at runtime

- Run `hermes tools` to list what is available in your install.
- Run `hermes chat --toolsets "web,terminal"` (etc.) to restrict bundles.
- Availability varies by platform, enabled toolsets, credentials, and environment keys.

## Built-in toolsets and their tools

| Toolset | Tools |
|--------|--------|
| **web** | `web_search`, `web_extract` — needs one of: `EXA_API_KEY`, `PARALLEL_API_KEY`, `FIRECRAWL_API_KEY`, `TAVILY_API_KEY` |
| **browser** | `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_press`, `browser_scroll`, `browser_back`, `browser_console`, `browser_get_images`, `browser_vision`, `browser_close` — the `browser` toolset in toolsets-reference also bundles `web_search` |
| **terminal** | `terminal`, `process` |
| **file** | `read_file`, `write_file`, `search_files`, `patch` |
| **vision** | `vision_analyze` |
| **image_gen** | `image_generate` — needs `FAL_KEY` |
| **tts** | `text_to_speech` |
| **todo** | `todo` |
| **clarify** | `clarify` |
| **code_execution** | `execute_code` |
| **delegation** | `delegate_task` |
| **memory** | `memory` |
| **session_search** | `session_search` |
| **cronjob** | `cronjob` |
| **messaging** | `send_message` |
| **homeassistant** | `ha_list_entities`, `ha_list_services`, `ha_get_state`, `ha_call_service` |
| **honcho** | `honcho_profile`, `honcho_search`, `honcho_context`, `honcho_conclude` |
| **moa** | `mixture_of_agents` — needs `OPENROUTER_API_KEY` |
| **skills** | `skills_list`, `skill_view`, `skill_manage` |
| **rl** | `rl_list_environments`, `rl_select_environment`, `rl_get_current_config`, `rl_edit_config`, `rl_start_training`, `rl_stop_training`, `rl_check_status`, `rl_list_runs`, `rl_get_results`, `rl_test_inference` — needs `TINKER_API_KEY`, `WANDB_API_KEY` |

## Composite and platform presets

Composite toolsets include **`debugging`**, **`safe`**, **`hermes-gateway`**, and platform presets such as **`hermes-cli`**, **`hermes-telegram`**, **`hermes-api-server`**, etc.

The **`hermes-cli`** preset unions most built-ins (browser, file, terminal, web, skills, memory, honcho, HA, image, MoA, messaging, TTS, etc.). It is **not identical** to every other preset; for example **`hermes-api-server`** omits `send_message`, `clarify`, and `text_to_speech` per the toolsets reference table.

## Beyond built-ins

- **`mcp-<server>`** — dynamic toolsets from each configured MCP server.
- **`all`** / **`*`** — wildcards that expand to every registered toolset (use with care).

For the exact tool list on a given machine, run `hermes tools` with your `~/.hermes/config.yaml` and environment.
