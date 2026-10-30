"""Unified token/state file management (Decision #3).

Stores:
  - JWT session token at ``~/.mpx-token`` (mode ``0o600``)
  - Publish state at ``~/.mpx-state.json``

Legacy files (``~/.mpx-cli-token``, ``~/.mpx-awa-token``, etc.) are
migrated automatically on first read.
"""

from __future__ import annotations

import base64
import json
import stat
from pathlib import Path

from mpx_tool.config import LEGACY_FILES, STATE_FILE, TOKEN_FILE

# Legacy token files (credentials) — migrated in order of precedence.
_LEGACY_TOKENS = [
    Path.home() / ".mpx-cli-token",
    Path.home() / ".mpx-awa-token",
]

# Legacy state files — merged (not replaced) into the unified state.
_LEGACY_STATES = [
    Path.home() / ".mpx-cli-state.json",
    Path.home() / ".mpx-awa-state.json",
]


# ── Migration ────────────────────────────────────────────────────

def _migrate_token() -> None:
    """Copy the first available legacy token into ~/.mpx-token."""
    if TOKEN_FILE.exists():
        return
    for legacy in _LEGACY_TOKENS:
        if legacy.exists():
            token = legacy.read_text().strip()
            if token:
                write_token(token)
            return


def _merge_state(state: dict) -> dict:
    """Merge legacy state files into the unified state (once)."""
    for legacy in _LEGACY_STATES:
        if not legacy.exists():
            continue
        try:
            legacy_state = json.loads(legacy.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(legacy_state, dict):
            # Keys from legacy tools: mpx-cli used {slug: username};
            # mpx-awa used {"username~domain": slug}. Store them under
            # their own namespace to avoid clobbering the new schema.
            for key, value in legacy_state.items():
                if key not in state:
                    state[key] = value
    return state


def _migrated_state() -> dict:
    state = read_state()
    state = _merge_state(state)
    write_state(state)
    return state


# ── Token operations ─────────────────────────────────────────────

def read_token() -> str | None:
    """Return the stored JWT, migrating legacy tokens if needed."""
    _migrate_token()
    if not TOKEN_FILE.exists():
        return None
    try:
        token = TOKEN_FILE.read_text().strip()
        return token if token else None
    except OSError:
        return None


def write_token(token: str) -> None:
    """Write the JWT to ``~/.mpx-token`` with mode ``0o600``."""
    TOKEN_FILE.write_text(token.strip() + "\n")
    TOKEN_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)


def clear_token() -> None:
    """Remove the unified token file."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()


def get_username_from_token(token: str) -> str | None:
    """Decode the ``username`` claim from a JWT payload (no signature check)."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        payload_b64 = parts[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload.get("username")
    except Exception:
        return None


# ── State operations ─────────────────────────────────────────────

def read_state() -> dict:
    """Read ``~/.mpx-state.json`` ({} if absent or malformed)."""
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text())
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def write_state(state: dict) -> None:
    """Write the unified state file."""
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")
