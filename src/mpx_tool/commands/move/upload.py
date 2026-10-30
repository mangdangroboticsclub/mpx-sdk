"""mpx move upload — upload a .wasm skill to the robot."""

from __future__ import annotations

import argparse
from pathlib import Path

from mpx_tool.config import DEFAULT_ROBOT_HOST, DEFAULT_ROBOT_PORT
from mpx_tool.sdk.robot import RobotClient, RobotError


def add_move_upload_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("upload", help="Upload a .wasm skill to the robot")
    p.add_argument("wasm", help="Path to the .wasm file to upload")
    p.add_argument("--ip", "-i", default=None, help=f"Robot IP address (default: {DEFAULT_ROBOT_HOST})")
    p.add_argument("--port", "-p", type=int, default=None, help=f"Robot HTTP port (default: {DEFAULT_ROBOT_PORT})")


def cmd_move_upload(args: argparse.Namespace) -> None:
    wasm_path = Path(args.wasm)

    if not wasm_path.exists():
        print(f"❌ File not found: {wasm_path}")
        return

    client = RobotClient(
        host=args.ip or DEFAULT_ROBOT_HOST,
        port=args.port or DEFAULT_ROBOT_PORT,
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
