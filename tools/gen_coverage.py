#!/usr/bin/env python3
"""Prove that everything the robot can do, a skill can do.

The SDK's central promise is that you never have to edit firmware to make the
robot move. A promise like that decays quietly: someone adds a capability to
`robot.h`, ships it to the web UI, and the SDK simply never learns about it.
Nobody notices, because nothing breaks -- makers just hit a wall and go patch
the firmware instead, which is the outcome this whole SDK exists to avoid.

So it is checked. This reads the firmware's public header, compares it against
abi/coverage.json, and fails on either kind of drift:

  * a firmware function nobody has classified  -- the new capability case
  * a classified function the firmware no longer has -- the stale mapping case

Anything deliberately not exposed must say why, in writing, in the JSON. That
turns "we decided not to" from tribal knowledge into a documented answer.

    python tools/gen_coverage.py --check     verify (CI)
    python tools/gen_coverage.py --write     regenerate the reference page
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FW_DIR = ROOT.parent / "mangdang" / "main"
MAP = ROOT / "abi" / "coverage.json"
ABI = ROOT / "abi" / "host_functions.json"
OUT = ROOT / "docs" / "internals" / "firmware-coverage.md"

AREAS = [
    ("gaits",       "Built-in gaits", "Movements the firmware already knows."),
    ("driving",     "Continuous driving", "Steering by velocity rather than by name."),
    ("body",        "Body attitude", "Roll, pitch and yaw with the feet planted."),
    ("feet",        "Feet", "Foot placement; the firmware solves the leg."),
    ("overlay",     "Overlay", "Adding to a frame something else produced, instead of replacing it."),
    ("joints",      "Joints", "Direct joint angles; you solve the leg."),
    ("bus",         "Servo bus", "Taking the bus to talk to the driver boards."),
    ("sensing",     "Sensing", "Reading the robot back."),
    ("calibration", "Calibration", "Per-joint zero offsets."),
]


def firmware_functions() -> list[str]:
    """Every free function declared in the firmware's public robot header."""
    src = FW_DIR / "robot" / "robot.h"
    if not src.is_file():
        return []
    names, text = [], src.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    for m in re.finditer(r"^\s*(?:[A-Za-z_][\w:<>,\s&*]*?)\s[\*&]?\s*([a-z_]\w*)\s*\([^;{]*\)\s*;",
                         text, re.M):
        name = m.group(1)
        if name not in names and name not in ("if", "for", "while", "return", "switch"):
            names.append(name)
    return names


def render(mapping: dict, abi_names: set[str]) -> str:
    fns = mapping["functions"]

    def row(name: str) -> str:
        e = fns[name]
        sdk = e.get("sdk") or e.get("abi") or []
        calls = " · ".join(f"`{c}()`" for c in sdk)
        note = e.get("note", "")
        return f"| `robot::{name}()` | {calls} | {note} |"

    parts = []
    for key, title, blurb in AREAS:
        rows = [row(n) for n, e in fns.items()
                if e.get("status") == "exposed" and e.get("area") == key]
        if not rows:
            continue
        parts.append(f"### {title}\n\n{blurb}\n\n"
                     "| Firmware | Call it from a skill with | |\n|---|---|---|\n"
                     + "\n".join(rows))

    withheld = [(n, e) for n, e in fns.items() if e.get("status") == "withheld"]
    internal = [n for n, e in fns.items() if e.get("status") == "internal"]

    withheld_md = "\n\n".join(f"**`robot::{n}()`** — {e['why']}" for n, e in withheld) \
        if withheld else "_Nothing._"

    exposed = sum(1 for e in fns.values() if e.get("status") == "exposed")

    return f"""# Firmware coverage

Everything the robot's firmware can do about movement, and the SDK call that
reaches it.

This page exists because of one specific failure mode. If a capability lands in
the firmware and never reaches the SDK, nothing breaks — makers just hit a wall
and go and patch the firmware themselves. That is the outcome this SDK exists
to prevent, and it is invisible unless something checks for it.

So this page is **generated and enforced**. `tools/gen_coverage.py` reads
`mangdang/main/robot/robot.h`, compares it against `abi/coverage.json`, and
fails the build if the firmware grows a function nobody has classified. CI runs
it on every push.

**{exposed} of {len(fns)} firmware functions are reachable from a skill.**
{len(internal)} are boot-time or sandbox plumbing with no meaning inside a
skill. {len(withheld)} are withheld on purpose, with the reason written down
below rather than left to be rediscovered.

{chr(10).join(chr(10) + p for p in parts)}

## Withheld on purpose

{withheld_md}

## Not applicable

Firmware plumbing that runs before a skill exists or after it ends:
{", ".join(f"`{n}()`" for n in internal)}.

`release_skill_bus_lock()` is worth knowing about even though you cannot call
it: the sandbox releases your bus lock when your skill ends, however it ends.
Forgetting `mpx_bus_release()` leaves the robot recoverable.

## If something is missing

Open an issue naming the firmware function. If the firmware can do it and the
SDK cannot, that is a bug in the SDK — not a reason to fork the firmware.

See also: [reference](../REFERENCE.md) ·
[how motion works](../MOVEMENT.md)
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    mapping = json.loads(MAP.read_text(encoding="utf-8"))
    fns = mapping["functions"]
    abi_names = {s["name"] for s in json.loads(ABI.read_text(encoding="utf-8"))["symbols"]}

    found = firmware_functions()
    problems = []
    if found:
        for name in found:
            if name not in fns:
                problems.append(
                    f"  firmware has robot::{name}() and abi/coverage.json does not mention it.\n"
                    f"    If a skill should be able to do this, expose it and add the mapping.\n"
                    f"    If not, add it with \"status\": \"withheld\" and say why.")
        for name in fns:
            if name not in found:
                problems.append(f"  abi/coverage.json maps robot::{name}(), which the firmware "
                                f"no longer declares. Remove it.")
    # every ABI symbol named in the mapping must actually exist
    for name, e in fns.items():
        for sym in e.get("abi", []):
            if sym not in abi_names:
                problems.append(f"  {name} claims ABI symbol '{sym}', which is not in ABI v3.")

    if problems:
        print("firmware coverage has drifted:\n" + "\n".join(problems))
        return 1

    if not found:
        print("  --    firmware repo not present; coverage mapping checked against the ABI only")

    text = render(mapping, abi_names)
    have = OUT.read_text(encoding="utf-8") if OUT.is_file() else None

    if args.check:
        if have != text:
            print(f"STALE  {OUT.relative_to(ROOT)}\n       run: python tools/gen_coverage.py --write")
            return 1
        print(f"  ok    {OUT.relative_to(ROOT)}  ({len(found)} firmware functions accounted for)")
        return 0

    if args.write:
        OUT.write_text(text, encoding="utf-8")
        print(("  unchanged " if have == text else "  updated   ") + str(OUT.relative_to(ROOT)))
        return 0

    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
