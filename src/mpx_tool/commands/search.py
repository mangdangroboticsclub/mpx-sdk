"""mpx search — browse or search marketplace skills."""

from __future__ import annotations

import argparse
import json
import sys

from mpx_tool.sdk.gateway import GatewayClient, GatewayError


def add_search_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("search", help="Browse or search marketplace skills")
    p.add_argument("query", nargs="?", default=None, help="Optional search term")
    p.add_argument("--json", action="store_true", help="Output raw JSON instead of a table")


def cmd_search(args: argparse.Namespace) -> None:
    client = GatewayClient(gateway_url=getattr(args, "gateway_url", None))

    try:
        skills = client.list_skills()
    except GatewayError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    if args.query:
        q = args.query.lower()
        skills = [
            s for s in skills
            if q in str(s.get("title", "")).lower()
            or q in str(s.get("id", "")).lower()
            or q in str(s.get("skill_id", "")).lower()
            or q in str(s.get("slug", "")).lower()
            or q in str(s.get("description", "")).lower()
        ]

    if not skills:
        print(f"📭 {'No skills found matching ' + repr(args.query) if args.query else 'No skills in marketplace yet'}")
        return

    if args.json:
        print(json.dumps(skills, indent=2))
        return

    def _skill_id(s: dict) -> str:
        return str(s.get("id", s.get("skill_id", "?")))

    def _version(s: dict) -> str:
        return str(s.get("current_version", s.get("version", s.get("latest_version", "?"))))

    def _author(s: dict) -> str:
        raw = s.get("username", s.get("author"))
        if raw:
            return str(raw)
        sid = _skill_id(s)
        return sid.split("~")[0] if "~" in sid else "?"

    id_width = max(max(len(_skill_id(s)) for s in skills) + 2, 12)
    ver_width = 10
    user_width = max(max(len(_author(s)) for s in skills) + 2, 10)

    print(f"📋 {'Search results' if args.query else 'Marketplace skills'}:")
    print()
    header = f"  {'Skill ID':<{id_width}} {'Version':<{ver_width}} {'Author':<{user_width}} Title"
    print(header)
    print(f"  {'-' * (id_width + ver_width + user_width + 40)}")

    for s in sorted(skills, key=lambda x: str(x.get("title", ""))):
        print(f"  {_skill_id(s):<{id_width}} {_version(s):<{ver_width}} {_author(s):<{user_width}} {s.get('title', '?')}")
    print()
