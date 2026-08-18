"""mpx-cli search — browse marketplace skills."""

from __future__ import annotations

import argparse
import sys

from mpx_cli.sdk.gateway import GatewayClient, GatewayError


def add_search_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("search", help="Browse or search marketplace skills")
    p.add_argument("query", nargs="?", default=None, help="Optional search term")
    p.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of a table",
    )


def cmd_search(args: argparse.Namespace) -> None:
    """Handle ``mpx-cli search [query]``."""
    client = GatewayClient(gateway_url=getattr(args, "gateway_url", None))

    try:
        skills = client.list_skills()
    except GatewayError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    # Filter by query if provided
    if args.query:
        q = args.query.lower()
        skills = [
            s for s in skills
            if q in s.get("title", "").lower()
            or q in s.get("id", "").lower()
            or q in s.get("skill_id", "").lower()
            or q in s.get("slug", "").lower()
            or q in s.get("description", "").lower()
        ]

    if not skills:
        if args.query:
            print(f"📭 No skills found matching '{args.query}'")
        else:
            print("📭 No skills in marketplace yet")
        return

    if args.json:
        import json
        print(json.dumps(skills, indent=2))
        return

    # Table output
    print(f"📋 {'Search results' if args.query else 'Marketplace skills'}:")
    print()

    def _skill_id(s: dict) -> str:
        return s.get("id", s.get("skill_id", "?"))

    def _version(s: dict) -> str:
        return s.get("current_version", s.get("version", s.get("latest_version", "?")))

    def _author(s: dict) -> str:
        raw = s.get("username", s.get("author", None))
        if raw:
            return raw
        # Extract username from id field (format: username~slug)
        sid = _skill_id(s)
        if sid and "~" in sid:
            return sid.split("~")[0]
        return "?"

    # Column widths
    id_width = max(len(_skill_id(s)) for s in skills) + 2
    id_width = max(id_width, 12)
    ver_width = 10
    user_width = max(len(_author(s)) for s in skills) + 2
    user_width = max(user_width, 10)

    header = (
        f"  {'Skill ID':<{id_width}} {'Version':<{ver_width}} {'Author':<{user_width}} Title"
    )
    print(header)
    print(f"  {'-' * (id_width + ver_width + user_width + 40)}")

    for s in sorted(skills, key=lambda x: x.get("title", "")):
        sid = _skill_id(s)
        ver = _version(s)
        author = _author(s)
        title = s.get("title", "?")
        print(f"  {sid:<{id_width}} {ver:<{ver_width}} {author:<{user_width}} {title}")
    print()
