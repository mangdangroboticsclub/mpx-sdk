"""mpx-cli init — scaffold a new skill.

What a scaffold is FOR is showing you the shape of a good skill, so this one
uses the API the documentation recommends rather than the raw imports
underneath it. The previous scaffold did the opposite: it called `print()` and
`robot_gait((int)"advance")` — precisely the two things the README told you not
to do — and told you to run a three-command build loop that `mpx-cli deploy`
had already replaced.

It also does not vendor the SDK headers. Copying an ABI snapshot into every new
project is how this repo ended up with four `mpx_host.h` files, two of them
stale and one still describing ABI v1. The compiler is pointed at the one copy
instead; see sdk/toolchain.py:sdk_include_dir().
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mpx_cli.sdk.toolchain import detect_all, sdk_include_dir

_RES = Path(__file__).resolve().parent / "resource"

EXT = {"c": "c", "ts": "ts", "wat": "wat"}


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.lstrip("\n"), encoding="utf-8")
    try:
        rel = path.relative_to(Path.cwd())
    except ValueError:
        rel = path.resolve()
    print(f"  created {rel}")


def _abi_version() -> int:
    """The ABI this SDK checkout describes, read from the generated JSON."""
    inc = sdk_include_dir()
    if inc:
        abi_json = inc.parent.parent / "abi" / "host_functions.json"
        if abi_json.is_file():
            try:
                return int(json.loads(abi_json.read_text())["abi_version"])
            except Exception:
                pass
    return 3


def add_init_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("init", help="Scaffold a new skill")
    p.add_argument("name", help="Skill name, e.g. my_wave")
    p.add_argument("--lang", "-l", choices=["c", "ts", "wat"], default="c",
                   help="c (default, and the only one with the friendly API), "
                        "ts (AssemblyScript) or wat (raw WebAssembly text)")
    p.add_argument("--dir", "-d", default=None,
                   help="Where to put it (default: ./<name>)")


def cmd_init(args: argparse.Namespace) -> None:
    name = args.name
    lang = args.lang
    ext = EXT[lang]
    out = Path(args.dir) if args.dir else Path(name)

    if out.exists():
        print(f"error: '{out}' already exists")
        return

    print(f"Creating skill '{name}' in {out}/\n")

    # ── source ────────────────────────────────────────────────────────────
    template = (_RES / f"skill.{ext}.template").read_text(encoding="utf-8")
    _write(out / "src" / f"{name}.{ext}", template.format(name=name))

    # ── AssemblyScript needs the generated bindings beside it ─────────────
    # C does not: the compiler is pointed at sdk/include and nothing is copied.
    # AssemblyScript resolves imports by path, so this one file is copied — and
    # stamped, so `mpx-cli build` can tell you when it has fallen behind and
    # `mpx-cli sync` can refresh it.
    _COPIED = {"ts":  ("src/mpx_env.ts",            "assemblyscript/mpx_env.ts"),
               "wat": ("include/host-functions.md", "wat/host-functions.md")}
    if lang in _COPIED:
        local_rel, sdk_rel = _COPIED[lang]
        inc = sdk_include_dir()
        master = (inc.parent / sdk_rel) if inc else None
        if master and master.is_file():
            _write(out / local_rel, master.read_text(encoding="utf-8"))
        else:
            print(f"  ! could not find sdk/{sdk_rel} — run "
                  "`python tools/gen_abi.py --write` in the SDK checkout")

    # ── manifest ──────────────────────────────────────────────────────────
    manifest = {
        "slug": name,
        "title": f"{name}",
        "skill_type": "WASM",
        "version": "0.1.0",
        "abi": _abi_version(),
        "readme": f"A movement for the MPX-Dog quadruped.",
        # Declared parameters become knobs: the CLI accepts --param for each,
        # and the robot's web UI renders a control. Delete what you do not use.
        "params": [
            {"name": "reach", "type": "float", "default": 20.0,
             "min": 0.0, "max": 40.0,
             "label": "How far the front feet reach forward (mm)"},
            {"name": "repeats", "type": "int", "default": 1,
             "min": 1, "max": 10,
             "label": "How many times to repeat"},
        ],
    }
    _write(out / "manifest.json", json.dumps(manifest, indent=2) + "\n")

    # ── README ────────────────────────────────────────────────────────────
    readme = (_RES / "README.md.template").read_text(encoding="utf-8")
    _write(out / "README.md", readme.format(name=name, ext=ext))

    # ── Makefile ──────────────────────────────────────────────────────────
    _write(out / "Makefile", f"""
# {name} — convenience wrapper around mpx-cli.
# Override the robot address:  make deploy MPX_HOST=10.0.0.5
export MPX_HOST ?= 192.168.2.1

.PHONY: deploy build logs clean

deploy:   ; mpx-cli deploy
build:    ; mpx-cli build
logs:     ; mpx-cli logs -f
clean:    ; rm -rf build
""")

    (out / "build").mkdir(parents=True, exist_ok=True)

    # ── toolchain report ──────────────────────────────────────────────────
    print()
    inc = sdk_include_dir()
    print(f"SDK headers: {inc if inc else 'NOT FOUND — set MPX_SDK_INCLUDE'}")
    for key, tc in detect_all().items():
        mark = "ok  " if tc.bin else "MISSING"
        print(f"  {mark} {tc.name}" + (f" ({tc.version})" if tc.bin else ""))

    print(f"""
Next:
  cd {out}
  mpx-cli deploy          build, upload and run
  mpx-cli logs -f         watch it

Read src/{name}.{ext} — it is a complete movement, not a stub.""")
