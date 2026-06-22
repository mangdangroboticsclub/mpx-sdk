"""mpx-cli delete — remove a skill from the robot."""

from __future__ import annotations

import argparse
from mpx_cli.sdk.connection import RobotClient, RobotError


def add_delete_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("delete", help="Delete a skill from the robot")
    p.add_argument("skill", help="Skill filename to delete (e.g. my_skill.wasm)")
    p.add_argument(
        "--ip", "-i",
        default=None,
        help="Robot IP address (default: 192.168.2.1)",
    )
    p.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help="Robot HTTP port (default: 80)",
    )
    p.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )


def cmd_delete(args: argparse.Namespace) -> None:
    if not args.yes:
        resp = input(f"⚠️  Delete '{args.skill}' from robot? [y/N] ")
        if resp.lower() not in ("y", "yes"):
            print("Cancelled.")
            return

    client = RobotClient(
        host=args.ip or "192.168.2.1",
        port=args.port or 80,
    )

    print(f"🗑️  Deleting '{args.skill}' from {client.host}:{client.port}...")

    try:
        result = client.delete_file(args.skill)
        if result.get("ok"):
            print(f"✅ Deleted '{args.skill}'")
        else:
            print(f"❌ Delete failed: {result}")
    except RobotError as e:
        print(f"❌ {e}")
