# simpleAgentTools: built-in tools

This project ships a fixed registry of tools (see [`simpletools/registry.py`](simpletools/registry.py)). Use the CLI to list names and descriptions:

```bash
simpleAgentTools list
```

## Included capabilities (by area)

| Area | Tools |
| --- | --- |
| **Web** | `web_search`, `web_extract` |
| **Files** | `read_file`, `write_file`, `search_files`, `patch` |
| **Shell** | `terminal`, `process` |
| **Browser** (optional extra) | `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_press`, `browser_scroll`, `browser_back`, `browser_console`, `browser_get_images`, `browser_vision`, `browser_close` |
| **Vision** | `vision_analyze` |
| **Session / tasks** | `todo`, `clarify`, `delegate_task`, `execute_code` |
| **Memory & sessions** | `memory`, `session_search`, `session_index` |
| **Scheduling** | `cronjob` |
| **Messaging** | `send_message` |
| **Honcho-like store** | `honcho_profile`, `honcho_search`, `honcho_context`, `honcho_conclude` |
| **Skills on disk** | `skills_list`, `skill_view`, `skill_manage` |

Availability of web search, browser automation, and vision depends on optional dependencies and environment variables (see [`README.md`](README.md)).

**Not included in this package:** image generation, TTS, Home Assistant, mixture-of-agents, RL.
