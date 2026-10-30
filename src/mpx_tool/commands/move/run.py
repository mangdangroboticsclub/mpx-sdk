"""mpx move run — execute a skill on the robot."""

from __future__ import annotations

import argparse

from mpx_tool.config import DEFAULT_ROBOT_HOST, DEFAULT_ROBOT_PORT
from mpx_tool.sdk.robot import RobotClient, RobotError


def add_move_run_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("run", help="Execute a skill on the robot")
    p.add_argument("skill", help="Skill filename to run (e.g. my_skill.wasm)")
    p.add_argument("--ip", "-i", default=None, help=f"Robot IP address (default: {DEFAULT_ROBOT_HOST})")
    p.add_argument("--port", "-p", type=int, default=None, help=f"Robot HTTP port (default: {DEFAULT_ROBOT_PORT})")


def cmd_move_run(args: argparse.Namespace) -> None:
    client = RobotClient(
        host=args.ip or DEFAULT_ROBOT_HOST,
        port=args.port or DEFAULT_ROBOT_PORT,
    )

    print(f"▶️  Running '{args.skill}' on {client.host}:{client.port}...")

    try:
        result = client.run_skill(args.skill)
        output = result.get("output", str(result))
        print(f"✅ {output}")
    except RobotError as e:
        print(f"❌ {e}")
