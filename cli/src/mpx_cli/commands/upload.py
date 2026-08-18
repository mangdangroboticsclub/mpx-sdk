"""mpx-cli upload — upload a .wasm skill to the robot."""

from __future__ import annotations

import argparse
from pathlib import Path
from mpx_cli.sdk.connection import RobotClient, RobotError
from mpx_cli.sdk.project import describe_missing, find_project


def add_upload_parser(sub: argparse._SubParsersAction) -> None:
    from mpx_cli.cli import robot_opts

    p = sub.add_parser(
        "upload",
        parents=[robot_opts()],
        help="Upload a .wasm skill to the robot",
    )
    p.add_argument(
        "wasm", nargs="?",
        help="Path to the .wasm file (default: build/<slug>.wasm from manifest.json)",
    )


def _resolve_wasm(args: argparse.Namespace) -> Path | None:
    """Explicit path wins; otherwise derive it from the project manifest."""
    if args.wasm:
        return Path(args.wasm)

    project = find_project()
    if project is None:
        print(f"❌ {describe_missing('.wasm file')}")
        return None

    print(f"📦 {project.slug} (from {project.root / 'manifest.json'})")
    return project.wasm


def cmd_upload(args: argparse.Namespace) -> bool:
    wasm_path = _resolve_wasm(args)
    if wasm_path is None:
        return False

    if not wasm_path.exists():
        print(f"❌ File not found: {wasm_path}")
        print("   Run 'mpx-cli build' first.")
        return False

    if wasm_path.suffix != ".wasm":
        print("⚠️  Warning: file does not end with .wasm")

    client = RobotClient(host=args.ip, port=args.port)

    print(f"📤 Uploading {wasm_path.name} to {client.host}:{client.port}...")

    try:
        result = client.upload_skill(str(wasm_path))
        if result.get("ok"):
            path = result.get("path", wasm_path.name)
            print(f"✅ Uploaded to '{path}'")
            return True
        print(f"❌ Upload failed: {result}")
        return False
    except RobotError as e:
        print(f"❌ {e}")
        return False
