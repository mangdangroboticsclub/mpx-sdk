"""mpx-cli delete — remove a skill from the robot."""

from __future__ import annotations

import argparse
from mpx_cli.sdk.connection import RobotClient, RobotError


def add_delete_parser(sub: argparse._SubParsersAction) -> None:
    from mpx_cli.cli import robot_opts

    p = sub.add_parser(
        "delete",
        parents=[robot_opts()],
        help="Delete a skill from the robot",
    )
    p.add_argument("skill", help="Skill filename to delete (e.g. my_skill.wasm)")
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

    client = RobotClient(host=args.ip, port=args.port)

    print(f"🗑️  Deleting '{args.skill}' from {client.host}:{client.port}...")

    try:
        result = client.delete_file(args.skill)
        if result.get("ok"):
            print(f"✅ Deleted '{args.skill}'")
        else:
            print(f"❌ Delete failed: {result}")
    except RobotError as e:
        print(f"❌ {e}")
