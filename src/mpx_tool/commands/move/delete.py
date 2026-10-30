"""mpx move delete — remove a skill from the robot."""

from __future__ import annotations

import argparse

from mpx_tool.config import DEFAULT_ROBOT_HOST, DEFAULT_ROBOT_PORT
from mpx_tool.sdk.robot import RobotClient, RobotError


def add_move_delete_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("delete", help="Delete a skill from the robot")
    p.add_argument("skill", help="Skill filename to delete (e.g. my_skill.wasm)")
    p.add_argument("--ip", "-i", default=None, help=f"Robot IP address (default: {DEFAULT_ROBOT_HOST})")
    p.add_argument("--port", "-p", type=int, default=None, help=f"Robot HTTP port (default: {DEFAULT_ROBOT_PORT})")
    p.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")


def cmd_move_delete(args: argparse.Namespace) -> None:
    if not args.yes:
        resp = input(f"⚠️  Delete '{args.skill}' from robot? [y/N] ")
        if resp.lower() not in ("y", "yes"):
            print("Cancelled.")
            return

    client = RobotClient(
        host=args.ip or DEFAULT_ROBOT_HOST,
        port=args.port or DEFAULT_ROBOT_PORT,
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
