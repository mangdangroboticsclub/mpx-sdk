"""mpx-cli — MPX-Dog Skill Development Kit.

This package auto-loads environment variables from ``.env`` files before
the CLI modules read defaults. Supported locations:

* the current working directory: ``./.env``
* the installed package directory: ``src/mpx_cli/.env`` during development

Environment variables defined in the real process environment always win.
"""

from __future__ import annotations

import os
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    try:
        for line in path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        return


_PACKAGE_DIR = Path(__file__).resolve().parent
_load_env_file(Path.cwd() / ".env")
_load_env_file(_PACKAGE_DIR / ".env")

__version__ = "0.2.0"
