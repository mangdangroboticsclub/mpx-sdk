"""mpx-cli upload — upload a .wasm skill to the robot."""

from __future__ import annotations

import argparse
from pathlib import Path
from mpx_cli.sdk.connection import RobotClient, RobotError


def add_upload_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("upload", help="Upload a .wasm skill to the robot")
    p.add_argument("wasm", help="Path to the .wasm file to upload")
    p.add_argument(
        "--ip", "-i",
        default=None,
        help="Robot IP address (default: 192.168.2.1)",
    )
    p.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help="Robot HTTP port (default: 80)",
    )


def cmd_upload(args: argparse.Namespace) -> None:
    wasm_path = Path(args.wasm)

    if not wasm_path.exists():
        print(f"❌ File not found: {wasm_path}")
        return

    if wasm_path.suffix != ".wasm":
        print("⚠️  Warning: file does not end with .wasm")

    client = RobotClient(
        host=args.ip or "192.168.2.1",
        port=args.port or 80,
    )

    print(f"📤 Uploading {wasm_path.name} to {client.host}:{client.port}...")

    try:
        result = client.upload_skill(str(wasm_path))
        if result.get("ok"):
            path = result.get("path", wasm_path.name)
            print(f"✅ Uploaded to '{path}'")
        else:
            print(f"❌ Upload failed: {result}")
    except RobotError as e:
        print(f"❌ {e}")
