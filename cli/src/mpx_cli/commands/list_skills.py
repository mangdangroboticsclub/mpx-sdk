"""mpx-cli list — list skills installed on the robot."""

from __future__ import annotations

import argparse
from mpx_cli.sdk.connection import RobotClient, RobotError


def add_list_parser(sub: argparse._SubParsersAction) -> None:
    from mpx_cli.cli import robot_opts

    p = sub.add_parser(
        "list",
        aliases=["ls"],
        parents=[robot_opts()],
        help="List skills installed on the robot",
    )
    p.add_argument(
        "--all", "-a",
        action="store_true",
        help="Show all files (not just .wasm skills)",
    )


def cmd_list(args: argparse.Namespace) -> None:
    client = RobotClient(host=args.ip, port=args.port)

    try:
        if args.all:
            items = client.list_files()
        else:
            items = client.list_skills()

        if not items:
            print("📭 No skills found on robot")
            return

        print(f"📋 {'Skills' if not args.all else 'Files'} on {client.host}:{client.port}:")
        print()

        # Determine column widths
        name_width = max(len(i.get("name", "")) for i in items) + 2
        name_width = max(name_width, 10)

        for item in sorted(items, key=lambda x: x.get("name", "")):
            name = item.get("name", "?")
            size = item.get("size", 0)
            size_str = _format_size(size)
            print(f"  {name:<{name_width}} {size_str:>8}")
        print()

    except RobotError as e:
        print(f"❌ {e}")


def _format_size(bytes: int) -> str:
    if bytes < 1024:
        return f"{bytes} B"
    elif bytes < 1024 * 1024:
        return f"{bytes / 1024:.1f} KB"
    else:
        return f"{bytes / (1024 * 1024):.2f} MB"
