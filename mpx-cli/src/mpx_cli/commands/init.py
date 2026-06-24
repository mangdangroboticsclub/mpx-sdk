"""mpx-cli init — scaffold a new skill development project."""

from __future__ import annotations

import argparse
from pathlib import Path
from mpx_cli.sdk.toolchain import detect_all

# ── Resolve paths to resource files ──────────────────────────────
_HERE = Path(__file__).resolve().parent
_RES_DIR = _HERE / "resource"

# ── Template sources (loaded from resource/ files) ──────────────

_skill_c = (_RES_DIR / "skill.c.template").read_text()

_skill_wat = (_RES_DIR / "skill.wat.template").read_text()

_skill_ts = (_RES_DIR / "skill.ts.template").read_text()

_readme_template_c = (_RES_DIR / "README_c.md.template").read_text()
_readme_template_wat = (_RES_DIR / "README_wat.md.template").read_text()
_readme_template_ts = (_RES_DIR / "README_ts.md.template").read_text()

_host_functions_wat = (_RES_DIR / "host_functions_wat.md").read_text()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.lstrip("\n"))
    try:
        rel = path.relative_to(Path.cwd())
    except ValueError:
        rel = path.resolve()
    print(f"  📝 Created {rel}")


def add_init_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("init", help="Scaffold a new skill development project")
    p.add_argument("name", help="Skill name (e.g. my_skill)")
    p.add_argument(
        "--lang", "-l",
        choices=["c", "wat", "ts"],
        default="c",
        help="Language: c (default), wat, or ts (AssemblyScript)",
    )
    p.add_argument(
        "--dir", "-d",
        default=None,
        help="Output directory (default: ./<name>)",
    )


def cmd_init(args: argparse.Namespace) -> None:
    name = args.name
    lang = args.lang
    out_dir = Path(args.dir) if args.dir else Path(name)

    if out_dir.exists():
        print(f"❌ Directory '{out_dir}' already exists")
        return

    ext_map = {"c": "c", "wat": "wat", "ts": "ts"}
    ext = ext_map[lang]

    print(f"🚀 Initializing skill project '{name}' in {out_dir}/")
    print()

    # Create directory structure
    src_dir = out_dir / "src"

    src_dir.mkdir(parents=True, exist_ok=True)

    # Write source file
    templates = {"c": _skill_c, "wat": _skill_wat, "ts": _skill_ts}
    _write(src_dir / f"{name}.{ext}", templates[lang].format(name=name))

    # Write host function declaration file (language-specific)
    if lang == "c":
        include_dir = out_dir / "include"
        include_dir.mkdir(parents=True, exist_ok=True)
        _write(include_dir / "mpx_host.h", MPX_HOST_H_CONTENT)
    elif lang == "ts":
        include_dir = out_dir / "include"
        include_dir.mkdir(parents=True, exist_ok=True)
        _write(include_dir / "mpx_env.ts", MPX_ENV_TS_CONTENT)
    elif lang == "wat":
        include_dir = out_dir / "include"
        include_dir.mkdir(parents=True, exist_ok=True)
        _write(include_dir / "host_functions.md", _host_functions_wat)

    # Write README
    readme_templates = {"c": _readme_template_c, "wat": _readme_template_wat, "ts": _readme_template_ts}
    _write(out_dir / "README.md", readme_templates[lang].format(name=name))

    # Write Makefile
    makefile = (
        f"# {name} — MPX-Dog WASM Skill\n"
        f"# Convenience wrapper around mpx-cli.\n\n"
        f"MPX_HOST ?= 192.168.2.1\n"
        f"SRC := src/{name}.{ext}\n"
        f"WASM := src/{name}.wasm\n\n"
        f".PHONY: build validate upload run clean\n\n"
        f"build:\n"
        f"\tmpx-cli build $(SRC)\n\n"
        f"validate:\n"
        f"\tmpx-cli build $(SRC) --validate\n\n"
        f"upload:\n"
        f"\tmpx-cli upload $(WASM) --host $(MPX_HOST)\n\n"
        f"run:\n"
        f"\tmpx-cli run {name}.wasm --host $(MPX_HOST)\n\n"
        f"clean:\n"
        f"\trm -f src/*.wasm\n"
    )
    _write(out_dir / "Makefile", makefile)

    # Detect and show toolchains
    print()
    tcs = detect_all()
    print("🔧 Toolchain status:")
    for key, tc in tcs.items():
        if tc.bin:
            print(f"  ✅ {tc.name}: {tc.bin} ({tc.version})")
        else:
            print(f"  ⚠️  {tc.name}: not found")
    print()
    print(f"✅ Project '{name}' initialized! See {out_dir / 'README.md'} to get started.")


# ── Header content (loaded from resource/ files) ──────────────────

MPX_HOST_H_CONTENT = (_RES_DIR / "mpx_host.h").read_text()
MPX_ENV_TS_CONTENT = (_RES_DIR / "mpx_env.ts").read_text()
