"""Shared publish command — one code path for WASM (move) and AWA (web) skills.

The skill family is detected from the project's ``manifest.json``
(``skill_type``), and the artifact is found accordingly:

  - ``skill_type: WASM``  → ``build/*.wasm`` (or ``src/*.wasm``)
  - anything else         → ``skill.js`` (JavaScript artifact)
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

from mpx_tool.manifest import parse_semver, write_manifest
from mpx_tool.sdk.auth import (
    get_username_from_token,
    read_state,
    read_token,
    write_state,
)
from mpx_tool.sdk.gateway import GatewayClient, GatewayError

_WASM_TYPES = {"WASM"}
_MAX_WASM_BYTES = 256 * 1024


def add_publish_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("publish", help="Publish a skill to the marketplace")
    p.add_argument(
        "dir",
        nargs="?",
        default=".",
        help="Skill directory (default: current directory)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Skip the skill-identity lock check",
    )


# ── Semver helpers ──────────────────────────────────────────────

_parse_semver = parse_semver  # kept for backward-compatible imports


def _prompt_semver_bump(current_version: str) -> str | None:
    parsed = _parse_semver(current_version)
    if parsed is None:
        print(f"⚠️  Cannot parse version '{current_version}' for auto-bump")
        return None
    major, minor, patch = parsed

    print(f"   Current remote version: {current_version}")
    print("   Choose bump:")
    print(f"     1) patch  → {major}.{minor}.{patch + 1}")
    print(f"     2) minor  → {major}.{minor + 1}.0")
    print(f"     3) major  → {major + 1}.0.0")
    print("     4) cancel")

    choice = input("   Select [1-4]: ").strip()
    if choice == "1":
        return f"{major}.{minor}.{patch + 1}"
    if choice == "2":
        return f"{major}.{minor + 1}.0"
    if choice == "3":
        return f"{major + 1}.0.0"
    return None


# ── Family detection / artifact discovery ────────────────────────

def _infer_source_language(skill_dir: Path) -> str:
    src_dir = skill_dir / "src"
    if src_dir.is_dir():
        for f in sorted(src_dir.iterdir()):
            if f.suffix == ".c":
                return "c"
            if f.suffix == ".wat":
                return "wat"
            if f.suffix == ".ts":
                return "ts"
    return "c"


def _find_wasm(skill_dir: Path) -> Path | None:
    build_dir = skill_dir / "build"
    if build_dir.is_dir():
        wasm_files = list(build_dir.glob("*.wasm"))
        if wasm_files:
            return wasm_files[0]
    src_dir = skill_dir / "src"
    if src_dir.is_dir():
        wasm_files = list(src_dir.glob("*.wasm"))
        if wasm_files:
            return wasm_files[0]
    return None


# ── Main flow ────────────────────────────────────────────────────

def cmd_publish(args: argparse.Namespace) -> None:
    token = read_token()
    if not token:
        print("❌ Not logged in. Run 'mpx login' first.", file=sys.stderr)
        sys.exit(1)

    username = get_username_from_token(token)
    if not username:
        print("❌ Invalid token. Run 'mpx login' again.", file=sys.stderr)
        sys.exit(1)

    skill_dir = Path(args.dir).resolve()
    if not skill_dir.is_dir():
        print(f"❌ Directory not found: {skill_dir}", file=sys.stderr)
        sys.exit(1)

    manifest_path = skill_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"❌ No manifest.json found in {skill_dir}", file=sys.stderr)
        print("   Run 'mpx move init' or 'mpx web init' to scaffold a project.")
        sys.exit(1)

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"❌ Invalid manifest.json: {e}", file=sys.stderr)
        sys.exit(1)

    slug = manifest.get("slug") or manifest.get("domain") or skill_dir.name
    title = manifest.get("title", slug)
    version = str(manifest.get("version", "1.0.0")).strip()
    if _parse_semver(version) is None:
        print(f'❌ Invalid version "{version}". Must be semver (X.Y.Z).', file=sys.stderr)
        sys.exit(1)

    skill_type = str(manifest.get("skill_type", "AWA")).upper()

    # ── Resolve artifact per family ──────────────────────────────
    if skill_type in _WASM_TYPES:
        wasm_path = _find_wasm(skill_dir)
        if not wasm_path:
            print("❌ No .wasm file found in build/ or src/.", file=sys.stderr)
            print("   Run 'mpx move build' first.", file=sys.stderr)
            sys.exit(1)
        wasm_size = wasm_path.stat().st_size
        if wasm_size == 0:
            print("❌ WASM file is empty", file=sys.stderr)
            sys.exit(1)
        if wasm_size > _MAX_WASM_BYTES:
            print(f"❌ WASM file too large ({wasm_size} bytes, max 256 KB)", file=sys.stderr)
            sys.exit(1)

        source_language = _infer_source_language(skill_dir)
        artifact_b64 = base64.b64encode(wasm_path.read_bytes()).decode("ascii")
        manifest["skill_type"] = "WASM"
        manifest["source_language"] = source_language
        manifest["username"] = username
        print(f"📦 WASM skill — {wasm_path} ({wasm_size / 1024:.1f} KB)")
    else:
        supported = {"AWA", "CAPABILITY"}
        if skill_type not in supported:
            print(
                f"❌ Unsupported skill_type \"{manifest.get('skill_type')}\" in manifest.json. "
                f"Supported: {', '.join(sorted(supported))}.",
                file=sys.stderr,
            )
            sys.exit(1)
        skill_path = skill_dir / "skill.js"
        if not skill_path.exists():
            print(f"❌ {skill_path} not found.", file=sys.stderr)
            sys.exit(1)

        source_language = "javascript"
        artifact_b64 = base64.b64encode(skill_path.read_bytes()).decode("ascii")
        manifest["skill_type"] = skill_type
        manifest["source_language"] = source_language
        print(f"📦 {skill_type} skill — {skill_path} ({skill_path.stat().st_size} bytes)")

    skill_id = f"{username}~{slug}"

    # ── Identity lock (slug ↔ skill_type) ────────────────────────
    state = read_state()
    if not args.force:
        locked = state.get(skill_id)
        if locked and locked.get("skill_type") != skill_type:
            print(
                f"❌ Skill identity '{skill_id}' was first published as "
                f"type '{locked.get('skill_type')}'. Pick a different slug.",
                file=sys.stderr,
            )
            sys.exit(1)

    # ── Publish ──────────────────────────────────────────────────
    client = GatewayClient(gateway_url=getattr(args, "gateway_url", None))
    print(f"📤 Publishing '{title}' ({skill_id}) v{version}...")

    def _do_publish(ver: str) -> tuple[int, dict]:
        return client.publish(
            skill_id=skill_id,
            title=title,
            version=ver,
            artifact_b64=artifact_b64,
            manifest=manifest,
            token=token,
            skill_type=skill_type,
            source_language=source_language,
        )

    try:
        status, body = _do_publish(version)
    except GatewayError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    while status == 409:
        current_remote = body.get("current_version", body.get("version", "?"))
        print(f"⚠️  Version conflict: v{version} already exists (remote: v{current_remote})")
        new_version = _prompt_semver_bump(current_remote)
        if new_version is None:
            print("Cancelled.")
            return

        manifest["version"] = new_version
        write_manifest(manifest_path, manifest)
        print(f"   Updated manifest.json version to {new_version}")
        version = new_version
        try:
            status, body = _do_publish(version)
        except GatewayError as e:
            print(f"❌ {e}", file=sys.stderr)
            sys.exit(1)

    if status in (200, 201):
        print(f"✅ Published '{title}' v{version}")
        if "message" in body:
            print(f"   {body['message']}")
        if "path" in body:
            print(f"   📍 {body['path']}")
        state[skill_id] = {
            "skill_type": skill_type,
            "dir": str(skill_dir),
            "slug": slug,
        }
        write_state(state)
    else:
        error_msg = body.get("error", body.get("message", str(body))) if isinstance(body, dict) else str(body)
        print(f"❌ Publish failed (HTTP {status}): {error_msg}", file=sys.stderr)
        sys.exit(1)
