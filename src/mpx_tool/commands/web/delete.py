"""mpx web delete — remove a seeded web skill from the GCS bucket."""

from __future__ import annotations

import argparse
import sys

from mpx_tool.sdk.gcs import GcsClient, GcsError


def add_web_delete_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("delete", help="Delete a seeded web skill (GCS)")
    p.add_argument("domain", help="Skill domain (e.g. bestbuy.com)")


def cmd_web_delete(args: argparse.Namespace) -> None:
    client = GcsClient()
    print(f'Deleting skill "{args.domain}" from GCS bucket "{client.bucket}"...')

    try:
        items = client.list_objects(prefix=f"user-scripts/{args.domain}/")
    except GcsError as e:
        print(f"  ✗ Failed to list objects: {e}", file=sys.stderr)
        sys.exit(1)

    if not items:
        print(f'  No objects found for domain "{args.domain}". Nothing to delete.')
        return

    names = [i.get("name", "") for i in items if i.get("name")]
    print(f"  Found {len(names)} object(s) to delete:")
    for n in names:
        print(f"    - {n}")

    failures = 0
    for name in names:
        try:
            client.delete_object(name)
            print(f"  ✓ Deleted: {name}")
        except GcsError as e:
            print(f"  ✗ Failed to delete \"{name}\": {e}", file=sys.stderr)
            failures += 1

    if failures:
        print(f'  ⚠️  Skill "{args.domain}" partially deleted ({failures} failure(s))')
        sys.exit(1)
    print(f'  ✅ Skill "{args.domain}" deleted successfully')
