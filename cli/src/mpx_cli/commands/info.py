"""mpx-cli info — show detailed skill information."""

from __future__ import annotations

import argparse
import sys

from mpx_cli.sdk.gateway import GatewayClient, GatewayError


def add_info_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("info", help="Show detailed marketplace skill information")
    p.add_argument("skill_id", help="Skill ID (e.g. username~slug)")
    p.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text",
    )


def cmd_info(args: argparse.Namespace) -> None:
    """Handle ``mpx-cli info <skill_id>``."""
    client = GatewayClient(gateway_url=getattr(args, "gateway_url", None))

    try:
        skill = client.get_skill(args.skill_id)
    except GatewayError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    if not skill:
        print(f"❌ Skill '{args.skill_id}' not found")
        return

    if args.json:
        import json
        print(json.dumps(skill, indent=2))
        return

    # Helper: extract username from id (format: username~slug)
    def _author() -> str:
        raw = skill.get("username", skill.get("author", None))
        if raw:
            return raw
        sid = skill.get("id", skill.get("skill_id", ""))
        if sid and "~" in sid:
            return sid.split("~")[0]
        return "?"

    # Formatted output
    sid = skill.get("id", skill.get("skill_id", "?"))
    ver = skill.get("current_version", skill.get("version", skill.get("latest_version", "?")))
    print(f"📦 {skill.get('title', '?')}")
    print(f"   ID:          {sid}")
    print(f"   Slug:        {skill.get('slug', '?')}")
    print(f"   Author:      {_author()}")
    print(f"   Version:     {ver}")
    print(f"   Type:        {skill.get('skill_type', '?')}")
    print(f"   Language:    {skill.get('source_language', '?')}")
    print(f"   Description: {skill.get('description', skill.get('readme', '(no description)'))}")

    # Try fetching manifest too
    try:
        manifest = client.get_manifest(args.skill_id)
        if manifest and isinstance(manifest, dict):
            print()
            print("   Manifest:")
            for key, val in manifest.items():
                if key not in ("skill_id",):
                    print(f"     {key}: {val}")
    except GatewayError:
        pass  # Manifest fetch is best-effort
