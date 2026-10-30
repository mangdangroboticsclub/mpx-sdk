"""Central configuration: defaults, paths, environment overrides.

All decision #1-9 values from the design doc live here in one place.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── App identity ────────────────────────────────────────────────
APP_NAME = "mpx"

# ── Gateway (marketplace / auth / publish) ──────────────────────
# Decision #2: canonical default, overridable via env.
DEFAULT_GATEWAY_URL = os.environ.get("MPX_GATEWAY_URL", "http://skills.mangdang.org:8080")

# ── Robot (move family) ─────────────────────────────────────────
DEFAULT_ROBOT_HOST = os.environ.get("MPX_HOST", "192.168.2.1")
DEFAULT_ROBOT_PORT = int(os.environ.get("MPX_PORT", "80"))

# ── AWA worker + GCS (web family) ───────────────────────────────
DEFAULT_AWA_WORKER_URL = os.environ.get("AWA_WORKER_URL", "http://localhost:9808")
DEFAULT_GCS_EMULATOR_URL = os.environ.get("GCS_EMULATOR_URL", "http://localhost:4443")
DEFAULT_GCS_BUCKET = os.environ.get("GCS_BUCKET", "awa-skills-dev")

# ── Auth / state files (Decision #3: unified) ───────────────────
TOKEN_FILE = Path.home() / ".mpx-token"
STATE_FILE = Path.home() / ".mpx-state.json"

# Legacy token/state files, migrated once on first run.
LEGACY_FILES = [
    Path.home() / ".mpx-cli-token",
    Path.home() / ".mpx-awa-token",
    Path.home() / ".mpx-cli-state.json",
    Path.home() / ".mpx-awa-state.json",
]

# ── Pinned Docker images (Decision #8: silverhusky personal hub for now)
MOVE_TOOLCHAIN_IMAGE = os.environ.get(
    "MPX_MOVE_TOOLCHAIN_IMAGE", "silverhusky/mpx-move-toolchain:0.1.0"
)
WEB_WORKER_IMAGE = os.environ.get(
    "MPX_WEB_WORKER_IMAGE", "silverhusky/mpx-web-worker:0.1.0"
)
GCS_EMULATOR_IMAGE = os.environ.get(
    "MPX_GCS_EMULATOR_IMAGE", "fsouza/fake-gcs-server:latest"
)
