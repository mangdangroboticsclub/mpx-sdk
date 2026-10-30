"""mpx web up / down — start and stop the web runtime (worker + GCS).

Auto-pulls the pinned Docker Hub images before bringing the stack up.
"""

from __future__ import annotations

import argparse

from mpx_tool.config import GCS_EMULATOR_IMAGE, WEB_WORKER_IMAGE
from mpx_tool.sdk.docker import (
    DockerError,
    compose_down,
    compose_up,
    ensure_image,
)
from mpx_tool.sdk.gcs import GcsClient


def add_web_runtime_parsers(sub: argparse._SubParsersAction) -> None:
    sub.add_parser("up", help="Start the web runtime (AWA worker + GCS emulator)")
    sub.add_parser("down", help="Stop the web runtime")


def cmd_web_up(args: argparse.Namespace) -> None:
    ensure_image(WEB_WORKER_IMAGE)
    ensure_image(GCS_EMULATOR_IMAGE)
    try:
        compose_up()
    except DockerError as e:
        print(f"❌ {e}")
        raise SystemExit(1)

    # fake-gcs-server starts with an empty data volume — create the
    # skills bucket if it doesn't already exist, so seed/list/delete work.
    client = GcsClient()
    try:
        client.ensure_bucket()
        print(f'  ✅ GCS bucket "{client.bucket}" ready')
    except Exception as e:  # noqa: BLE001 — surface a clear warning, not a crash
        print(f'  ⚠️  Could not create GCS bucket "{client.bucket}": {e}')


def cmd_web_down(args: argparse.Namespace) -> None:
    try:
        compose_down()
    except DockerError as e:
        print(f"❌ {e}")
        raise SystemExit(1)
