from __future__ import annotations

import argparse
import json
import sys

from simpletools.registry import list_tools


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    p = argparse.ArgumentParser(
        prog="simpletools", description="Hermes-style Python tools (subset)."
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    lp = sub.add_parser("list", help="List built-in tool names.")
    lp.set_defaults(func=_cmd_list)

    cp = sub.add_parser("call", help="Invoke one tool (JSON args on stdin or --args).")
    cp.add_argument("tool")
    cp.add_argument("--args", default="{}", help="JSON object of kwargs")
    cp.set_defaults(func=_cmd_call)

    args = p.parse_args(argv)
    args.func(args)


def _cmd_list(_args: argparse.Namespace) -> None:
    for row in list_tools():
        print(f"{row['name']}\t{row['description']}")


def _cmd_call(args: argparse.Namespace) -> None:
    from pathlib import Path

    from simpletools.runner import ToolRunner

    raw = args.args
    if not sys.stdin.isatty():
        extra = sys.stdin.read().strip()
        if extra:
            raw = extra
    kwargs = json.loads(raw)
    r = ToolRunner(cwd=Path.cwd())
    out = r.call(args.tool, **kwargs)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
