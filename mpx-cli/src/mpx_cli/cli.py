"""mpx-cli entry point — argument parsing and command dispatch."""

from __future__ import annotations

import argparse
import sys

from mpx_cli.commands.init import add_init_parser, cmd_init
from mpx_cli.commands.build import add_build_parser, cmd_build
from mpx_cli.commands.upload import add_upload_parser, cmd_upload
from mpx_cli.commands.run import add_run_parser, cmd_run
from mpx_cli.commands.list_skills import add_list_parser, cmd_list
from mpx_cli.commands.delete import add_delete_parser, cmd_delete
from mpx_cli.sdk.connection import DEFAULT_HOST, DEFAULT_PORT


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mpx-cli",
        description="MPX-Dog Skill Development Kit — build & deploy WASM skills",
    )
    parser.add_argument(
        "--ip", "-i",
        default=DEFAULT_HOST,
        help=f"Robot IP address (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=DEFAULT_PORT,
        help=f"Robot HTTP port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"mpx-cli {__import__('mpx_cli').__version__}",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    add_init_parser(sub)
    add_build_parser(sub)
    add_upload_parser(sub)
    add_run_parser(sub)
    add_list_parser(sub)
    add_delete_parser(sub)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    commands = {
        "init": cmd_init,
        "build": cmd_build,
        "upload": cmd_upload,
        "run": cmd_run,
        "list": cmd_list,
        "delete": cmd_delete,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()