"""Token and state file management for mpx-cli cloud features.

Stores:
  - JWT token at ``~/.mpx-cli-token`` (mode ``0o600``)
  - Slug-to-domain mapping at ``~/.mpx-cli-state.json``

These files are intentionally separate from the ``mpx-awa`` equivalents
to avoid cross-tool conflicts.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

# ── File paths ────────────────────────────────────────────────────
TOKEN_FILE = Path.home() / ".mpx-cli-token"
STATE_FILE = Path.home() / ".mpx-cli-state.json"


# ── Token operations ──────────────────────────────────────────────

def read_token() -> str | None:
    """Read the JWT from ``~/.mpx-cli-token``.

    Returns ``None`` if the file does not exist or is empty.
    """
    if not TOKEN_FILE.exists():
        return None
    try:
        token = TOKEN_FILE.read_text().strip()
        return token if token else None
    except OSError:
        return None


def write_token(token: str) -> None:
    """Write a JWT to ``~/.mpx-cli-token`` with mode ``0o600``.

    Creates the file and sets permissions so only the owner can read it.
    """
    TOKEN_FILE.write_text(token.strip() + "\n")
    # Restrict to owner read/write only
    TOKEN_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)


def clear_token() -> None:
    """Remove the token file if it exists."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()


def get_username_from_token(token: str) -> str | None:
    """Decode the payload segment of a JWT to extract the ``username`` claim.

    This does **not** verify the signature — it simply base64-decodes the
    second (payload) segment of the JWT and reads the ``username`` field.
    This is safe for local display purposes only.
    """
    import base64

    parts = token.split(".")
    if len(parts) != 3:
        return None

    try:
        # JWT payload is base64url-encoded
        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        decoded = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(decoded)
        return payload.get("username")
    except (json.JSONDecodeError, Exception):
        return None


# ── State file operations ─────────────────────────────────────────

def read_state() -> dict:
    """Read the slug-to-domain mapping from ``~/.mpx-cli-state.json``.

    Returns an empty dict if the file does not exist or is malformed.
    """
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text())
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def write_state(state: dict) -> None:
    """Write the slug-to-domain mapping to ``~/.mpx-cli-state.json``."""
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")
