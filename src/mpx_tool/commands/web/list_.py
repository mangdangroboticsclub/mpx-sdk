"""mpx web list — list seeded web skills in the GCS bucket."""

from __future__ import annotations

import argparse
import re
import sys

from mpx_tool.sdk.gcs import GcsClient, GcsError


def add_web_list_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("list", help="List seeded web skills (GCS)")


def cmd_web_list(args: argparse.Namespace) -> None:
    client = GcsClient()
    print(f'Fetching skills from GCS bucket "{client.bucket}"...')
    print()

    try:
        items = client.list_objects(prefix="user-scripts/")
    except GcsError as e:
        print(f"  ✗ Failed to list skills: {e}", file=sys.stderr)
        sys.exit(1)

    if not items:
        print("  No skills found in bucket.")
        return

    domains: set[str] = set()
    for item in items:
        match = re.match(r"^user-scripts/([^/]+)/", item.get("name", ""))
        if match:
            domains.add(match.group(1))

    names = {i.get("name", "") for i in items}
    sorted_domains = sorted(domains)

    print(f"  Found {len(sorted_domains)} skill(s):\n")
    for domain in sorted_domains:
        files = []
        if f"user-scripts/{domain}/manifest.json" in names:
            files.append("manifest.json")
        if f"user-scripts/{domain}/skill.js" in names:
            files.append("skill.js")
        print(f"  {domain}")
        print(f"    Files: {', '.join(files)}")
        print()
