"""mpx move init — scaffold a robot (WASM) skill project.

Parity contract with ``mpx web init``: same prompts (slug / title / version),
same ``--slug`` / ``--dir`` / ``--yes`` flags, same slug-collision check, same
exit code on an existing directory, same console summary, and the manifest /
GUIDE metadata contract embedded into the generated docs.
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

_RES = "mpx_tool.commands.resource.move"


def add_move_init_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("init", help="Scaffold a robot (WASM) skill project")
    p.add_argument("name", help="Skill name (e.g. my_skill)")
    p.add_argument(
        "--lang", "-l",
        choices=["c", "wat", "ts"],
        default="c",
        help="Language: c (default), wat, or ts (AssemblyScript)",
    )
    p.add_argument("--dir", "-d", default=None, help="Output directory (default: ./<name>)")
    p.add_argument("--slug", "-s", default=None, help="Marketplace slug (default: derived from name)")
    p.add_argument("--title", "-t", default=None, help="Marketplace title (default: '<name> — MPX-Dog skill')")
    p.add_argument("--version", default=None, help="Initial version (default: 1.0.0)")
    p.add_argument("--yes", "-y", action="store_true", help="Accept defaults without prompting")


def cmd_move_init(args: argparse.Namespace) -> None:
    name = args.name
    lang = args.lang
    out_dir = Path(args.dir) if args.dir else Path(name)
    interactive = not args.yes

    if out_dir.exists():
        print(f'❌ Directory "{out_dir}" already exists.', file=sys.stderr)
        sys.exit(1)

    print(f'\n  📋 Scaffolding WASM skill for "{name}"\n')

    slug = require_slug(args.slug or prompt("Slug (short marketplace identifier)", derive_slug(name), enabled=interactive))
    title = args.title or prompt("Title", f"{name} — MPX-Dog skill", enabled=interactive)
    version = require_semver(args.version or prompt("Version", "1.0.0", enabled=interactive))

    check_slug_collision(slug, getattr(args, "gateway_url", None))

    out_dir.mkdir(parents=True, exist_ok=False)

    # ── Sources + language-specific includes ─────────────────────
    src_dir = out_dir / "src"
    write_file(src_dir / f"{name}.{lang}", read_resource(_RES, f"skill.{lang}.template").format(name=name))

    include_dir = out_dir / "include"
    include_resource = {
        "c": ("mpx_host.h", "mpx_host.h"),
        "ts": ("mpx_env.ts", "mpx_env.ts"),
        "wat": ("host_functions.md", "host_functions_wat.md"),
    }[lang]
    include_name, include_template = include_resource
    write_file(include_dir / include_name, read_resource(_RES, include_template))

    # ── Docs (GUIDE carries the shared metadata contract) ────────
    guide = read_resource(_RES, f"GUIDE_{lang}.md.template").format(name=name)
    guide = f"{guide.rstrip()}\n\n{metadata_section('WASM')}"
    write_file(out_dir / "GUIDE.md", guide)

    makefile = (
        f"# {name} — MPX-Dog WASM Skill\n"
        f"# Convenience wrapper around mpx.\n\n"
        f"MPX_HOST ?= 192.168.2.1\n"
        f"SRC := src/{name}.{lang}\n"
        f"WASM := build/{name}.wasm\n\n"
        f".PHONY: build upload run publish clean\n\n"
        f"build:\n"
        f"\tmpx move build $(SRC)\n\n"
        f"upload:\n"
        f"\tmpx move upload $(WASM) --ip $(MPX_HOST)\n\n"
        f"run:\n"
        f"\tmpx move run {name}.wasm --ip $(MPX_HOST)\n\n"
        f"publish:\n"
        f"\tmpx publish .\n\n"
        f"clean:\n"
        f"\trm -f build/*.wasm\n"
    )
    write_file(out_dir / "Makefile", makefile)

    write_manifest_file(
        out_dir / "manifest.json",
        {
            "slug": slug,
            "title": title,
            "skill_type": "WASM",
            "source_language": lang,
            "version": version,
            "readme": "A WASM skill for the MPX-Dog quadruped robot.",
        },
    )

    (out_dir / "build").mkdir(parents=True, exist_ok=True)

    report_scaffolded(
        "move",
        name,
        what="WASM skill",
        slug=slug,
        title=title,
        version=version,
        language=lang,
        doc="GUIDE.md",
        rows=[
            ("cd", str(out_dir)),
            ("build", f"mpx move build src/{name}.{lang}"),
            ("upload", f"mpx move upload build/{name}.wasm --ip <robot-ip>"),
            ("run", f"mpx move run {name}.wasm --ip <robot-ip>"),
            ("publish", "mpx publish ."),
            ("docs", "GUIDE.md"),
        ],
    )
