"""mpx-cli gaits — the catalogue of built-in movements.

There are 46 of them and their names are terse (`buttshrugL`, `blegR`,
`headellipse`). Before this command the only way to find out what one did was
to run it and watch, which is a slow way to browse a list that long and an
alarming one if the robot is on a table.

The catalogue is read from `sdk/include/mpx/gaits.h`, which is generated from
the firmware's own enum — so this cannot describe a gait the robot does not
have, or miss one it does.
"""

from __future__ import annotations

import argparse
import re

from mpx_cli.sdk.toolchain import sdk_include_dir

_ROW = re.compile(
    r'\{\s*(MPX_GAIT_[A-Z_0-9]+)\s*,\s*"([^"]+)"\s*,\s*'
    r'((?:"(?:[^"\\]|\\.)*"\s*)+),\s*(MPX_GAIT_[A-Z]+)\s*,\s*(-?\d+)\s*\}'
)

_ENDING = {"MPX_GAIT_HOLDS": "holds", "MPX_GAIT_RETURNS": "returns", "MPX_GAIT_CYCLES": "cycles"}


def _catalogue() -> list[dict]:
    inc = sdk_include_dir()
    if not inc:
        return []
    path = inc / "mpx" / "gaits.h"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    out = []
    for enum, wire, summary_raw, ending, ms in _ROW.findall(text):
        summary = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', summary_raw))
        out.append({
            "enum": enum,
            "wire": wire,
            "summary": summary.strip(),
            "ending": _ENDING.get(ending, ending),
            "typical_ms": int(ms),
        })
    return out


def add_gaits_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("gaits", help="List the robot's built-in movements")
    p.add_argument("filter", nargs="?", help="Only show gaits matching this text")
    p.add_argument("--names", action="store_true",
                   help="Just the C enum names, one per line (for scripting)")


def cmd_gaits(args: argparse.Namespace) -> None:
    rows = _catalogue()
    if not rows:
        print("Could not find sdk/include/mpx/gaits.h.")
        print("Run this from inside the SDK checkout, or set MPX_SDK_INCLUDE.")
        return

    if args.filter:
        needle = args.filter.lower()
        rows = [r for r in rows
                if needle in r["enum"].lower()
                or needle in r["wire"].lower()
                or needle in r["summary"].lower()]
        if not rows:
            print(f"Nothing matches '{args.filter}'.")
            return

    if args.names:
        for r in rows:
            print(r["enum"])
        return

    w = max(len(r["enum"]) for r in rows)
    print(f"{len(rows)} built-in movements. Call one with mpx_gait(NAME) "
          f"or mpx_gait_for(NAME, ms).\n")
    print(f"{'NAME'.ljust(w)}  ENDING   TYPICAL  WHAT IT DOES")
    print(f"{'-' * w}  -------  -------  ------------")
    for r in rows:
        ms = f"{r['typical_ms']}ms" if r["typical_ms"] else "-"
        print(f"{r['enum'].ljust(w)}  {r['ending'].ljust(7)}  {ms.rjust(7)}  {r['summary']}")
    print("""
ENDING is what happens when you stop asking for it:
  holds    stays in its final pose  -- it will still be there when your skill exits
  returns  comes back to standing on its own
  cycles   repeats until you stop it

TYPICAL is a duration that looks right; '-' means it runs until stopped.
mpx_gait_once(NAME) uses it for you.""")
