"""mpx web init — scaffold an AWA (web automation) skill.

Usage:
  mpx web init <domain>
  mpx web init <slug>@<domain>       # multiple skills for same domain

Parity contract with ``mpx move init``: same prompts (slug / title / version),
same ``--slug`` / ``--dir`` / ``--yes`` flags, same slug-collision check, same
exit code on an existing directory, same console summary, and the manifest /
GUIDE metadata contract embedded into the generated docs.

Creates manifest.json, skill.js and GUIDE.md in ./<domain>/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mpx_tool.commands.scaffold import (
    check_slug_collision,
    derive_slug,
    prompt,
    read_resource,
    report_scaffolded,
    require_semver,
    require_slug,
    write_file,
    write_manifest_file,
)
from mpx_tool.manifest import metadata_section

_RES = "mpx_tool.commands.resource.web"


def add_web_init_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("init", help="Scaffold an AWA (web automation) skill")
    p.add_argument("target", help="Domain (bestbuy.com) or slug@domain")
    p.add_argument("--dir", "-d", default=None, help="Output directory (default: ./<target>)")
    p.add_argument("--slug", "-s", default=None, help="Marketplace slug (default: derived from domain)")
    p.add_argument("--title", "-t", default=None, help="Marketplace title (default: '<domain> merchant skill')")
    p.add_argument("--version", default=None, help="Initial version (default: 1.0.0)")
    p.add_argument("--yes", "-y", action="store_true", help="Accept defaults without prompting")


def cmd_web_init(args: argparse.Namespace) -> None:
    raw = args.target
    interactive = not args.yes

    # Parse slug@domain format
    if "@" in raw and not raw.startswith("@") and not raw.endswith("@"):
        inline_slug, domain = raw.split("@", 1)
    else:
        domain, inline_slug = raw, None

    target_dir = Path(args.dir) if args.dir else Path(raw)
    target_dir = target_dir.resolve()

    if target_dir.exists():
        print(f'❌ Directory "{raw}" already exists.', file=sys.stderr)
        sys.exit(1)

    print(f'\n  📋 Scaffolding AWA skill for "{raw}"\n')

    slug_default = derive_slug(domain)
    slug = require_slug(
        args.slug
        or inline_slug
        or prompt("Slug (short marketplace identifier)", slug_default, enabled=interactive)
    )
    title = args.title or prompt("Title", f"{domain} merchant skill", enabled=interactive)
    version = require_semver(args.version or prompt("Version", "1.0.0", enabled=interactive))

    check_slug_collision(slug, getattr(args, "gateway_url", None))

    # ── Create directory + files ──────────────────────────────────
    target_dir.mkdir(parents=True, exist_ok=False)

    manifest_content = (
        read_resource(_RES, "manifest.json")
        .replace("{{DOMAIN}}", domain)
        .replace("{{SLUG}}", slug)
        .replace("{{VERSION}}", version)
    )
    write_file(target_dir / "manifest.json", manifest_content)

    write_file(
        target_dir / "skill.js",
        read_resource(_RES, "skill.js").replace("{{DOMAIN}}", domain).replace("{{SLUG}}", slug),
    )

    # ── Docs (GUIDE.md carries the shared metadata contract) ─────
    guide = read_resource(_RES, "GUIDE.md")
    write_file(target_dir / "GUIDE.md", f"{guide.rstrip()}\n\n{metadata_section('AWA')}")

    report_scaffolded(
        "web",
        raw,
        what="AWA skill",
        slug=slug,
        title=title,
        version=version,
        language="javascript",
        doc="GUIDE.md",
        rows=[
            ("cd", raw),
            ("runtime", "mpx web up"),
            ("seed", f"mpx web seed {raw}"),
            ("test", f"mpx web session start {slug} --robot <uuid>"),
            ("publish", "mpx publish ."),
            ("docs", "GUIDE.md"),
        ],
    )
