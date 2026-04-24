"""TypedDict response shapes for tools, store rows, and session state."""

from __future__ import annotations

from typing import Any, Literal, TypeAlias, TypedDict

from typing_extensions import NotRequired

# --- Registry / dispatch -----------------------------------------------------


class UnknownToolResponse(TypedDict):
    ok: Literal[False]
    error: str


class ToolListingRow(TypedDict):
    name: str
    description: str


# --- Shared error pattern ----------------------------------------------------


class ToolError(TypedDict, total=False):
    ok: Literal[False]
    error: str
    hint: NotRequired[str]
    partial_diff: NotRequired[str]
    status: NotRequired[int]
    content_type: NotRequired[str]
    stdout: NotRequired[str]
    stderr: NotRequired[str]
    targets: NotRequired[list[str]]
    total_lines: NotRequired[int]
    path: NotRequired[str]
    matches: NotRequired[list[str]]


# --- Web --------------------------------------------------------------------


class WebSearchHit(TypedDict, total=False):
    title: str
    url: str
    content: str
    position: int


class WebSearchOk(TypedDict, total=False):
    ok: Literal[True]
    provider: str
    results: list[WebSearchHit]
    note: NotRequired[str]


WebSearchResult: TypeAlias = WebSearchOk | ToolError


class WebExtractOk(TypedDict, total=False):
    ok: Literal[True]
    provider: str
    url: str
    markdown: str
    truncated: bool
    content_type: NotRequired[str]


WebExtractResult: TypeAlias = WebExtractOk | ToolError


# --- File ops ----------------------------------------------------------------


class ReadFileOk(TypedDict, total=False):
    ok: Literal[True]
    path: str
    content: str
    total_lines: NotRequired[int]
    truncated: NotRequired[bool]
    file_size: NotRequired[int]
    dedup: NotRequired[bool]
    _warning: NotRequired[str]
    _hint: NotRequired[str]


ReadFileResult: TypeAlias = ReadFileOk | ToolError


class WriteFileOk(TypedDict, total=False):
    ok: Literal[True]
    path: str
    _warning: NotRequired[str]


WriteFileResult: TypeAlias = WriteFileOk | ToolError


class PyCompileLint(TypedDict):
    cmd: Literal["py_compile"]
    exit_code: int
    stderr: str


class PatchReplaceOk(TypedDict, total=False):
    ok: Literal[True]
    path: str
    replacements: int
    diff: str
    lint: NotRequired[PyCompileLint | None]
    _warning: NotRequired[str]


class PatchV4AOk(TypedDict, total=False):
    ok: Literal[True]
    diff: NotRequired[str | None]
    files: NotRequired[list[str] | None]


PatchResult: TypeAlias = PatchReplaceOk | PatchV4AOk | ToolError


class SearchMatch(TypedDict, total=False):
    path: str
    line: NotRequired[int | None]
    text: NotRequired[str]


class SearchFilesOk(TypedDict):
    ok: Literal[True]
    mode: Literal["name", "rg", "python"]
    matches: list[SearchMatch]


SearchFilesResult: TypeAlias = SearchFilesOk | ToolError


# --- Terminal / process ------------------------------------------------------


class TerminalOk(TypedDict, total=False):
    ok: Literal[True]
    exit_code: NotRequired[int | None]
    stdout: str
    stderr: str
    session_id: NotRequired[str]
    pid: NotRequired[int | None]
    background: NotRequired[bool]


class TerminalTimeout(TypedDict):
    ok: Literal[False]
    error: Literal["timeout"]
    stdout: str
    stderr: str


TerminalResult: TypeAlias = TerminalOk | TerminalTimeout | ToolError


class ProcessRow(TypedDict):
    session_id: str
    pid: int | None
    cmd: str
    running: bool


class ProcessListOk(TypedDict):
    ok: Literal[True]
    processes: list[ProcessRow]


class ProcessPollOk(TypedDict):
    ok: Literal[True]
    running: bool
    exit_code: int | None
    new_output: str


class ProcessLogOk(TypedDict):
    ok: Literal[True]
    stdout: str
    stderr: str
    exit_code: int | None


class ProcessWaitOk(TypedDict):
    ok: Literal[True]
    exit_code: int | None
    stdout: str
    stderr: str


class ProcessKillOk(TypedDict):
    ok: Literal[True]
    killed: Literal[True]


ProcessResult: TypeAlias = (
    ProcessListOk | ProcessPollOk | ProcessLogOk | ProcessWaitOk | ProcessKillOk | ToolError
)


# --- Browser console messages (shared) --------------------------------------


class BrowserConsoleMsg(TypedDict, total=False):
    type: str
    text: str


# --- Browser tools -----------------------------------------------------------


class BrowserNavigateOk(TypedDict):
    ok: Literal[True]
    url: str
    title: str


class BrowserSnapshotOk(TypedDict):
    ok: Literal[True]
    snapshot: str


class BrowserConsoleOk(TypedDict):
    ok: Literal[True]
    messages: list[BrowserConsoleMsg]


class BrowserImageRow(TypedDict, total=False):
    src: str
    alt: str


class BrowserImagesOk(TypedDict):
    ok: Literal[True]
    images: list[BrowserImageRow]


class BrowserActionOk(TypedDict):
    ok: Literal[True]


class BrowserBackOk(TypedDict):
    ok: Literal[True]
    url: str


class VisionAnalyzeOk(TypedDict):
    ok: Literal[True]
    answer: str


class VisionAnalyzeErr(TypedDict, total=False):
    ok: Literal[False]
    error: str
    status: NotRequired[int]


VisionAnalyzeResult: TypeAlias = VisionAnalyzeOk | VisionAnalyzeErr


BrowserResult: TypeAlias = (
    BrowserNavigateOk
    | BrowserSnapshotOk
    | BrowserActionOk
    | BrowserBackOk
    | BrowserConsoleOk
    | BrowserImagesOk
    | VisionAnalyzeResult
    | ToolError
)


# --- Session index rows (store + tools) --------------------------------------


class SessionIndexRow(TypedDict, total=False):
    id: str
    title: str
    summary: str
    body: str
    created: float


class SessionSearchResultOk(TypedDict):
    ok: Literal[True]
    matches: list[SessionIndexRow]


class SessionIndexOk(TypedDict):
    ok: Literal[True]
    id: str


# --- Todo --------------------------------------------------------------------


class TodoItem(TypedDict):
    id: str
    content: str
    status: str


class TodoSummary(TypedDict):
    total: int
    pending: int
    in_progress: int
    completed: int
    cancelled: int


class TodoResult(TypedDict):
    ok: Literal[True]
    todos: list[TodoItem]
    summary: TodoSummary


# --- Memory store (used by memory tool and FileMemoryStore) ------------------


class MemoryStoreReadOk(TypedDict):
    ok: Literal[True]
    target: str
    entries: list[str]
    rendered: str


class MemoryStoreDupOk(TypedDict):
    ok: Literal[True]
    message: str
    entries: list[str]


class MemoryStoreEntriesOk(TypedDict):
    ok: Literal[True]
    entries: list[str]


MemoryStoreMutation: TypeAlias = MemoryStoreDupOk | MemoryStoreEntriesOk | ToolError


class MemoryReadAllOk(TypedDict):
    ok: Literal[True]
    memory: list[str]
    user: list[str]


MemoryToolResult: TypeAlias = MemoryReadAllOk | MemoryStoreMutation | ToolError


# --- Delegate ----------------------------------------------------------------


class DelegateRow(TypedDict):
    task: str
    result: Any


class DelegateOk(TypedDict):
    ok: Literal[True]
    results: list[DelegateRow]


class DelegateErr(TypedDict, total=False):
    ok: Literal[False]
    error: str
    hint: NotRequired[str]


DelegateResult: TypeAlias = DelegateOk | DelegateErr


# --- Messaging / clarify / execute -------------------------------------------


class MessageListOk(TypedDict):
    ok: Literal[True]
    targets: list[str]
    note: str


class MessageSendOk(TypedDict):
    ok: Literal[True]
    delivery: Any


MessageResult: TypeAlias = MessageListOk | MessageSendOk | ToolError


class ClarifyInteractiveOk(TypedDict):
    ok: Literal[True]
    answer: str


class ClarifyPending(TypedDict, total=False):
    ok: Literal[False]
    mode: Literal["non_interactive"]
    prompt: str
    choices: list[str] | None
    message: str


ClarifyResult: TypeAlias = ClarifyInteractiveOk | ClarifyPending


class ExecuteCodeOk(TypedDict):
    ok: Literal[True]
    exit_code: int | None
    stdout: str
    stderr: str


ExecuteCodeResult: TypeAlias = ExecuteCodeOk | TerminalTimeout | ToolError


# --- Honcho ------------------------------------------------------------------


class HonchoCard(TypedDict, total=False):
    facts: list[str]


class HonchoProfileOk(TypedDict, total=False):
    ok: Literal[True]
    card: HonchoCard
    note: NotRequired[str]


class HonchoSearchRow(TypedDict):
    content: str
    id: NotRequired[str]
    created: NotRequired[float]


class HonchoSearchOk(TypedDict):
    ok: Literal[True]
    excerpts: list[HonchoSearchRow]


class HonchoContextOk(TypedDict):
    ok: Literal[True]
    synthesized_from_excerpts: str
    count: int


class HonchoConcludeOk(TypedDict):
    ok: Literal[True]
    id: str


HonchoResult: TypeAlias = (
    HonchoProfileOk | HonchoSearchOk | HonchoContextOk | HonchoConcludeOk | ToolError
)


# --- Skills ------------------------------------------------------------------


class SkillRow(TypedDict):
    name: str
    description: str


class SkillsListOk(TypedDict):
    ok: Literal[True]
    skills: list[SkillRow]


class SkillViewFileOk(TypedDict):
    ok: Literal[True]
    path: str
    content: str


SkillViewMdOk = TypedDict(
    "SkillViewMdOk",
    {
        "ok": Literal[True],
        "skill": str,
        "SKILL.md": str,
    },
)


class SkillManageOk(TypedDict, total=False):
    ok: Literal[True]
    skill: NotRequired[str]
    deleted: NotRequired[str]


SkillsResult: TypeAlias = SkillsListOk | SkillViewFileOk | SkillViewMdOk | SkillManageOk | ToolError


# --- Cron --------------------------------------------------------------------


class CronJobRow(TypedDict):
    id: str
    spec: str
    payload_json: str
    enabled: int
    last_run: float | None
    next_run: float | None


class CronListOk(TypedDict):
    ok: Literal[True]
    jobs: list[CronJobRow]


class CronCreateOk(TypedDict):
    ok: Literal[True]
    id: str
    next_run: float


class CronUpdateOk(TypedDict):
    ok: Literal[True]
    id: str


class CronPauseResumeOk(TypedDict):
    ok: Literal[True]
    id: str
    enabled: bool


class CronRemoveOk(TypedDict):
    ok: Literal[True]
    removed: str


CronResult: TypeAlias = (
    CronListOk
    | CronCreateOk
    | CronUpdateOk
    | CronPauseResumeOk
    | CronRemoveOk
    | TerminalResult
    | ExecuteCodeResult
    | ToolError
)


# --- V4A apply (internal helper; same JSON shape as tools) --------------------


class V4ApplyResult(TypedDict):
    ok: bool
    errors: list[str]
    files: list[str]
    diff: str


# --- Mutable session bags (ToolContext internals) ----------------------------


class FileReadTrackerState(TypedDict):
    last_key: tuple[str, str, int, int] | None
    consecutive: int
    dedup: dict[tuple[str, int, int], float]
    read_ts: dict[str, float]


class BrowserSessionState(TypedDict):
    page: Any
    browser: Any
    pw: Any
    console: list[BrowserConsoleMsg]


# --- Union of all tool-facing API returns ------------------------------------

ToolResult: TypeAlias = (
    UnknownToolResponse
    | WebSearchResult
    | WebExtractResult
    | ReadFileResult
    | WriteFileResult
    | PatchResult
    | SearchFilesResult
    | TerminalResult
    | ProcessResult
    | BrowserResult
    | TodoResult
    | MemoryToolResult
    | SessionSearchResultOk
    | SessionIndexOk
    | DelegateResult
    | MessageResult
    | ClarifyResult
    | ExecuteCodeResult
    | HonchoResult
    | SkillsResult
    | CronResult
)
