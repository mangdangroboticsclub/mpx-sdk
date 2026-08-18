"""mpx-cli robot — show robot info and assigned skills."""

from __future__ import annotations

import argparse
import sys

from mpx_cli.sdk.gateway import GatewayClient, GatewayError


def add_robot_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("robot", help="Show robot information and assigned skills")
    p.add_argument("uuid", help="Robot UUID")
    p.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text",
    )


def cmd_robot(args: argparse.Namespace) -> None:
    """Handle ``mpx-cli robot <uuid>``."""
    client = GatewayClient(gateway_url=getattr(args, "gateway_url", None))

    try:
        info = client.get_robot(args.uuid)
        skills = client.get_robot_skills(args.uuid)
    except GatewayError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    if not info:
        print(f"❌ Robot '{args.uuid}' not found")
        return

    if args.json:
        import json
        output = {"info": info, "skills": skills}
        print(json.dumps(output, indent=2))
        return

    # Formatted output
    print(f"🤖 Robot: {info.get('name', info.get('uuid', args.uuid))}")
    print(f"   UUID:  {info.get('uuid', '?')}")
    if "model" in info:
        print(f"   Model: {info['model']}")
    if "firmware" in info:
        print(f"   Firmware: {info['firmware']}")
    if "status" in info:
        print(f"   Status: {info['status']}")

    print()
    if skills:
        print(f"📋 Assigned skills ({len(skills)}):")
        for s in skills:
            sid = s.get("id", s.get("skill_id", "?"))
            ver = s.get("current_version", s.get("version", s.get("latest_version", "?")))
            print(f"   • {sid} (v{ver})")
    else:
        print("📭 No skills assigned to this robot")
    print()
