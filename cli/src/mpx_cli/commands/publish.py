"""mpx-cli publish — publish a skill directory to the marketplace."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

from mpx_cli.sdk.auth import (
    read_token,
    get_username_from_token,
    read_state,
    write_state,
)
from mpx_cli.sdk.gateway import GatewayClient, GatewayError


def add_publish_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("publish", help="Publish a skill to the marketplace")
    p.add_argument("dir", help="Path to the skill directory (with manifest.json and build/)")
    p.add_argument(
        "--force",
        action="store_true",
        help="Skip slug lock check",
    )


def _infer_source_language(skill_dir: Path) -> str:
    """Determine the source language by inspecting the ``src/`` directory."""
    src_dir = skill_dir / "src"
    if not src_dir.is_dir():
        return "c"  # default fallback

    for f in sorted(src_dir.iterdir()):
        if f.suffix == ".c":
            return "c"
        if f.suffix == ".wat":
            return "wat"
        if f.suffix == ".ts":
            return "ts"
    return "c"


def _prompt_semver_bump(current_version: str) -> str | None:
    """Offer interactive semver bump (patch/minor/major/cancel).

    Returns the new version string, or ``None`` if cancelled.
    """
    parts = current_version.split(".")
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    except (ValueError, IndexError):
        print(f"⚠️  Cannot parse version '{current_version}' for auto-bump")
        return None

    print(f"   Current remote version: {current_version}")
    print("   Choose bump:")
    print(f"     1) patch  → {major}.{minor}.{patch + 1}")
    print(f"     2) minor  → {major}.{minor + 1}.0")
    print(f"     3) major  → {major + 1}.0.0")
    print("     4) cancel")

    choice = input("   Select [1-4]: ").strip()
    if choice == "1":
        return f"{major}.{minor}.{patch + 1}"
    elif choice == "2":
        return f"{major}.{minor + 1}.0"
    elif choice == "3":
        return f"{major + 1}.0.0"
    else:
        return None


def cmd_publish(args: argparse.Namespace) -> None:
    """Handle ``mpx-cli publish <dir>``."""

    # 1. Check authentication
    token = read_token()
    if not token:
        print("❌ Not logged in. Run 'mpx-cli login' first.", file=sys.stderr)
        sys.exit(1)

    username = get_username_from_token(token)
    if not username:
        print("❌ Invalid token. Run 'mpx-cli login' again.", file=sys.stderr)
        sys.exit(1)

    # 2. Resolve skill directory
    skill_dir = Path(args.dir)
    if not skill_dir.is_dir():
        print(f"❌ Directory not found: {skill_dir}", file=sys.stderr)
        sys.exit(1)

    # 3. Read manifest.json
    manifest_path = skill_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"❌ No manifest.json found in {skill_dir}", file=sys.stderr)
        print("   Run 'mpx-cli init' to scaffold a project with a manifest.")
        sys.exit(1)

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        print(f"❌ Invalid manifest.json: {e}", file=sys.stderr)
        sys.exit(1)

    slug = manifest.get("slug")
    title = manifest.get("title", slug or "Untitled Skill")
    version = manifest.get("version", "1.0.0")

    if not slug:
        print("❌ manifest.json missing 'slug' field", file=sys.stderr)
        sys.exit(1)

    # 4. Find compiled WASM
    # Look in build/<name>.wasm first, then src/<name>.wasm
    wasm_path = None
    build_dir = skill_dir / "build"
    if build_dir.is_dir():
        wasm_files = list(build_dir.glob("*.wasm"))
        if wasm_files:
            wasm_path = wasm_files[0]

    if not wasm_path:
        # Fallback: check src/ for .wasm files
        src_dir = skill_dir / "src"
        if src_dir.is_dir():
            wasm_files = list(src_dir.glob("*.wasm"))
            if wasm_files:
                wasm_path = wasm_files[0]

    if not wasm_path:
        print(f"❌ No .wasm file found in build/ or src/", file=sys.stderr)
        print("   Run 'mpx-cli build' first.", file=sys.stderr)
        sys.exit(1)

    # 5. Validate WASM
    wasm_size = wasm_path.stat().st_size
    if wasm_size > 256 * 1024:
        print(f"❌ WASM file too large ({wasm_size} bytes, max 256 KB)", file=sys.stderr)
        sys.exit(1)
    if wasm_size == 0:
        print(f"❌ WASM file is empty", file=sys.stderr)
        sys.exit(1)

    # 6. Check slug lock (unless --force)
    state = read_state()
    if not args.force:
        locked_owner = state.get(slug)
        if locked_owner and locked_owner != username:
            print(f"❌ Slug '{slug}' is locked to user '{locked_owner}'", file=sys.stderr)
            print("   Use --force to override (not recommended).")
            sys.exit(1)

    # 7. Enforce read-only manifest fields
    skill_id = f"{username}~{slug}"
    source_language = _infer_source_language(skill_dir)
    manifest["skill_type"] = "WASM"
    manifest["source_language"] = source_language
    manifest["username"] = username

    # 8. Read and encode WASM artifact
    artifact_b64 = base64.b64encode(wasm_path.read_bytes()).decode("ascii")

    # 9. Publish
    client = GatewayClient(gateway_url=getattr(args, "gateway_url", None))
    print(f"📤 Publishing '{title}' ({skill_id}) v{version}...")
    print(f"   WASM: {wasm_path} ({wasm_size / 1024:.1f} KB)")
    print(f"   Language: {source_language}")

    try:
        status, body = client.publish(
            skill_id=skill_id,
            title=title,
            version=version,
            artifact_b64=artifact_b64,
            manifest=manifest,
            token=token,
        )
    except GatewayError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    # 10. Handle version conflict (HTTP 409)
    if status == 409:
        current_remote = body.get("current_version", body.get("version", "?"))
        print(f"⚠️  Version conflict: v{version} already exists (remote: v{current_remote})")
        new_version = _prompt_semver_bump(current_remote)
        if new_version is None:
            print("Cancelled.")
            return

        # Update manifest.json on disk
        manifest["version"] = new_version
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"   Updated manifest.json version to {new_version}")

        # Retry
        print(f"📤 Retrying publish v{new_version}...")
        try:
            status, body = client.publish(
                skill_id=skill_id,
                title=title,
                version=new_version,
                artifact_b64=artifact_b64,
                manifest=manifest,
                token=token,
            )
        except GatewayError as e:
            print(f"❌ {e}", file=sys.stderr)
            sys.exit(1)

    # 11. Final status
    if status in (200, 201):
        print(f"✅ Published '{title}' v{manifest.get('version', version)}")
        if "message" in body:
            print(f"   {body['message']}")

        # Record slug lock
        state[slug] = username
        write_state(state)
    else:
        error_msg = body.get("error", body.get("message", str(body)))
        print(f"❌ Publish failed (HTTP {status}): {error_msg}", file=sys.stderr)
        sys.exit(1)
