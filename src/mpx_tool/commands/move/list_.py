"""mpx move list — list skills installed on the robot."""

from __future__ import annotations

import argparse

from mpx_tool.config import DEFAULT_ROBOT_HOST, DEFAULT_ROBOT_PORT
from mpx_tool.sdk.robot import RobotClient, RobotError


def add_move_list_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "list",
        aliases=["ls"],
        help="List skills installed on the robot",
    )
    p.add_argument("--ip", "-i", default=None, help=f"Robot IP address (default: {DEFAULT_ROBOT_HOST})")
    p.add_argument("--port", "-p", type=int, default=None, help=f"Robot HTTP port (default: {DEFAULT_ROBOT_PORT})")
    p.add_argument("--all", "-a", action="store_true", help="Show all files (not just .wasm skills)")


def _format_size(num: int) -> str:
    if num < 1024:
        return f"{num} B"
    if num < 1024 * 1024:
        return f"{num / 1024:.1f} KB"
    return f"{num / (1024 * 1024):.2f} MB"


def cmd_move_list(args: argparse.Namespace) -> None:
    client = RobotClient(
        host=args.ip or DEFAULT_ROBOT_HOST,
        port=args.port or DEFAULT_ROBOT_PORT,
    )

    try:
        items = client.list_files() if args.all else client.list_skills()

        if not items:
            print("📭 No skills found on robot")
            return

        print(f"📋 {'Skills' if not args.all else 'Files'} on {client.host}:{client.port}:")
        print()

        name_width = max(max(len(str(i.get("name", ""))) for i in items) + 2, 10)
        for item in sorted(items, key=lambda x: str(x.get("name", ""))):
            name = item.get("name", "?")
            size = item.get("size", 0)
            print(f"  {str(name):<{name_width}} {_format_size(size):>8}")
        print()

    except RobotError as e:
        print(f"❌ {e}")
