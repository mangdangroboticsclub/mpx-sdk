"""mpx-cli sync — refresh a project's generated bindings from the SDK.

C skills copy nothing: the compiler is pointed at the one `sdk/include`, so
there is never anything to sync and this command says so.

AssemblyScript and WAT resolve imports by path, so those projects hold one
generated file each. That file is the only copy of anything in a project, and
this is how you keep it current after the SDK's ABI moves.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from mpx_cli.sdk.project import find_project
from mpx_cli.sdk.toolchain import sdk_include_dir

# What each language keeps locally, and where the SDK's copy of it lives.
BINDINGS = {
    ".ts":  ("src/mpx_env.ts",       "assemblyscript/mpx_env.ts"),
    ".wat": ("include/host-functions.md", "wat/host-functions.md"),
}


def add_sync_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("sync", help="Refresh this project's generated bindings from the SDK")
    p.add_argument("--check", action="store_true",
                   help="Report staleness without writing anything (exit 1 if stale)")


def _sdk_abi(inc: Path) -> int | None:
    j = inc.parent.parent / "abi" / "host_functions.json"
    if j.is_file():
        try:
            return int(json.loads(j.read_text(encoding="utf-8"))["abi_version"])
        except Exception:
            return None
    return None


def cmd_sync(args: argparse.Namespace) -> None:
    project = find_project()
    if project is None:
        print("error: no manifest.json here or in any parent directory.")
        return

    inc = sdk_include_dir()
    if inc is None:
        print("error: could not find the SDK headers.")
        print("       export MPX_SDK_INCLUDE=/path/to/mpx-sdk/sdk/include")
        return
    sdk_root = inc.parent            # .../sdk
    abi = _sdk_abi(inc)

    src = project.source
    ext = src.suffix if src else ".c"

    if ext not in BINDINGS:
        print(f"{project.slug} is a C project — nothing to sync.")
        print(f"  Headers come from {inc} at build time; no copy is kept here.")
        if abi:
            print(f"  SDK is ABI v{abi}.")
        _check_manifest_abi(project, abi, args.check)
        return

    local_rel, sdk_rel = BINDINGS[ext]
    local = project.root / local_rel
    master = sdk_root / sdk_rel

    if not master.is_file():
        print(f"error: {master} not found. Run:  python tools/gen_abi.py --write")
        return

    want = master.read_text(encoding="utf-8")
    have = local.read_text(encoding="utf-8") if local.is_file() else None

    if have == want:
        print(f"{local_rel} is up to date (ABI v{abi}).")
    elif args.check:
        old = re.search(r"ABI version (\d+)", have or "")
        print(f"STALE  {local_rel}"
              + (f" — it is ABI v{old.group(1)}, the SDK is v{abi}" if old and abi else ""))
        print("Run:  mpx-cli sync")
        raise SystemExit(1)
    else:
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(want, encoding="utf-8")
        print(f"updated {local_rel}  ->  ABI v{abi}")

    _check_manifest_abi(project, abi, args.check)


def _check_manifest_abi(project, abi: int | None, check_only: bool) -> None:
    if abi is None:
        return
    declared = project.manifest.get("abi")
    if declared == abi:
        return
    path = project.root / "manifest.json"
    if check_only:
        print(f'STALE  manifest.json says "abi": {declared}, the SDK is v{abi}')
        raise SystemExit(1)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["abi"] = abi
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f'updated manifest.json  ->  "abi": {abi}')
