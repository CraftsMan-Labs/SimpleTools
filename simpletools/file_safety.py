"""Path safety rules for agent file tools (device reads, sensitive writes)."""

from __future__ import annotations

from pathlib import Path

# Device paths that hang or stream forever — literal path match, no symlink follow.
_BLOCKED_DEVICE_PATHS: frozenset[str] = frozenset(
    {
        "/dev/zero",
        "/dev/random",
        "/dev/urandom",
        "/dev/full",
        "/dev/stdin",
        "/dev/tty",
        "/dev/console",
        "/dev/stdout",
        "/dev/stderr",
        "/dev/fd/0",
        "/dev/fd/1",
        "/dev/fd/2",
    }
)

_SENSITIVE_PREFIXES: tuple[str, ...] = ("/etc/", "/boot/", "/usr/lib/systemd/")
_SENSITIVE_EXACT: frozenset[str] = frozenset({"/var/run/docker.sock", "/run/docker.sock"})


def is_blocked_device_path(filepath: str) -> bool:
    normalized = str(Path(filepath).expanduser())
    proc_stdio = normalized.startswith("/proc/") and normalized.endswith(
        ("/fd/0", "/fd/1", "/fd/2")
    )
    return normalized in _BLOCKED_DEVICE_PATHS or proc_stdio


def sensitive_write_error(filepath: str) -> str | None:
    try:
        resolved = str(Path(filepath).expanduser().resolve(strict=False))
    except (OSError, ValueError):
        resolved = filepath
    for prefix in _SENSITIVE_PREFIXES:
        if resolved.startswith(prefix):
            return (
                f"Refusing to write to sensitive system path: {filepath}\n"
                "Use the terminal tool with elevated privileges only if you intend system changes."
            )
    if resolved in _SENSITIVE_EXACT:
        return (
            f"Refusing to write to sensitive system path: {filepath}\n"
            "Use the terminal tool if you need to modify this resource."
        )
    return None
