"""mpx update-manifest — interactively edit a project's manifest metadata.

Shared by both families (registered as a top-level command and under
``mpx move …`` / ``mpx web …``), because ``mpx publish`` reads one manifest
contract regardless of ``skill_type``.

Interactive mode prompts for each editable field with the current value as the
default (Enter keeps it). Non-interactive / scripted mode takes flags:

  mpx update-manifest . --version 1.2.0 --readme "Now supports checkout"

With no flags and no TTY, the current values are printed instead of prompting.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mpx_tool.commands.scaffold import prompt
from mpx_tool.manifest import family_label, is_wasm, parse_semver, read_manifest, write_manifest

# Editable fields, in prompt order. `applies_to_web` fields are skipped for WASM.
_EDITABLE: tuple[tuple[str, str, bool], ...] = (
    ("slug", "Slug (short marketplace identifier)", True),
    ("title", "Title", True),
    ("version", "Version (X.Y.Z)", True),
    ("readme", "Readme (one-paragraph summary)", True),
    ("domain", "Domain (site this skill drives)", False),
)

_FLAG_TO_FIELD = {
    "slug": "slug",
    "title": "title",
    "version": "version",
    "readme": "readme",
    "domain": "domain",
}


def add_update_manifest_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        "update-manifest",
        help="Interactively edit manifest.json metadata (slug/title/version/readme/domain)",
    )
    p.add_argument("dir", nargs="?", default=".", help="Skill directory (default: current directory)")
    p.add_argument("--slug", default=None, help="Set slug without prompting")
    p.add_argument("--title", default=None, help="Set title without prompting")
    p.add_argument("--version", default=None, help="Set version (semver X.Y.Z) without prompting")
    p.add_argument("--readme", default=None, help="Set readme summary without prompting")
    p.add_argument("--domain", default=None, help="Set domain without prompting (web skills)")
    p.add_argument("--dry-run", action="store_true", help="Show the resulting manifest without writing")


def _prompt_field(manifest: dict, field: str, question: str) -> str:
    current = str(manifest.get(field, ""))
    return prompt(question, current)


def _ask_field(manifest: dict, field: str, question: str) -> str:
    """Prompt for one field, re-asking while a version is not semver."""
    while True:
        value = _prompt_field(manifest, field, question).strip()
        if field != "version" or not value or parse_semver(value) is not None:
            return value
        print("  ❌ Version must be semver (X.Y.Z) — try again, or press Enter to keep the current one.")


def cmd_update_manifest(args: argparse.Namespace) -> None:
    skill_dir = Path(args.dir).resolve()
    if not skill_dir.is_dir():
        print(f"❌ Directory not found: {skill_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        manifest_path, manifest = read_manifest(skill_dir)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        print("   Run 'mpx move init' or 'mpx web init' to scaffold a project.", file=sys.stderr)
        sys.exit(1)

    wasm = is_wasm(manifest)
    family = family_label(manifest)

    provided = {
        field: getattr(args, flag)
        for flag, field in _FLAG_TO_FIELD.items()
        if getattr(args, flag, None) is not None
    }
    if provided.get("domain") is not None and wasm:
        print("❌ '--domain' only applies to web (AWA) skills.", file=sys.stderr)
        sys.exit(1)
    if provided.get("version") is not None and parse_semver(provided["version"]) is None:
        print(f'❌ Invalid version "{provided["version"]}" — must be semver (X.Y.Z).', file=sys.stderr)
        sys.exit(1)

    interactive = sys.stdin.isatty()
    updates: dict[str, str] = {}

    if provided:
        updates.update(provided)
    elif interactive:
        print(f"\n  ✏️  Editing {manifest_path}\n")
        for field, question, applies_to_web in _EDITABLE:
            if not applies_to_web and wasm:
                continue
            if field not in manifest and field == "domain":
                continue  # only offer domain when the manifest already declares one
            value = _ask_field(manifest, field, question)
            if value and value != str(manifest.get(field, "")):
                updates[field] = value
    else:
        print(f"  {manifest_path} (skill_type={manifest.get('skill_type', 'AWA')})")
        for field, _question, applies_to_web in _EDITABLE:
            if not applies_to_web and wasm:
                continue
            if field in manifest:
                print(f"    {field:<10} {manifest[field]}")
        print()
        print("  No changes: not a terminal. Pass flags to update, e.g.")
        print(f"    mpx {family} update-manifest . --version 1.1.0")
        return

    if not updates:
        print("\n  No changes.\n")
        return

    for field in ("slug", "title", "version", "readme", "domain"):
        if field not in updates:
            continue
        value = updates[field]
        if field == "version" and parse_semver(value) is None:
            print(f'❌ Invalid version "{value}" — must be semver (X.Y.Z).', file=sys.stderr)
            sys.exit(1)
        old = manifest.get(field)
        manifest[field] = value
        if str(old) == str(value):
            print(f"  · {field}: {value} (unchanged)")
        else:
            print(f"  ✓ {field}: {old if old is not None else '(unset)'} → {value}")

    if args.dry_run:
        print()
        print(json.dumps(manifest, indent=2))
        print("\n  (dry run — nothing written)\n")
        return

    write_manifest(manifest_path, manifest)
    print()
    print(f"  ✅ Updated {manifest_path.name}")
    print(f"  Next: mpx publish {args.dir}\n")
