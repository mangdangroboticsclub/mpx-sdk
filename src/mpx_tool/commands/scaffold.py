"""Shared scaffolding helpers for ``mpx move init`` and ``mpx web init``.

Both families produce the same project skeleton contract:

  manifest.json  — marketplace metadata (see ``mpx_tool.manifest``)
  <doc>.md       — GUIDE.md, including the embedded
                   "Updating this GUIDE and the manifest metadata" section
  a family-specific source/artifact layout

Keeping the prompts, slug derivation, collision check, file writer and console
output here means the two ``init`` commands stay in lockstep.
"""

from __future__ import annotations

import importlib.resources
import re
import sys
from pathlib import Path

from mpx_tool.sdk.auth import get_username_from_token, read_token
from mpx_tool.sdk.gateway import GatewayClient, GatewayError


# ── Resources ────────────────────────────────────────────────────

def read_resource(package: str, name: str) -> str:
    """Return a vendored template's text, always decoded as UTF-8."""
    ref = importlib.resources.files(package) / name
    if not ref.is_file():
        raise FileNotFoundError(f"missing bundled resource {package}:{name}")
    with importlib.resources.as_file(ref) as path:
        # Templates are UTF-8 (banners, box drawing); read explicitly so
        # Windows' default cp1252 codec is never used.
        return Path(path).read_text(encoding="utf-8")


# ── Console helpers ──────────────────────────────────────────────

def prompt(question: str, default: str = "", *, enabled: bool = True) -> str:
    """Ask for a value, falling back to ``default`` when not interactive."""
    if not enabled or not sys.stdin.isatty():
        return default
    hint = f" ({default})" if default else ""
    try:
        return input(f"  {question}{hint}: ").strip() or default
    except EOFError:
        # stdin closed mid-questionnaire (piped input) — keep the default.
        print()
        return default


def write_file(path: Path, content: str) -> None:
    """Write a scaffolded file and report it relative to the cwd."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.lstrip("\n"), encoding="utf-8")
    _report(path)


def write_manifest_file(path: Path, manifest: dict) -> None:
    """Write ``manifest.json`` (identical JSON shape for both families)."""
    from mpx_tool.manifest import write_manifest

    path.parent.mkdir(parents=True, exist_ok=True)
    write_manifest(path, manifest)
    _report(path)


def _report(path: Path) -> None:
    try:
        rel = path.relative_to(Path.cwd())
    except ValueError:
        rel = path.resolve()
    print(f"  ✓ Created {rel}")


def derive_slug(text: str) -> str:
    """Normalize a name/domain into a marketplace-safe slug."""
    slug = re.sub(r"[^a-zA-Z0-9_-]", "", text.replace(".", "-")).strip("-_")
    return slug or "skill"


# ── Validation shared by both families ───────────────────────────

def check_slug_collision(slug: str, gateway_url: str | None = None) -> bool:
    """Warn when ``slug`` is already published. Returns True when taken."""
    token = read_token()
    if not token or not get_username_from_token(token):
        return False
    try:
        resp = GatewayClient(gateway_url=gateway_url).check_slug(slug, token)
    except GatewayError:
        return False  # Gateway unreachable — publish will surface it.
    if not (resp and resp.get("exists")):
        return False
    print(f'\n  ⚠️  Warning: Slug "{slug}" is already taken by one of your skills.')
    print("    Publishing will conflict with the existing skill.")
    print(f'    Pick a different slug, or pass --slug "{slug}-variant".\n')
    return True


def require_semver(version: str) -> str:
    """Validate an initial/edited version, exiting with a clear message."""
    from mpx_tool.manifest import parse_semver

    version = version.strip()
    if parse_semver(version) is None:
        print(f'  ❌ Invalid version "{version}" — must be semver (X.Y.Z).', file=sys.stderr)
        sys.exit(1)
    return version


def require_slug(slug: str) -> str:
    """Validate a slug (it becomes half of the marketplace skill id)."""
    slug = slug.strip()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", slug):
        print(
            f'  ❌ Invalid slug "{slug}" — use letters, digits, "-" or "_" (no leading dot/dash).',
            file=sys.stderr,
        )
        sys.exit(1)
    return slug


# ── Trailing guidance printed by every init ──────────────────────

def report_scaffolded(
    family: str,
    target: str,
    *,
    what: str,
    slug: str,
    title: str,
    version: str,
    language: str,
    doc: str,
    rows: list[tuple[str, str]],
) -> None:
    """Print the shared 'configuration / next steps / metadata' summary."""
    print()
    print(f'  ✅ {what} scaffolded for "{target}"')
    print()
    print("  Configuration:")
    print(f"    Slug:      {slug}")
    print(f"    Title:     {title}")
    print(f"    Version:   {version}")
    print(f"    Language:  {language}")
    print()
    print("  Next steps:")
    for label, value in rows:
        print(f"    {label:<12}{value}")
    print()
    print("  Metadata:")
    print(f"    Edit manifest.json — field table in {doc}")
    print('    → "Updating this GUIDE and the manifest metadata"')
    print(f"    Or edit interactively:  mpx {family} update-manifest <dir>")
    print()
