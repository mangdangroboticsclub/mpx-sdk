"""mpx-cli run — execute a skill on the robot."""

from __future__ import annotations

import argparse
from mpx_cli.sdk.connection import RobotClient, RobotError


def add_run_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("run", help="Execute a skill on the robot")
    p.add_argument("skill", help="Skill filename to run (e.g. my_skill.wasm)")
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


def cmd_run(args: argparse.Namespace) -> None:
    client = RobotClient(
        host=args.ip or "192.168.2.1",
        port=args.port or 80,
    )

    print(f"▶️  Running '{args.skill}' on {client.host}:{client.port}...")

    try:
        result = client.run_skill(args.skill)
        output = result.get("output", str(result))
        print(f"✅ {output}")
    except RobotError as e:
        print(f"❌ {e}")
