"""mpx-cli versions — list published versions of a marketplace skill."""

from __future__ import annotations

import argparse
import sys

from mpx_cli.sdk.gateway import GatewayClient, GatewayError


def add_versions_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("versions", help="List all published versions of a skill")
    p.add_argument("skill_id", help="Skill ID (e.g. username~slug)")
    p.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of a table",
    )


def cmd_versions(args: argparse.Namespace) -> None:
    """Handle ``mpx-cli versions <skill_id>``."""
    client = GatewayClient(gateway_url=getattr(args, "gateway_url", None))

    try:
        versions = client.get_versions(args.skill_id)
    except GatewayError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    if not versions:
        print(f"📭 No versions found for '{args.skill_id}'")
        return

    if args.json:
        import json
        print(json.dumps(versions, indent=2))
        return

    print(f"📋 Versions for '{args.skill_id}':")
    print()

    # Column widths
    ver_width = max(len(v.get("version", "?")) for v in versions) + 2
    ver_width = max(ver_width, 10)

    header = f"  {'Version':<{ver_width}} Published"
    print(header)
    print(f"  {'-' * (ver_width + 30)}")

    for v in sorted(
        versions,
        key=lambda x: x.get("created_at", x.get("published_at", "")),
    ):
        ver = v.get("version", "?")
        date = v.get("created_at", v.get("published_at", "?"))
        print(f"  {ver:<{ver_width}} {date}")
    print()
