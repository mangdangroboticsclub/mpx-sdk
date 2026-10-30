"""mpx web seed — upload a web skill (manifest.json + skill.js) to GCS."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mpx_tool.sdk.gcs import GcsClient, GcsError


def add_web_seed_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("seed", help="Upload a web skill to GCS for local testing")
    p.add_argument("domain", help="Skill domain directory (e.g. bestbuy.com)")


def cmd_web_seed(args: argparse.Namespace) -> None:
    skill_dir = Path(args.domain).resolve()

    manifest_path = skill_dir / "manifest.json"
    skill_path = skill_dir / "skill.js"
    if not manifest_path.exists():
        print(f"❌ {args.domain}/manifest.json not found. Run 'mpx web init' first.", file=sys.stderr)
        sys.exit(1)
    if not skill_path.exists():
        print(f"❌ {args.domain}/skill.js not found.", file=sys.stderr)
        sys.exit(1)

    print(f'Seeding skill "{args.domain}" to GCS...')

    client = GcsClient()
    print(f"  Bucket: {client.bucket}")

    try:
        # Ensure the GCS bucket exists before uploading (fake-gcs-server
        # starts empty and we want a fresh 'mpx web up && mpx web seed'
        # to just work).
        client.ensure_bucket()
        client.upload(
            f"user-scripts/{args.domain}/manifest.json",
            manifest_path.read_bytes(),
            "application/json",
        )
        print("  ✓ manifest.json")
        client.upload(
            f"user-scripts/{args.domain}/skill.js",
            skill_path.read_bytes(),
            "application/javascript",
        )
        print("  ✓ skill.js")
    except GcsError as e:
        print(f"  ✗ {e}", file=sys.stderr)
        sys.exit(1)

    print(f'  ✅ Skill "{args.domain}" seeded successfully')
