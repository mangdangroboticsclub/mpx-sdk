#!/usr/bin/env python3
"""Generate sdk/include/mpx/gaits.h from the firmware's gait table.

A gait's numeric value is a wire protocol: the SDK sends a name, the firmware
maps it to `robot::GaitCmd`, and if the two lists disagree the robot performs a
different move than the one you named. Silently. That makes this exactly the
kind of table no one should be maintaining by hand.

Two inputs, and the split matters:

  * The firmware      -- which gaits exist, their numbers, and the wire names
                         it will accept. Authoritative; read, never written.
  * abi/gaits.json    -- what each one is called in the SDK, what it does,
                         whether it holds or returns, how long it takes.
                         Human-authored, because none of that is in the C++.

The generator fails if the two disagree in either direction: a gait the
firmware accepts but nobody has described, or a description for a gait the
firmware would reject. Both are bugs, and both are invisible at runtime.

    python tools/gen_gaits.py --check     verify (CI)
    python tools/gen_gaits.py --write     regenerate
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FW_ENUM = ROOT.parent / "mangdang" / "main" / "robot" / "robot.h"
FW_NAMES = ROOT.parent / "mangdang" / "main" / "robot" / "robot.cc"
META = ROOT / "abi" / "gaits.json"
OUT = ROOT / "sdk" / "include" / "mpx" / "gaits.h"

KIND_ENUM = {"holds": "MPX_GAIT_HOLDS", "returns": "MPX_GAIT_RETURNS",
             "cycles": "MPX_GAIT_CYCLES"}


def parse_firmware() -> list[tuple[str, int]]:
    """[(wire_name, numeric_value)] for every gait robot_gait() accepts."""
    for p in (FW_ENUM, FW_NAMES):
        if not p.is_file():
            sys.exit(f"error: {p} not found — this generator reads the firmware repo.")

    # robot::GaitCmd — the numbers. Implicit values continue from the last one,
    # exactly as C++ does, so a future gait added without "= n" still lands right.
    body = re.search(r"enum class GaitCmd\s*:\s*\w+\s*\{(.*?)\};",
                     FW_ENUM.read_text(encoding="utf-8", errors="replace"), re.S)
    if not body:
        sys.exit(f"error: no `enum class GaitCmd` in {FW_ENUM}")
    value, numbers = 0, {}
    for line in body.group(1).splitlines():
        line = re.sub(r"//.*|/\*.*?\*/", "", line).strip().rstrip(",").strip()
        if not line:
            continue
        m = re.match(r"^(\w+)\s*(?:=\s*(\d+))?$", line)
        if not m:
            continue
        if m.group(2) is not None:
            value = int(m.group(2))
        numbers[m.group(1)] = value
        value += 1

    # robot.cc's GAIT_NAMES[] — the wire names, and which enumerator each maps
    # to. This used to live as a strcmp chain in three separate files; it is one
    # table now, and a gait absent from it cannot be reached by name at all.
    pairs = re.findall(r'\{\s*"([^"]+)"\s*,\s*GaitCmd::(\w+)\s*\}',
                       FW_NAMES.read_text(encoding="utf-8", errors="replace"))
    if not pairs:
        sys.exit(f"error: no gait name table found in {FW_NAMES}")

    out = []
    for wire, enumerator in pairs:
        if enumerator not in numbers:
            sys.exit(f"error: robot_gait accepts \"{wire}\" -> GaitCmd::{enumerator}, "
                     f"which is not in the enum.")
        out.append((wire, numbers[enumerator]))
    return out


def render(gaits: list[tuple[str, int]], meta: dict) -> str:
    described = meta["gaits"]
    firmware_names = {w for w, _ in gaits}

    missing = [w for w in firmware_names if w not in described]
    if missing:
        sys.exit("error: the firmware accepts gaits nobody has described:\n"
                 + "".join(f"       {w}\n" for w in sorted(missing))
                 + f"       Add them to {META.relative_to(ROOT)}.")
    extra = [w for w in described if w not in firmware_names]
    if extra:
        sys.exit("error: described gaits the firmware would reject:\n"
                 + "".join(f"       {w}\n" for w in sorted(extra))
                 + "       Remove them, or check the firmware's name table.")

    ew = max(len(described[w]["enum"]) for w, _ in gaits)
    enum_lines = []
    for wire, value in gaits:
        d = described[wire]
        note = f"   /* firmware name: {wire} */" if _differs(d["enum"], wire) else ""
        enum_lines.append(f"    {d['enum']:<{ew}} = {value:>2},{note}")

    nw = max(len(described[w]['enum']) for w, _ in gaits)
    ww = max(len(w) for w, _ in gaits) + 2
    dw = max(len(described[w]['description']) for w, _ in gaits) + 2
    table = "\n".join(
        f'    {{ {described[w]["enum"]:<{nw}}, {chr(34)+w+chr(34):<{ww}}, '
        f'{chr(34)+described[w]["description"]+chr(34):<{dw}}, '
        f'{KIND_ENUM[described[w]["kind"]]:<18}, {described[w]["typical_ms"]:>5} }},'
        for w, _ in gaits)

    return f'''/* mpx/gaits.h — the movements the robot already knows.
 *
 * A gait is a motion the firmware performs for you. You name one; it does the
 * rest. This is the highest control layer and the only one where a mistake in
 * your maths cannot put the robot on its side.
 *
 * The catalogue carries more than names. `kind` is the field people trip over:
 *
 *   MPX_GAIT_HOLDS     stays in its final pose until you change it. If your
 *                      skill exits here, the robot stays here.
 *   MPX_GAIT_RETURNS   performs once and comes back to standing by itself.
 *   MPX_GAIT_CYCLES    repeats until you stop it.
 *
 * `typical_ms` is how long one performance naturally takes — 0 means it runs
 * until stopped. {{@link mpx_gait_play}} uses it so you can write the movement
 * without timing it by hand.
 *
 * GENERATED by `python tools/gen_gaits.py --write` from the firmware's
 * robot::GaitCmd enum and robot.cc's GAIT_NAMES table, merged with
 * abi/gaits.json. Do not edit: the numbers are a wire protocol.
 */
#ifndef MPX_GAITS_H
#define MPX_GAITS_H

#ifdef __cplusplus
extern "C" {{
#endif

typedef enum {{
{chr(10).join(enum_lines)}
}} mpx_gait_t;

/** How a gait behaves when it reaches the end of its motion. */
typedef enum {{
    MPX_GAIT_HOLDS   = 0,  /**< Stays in its final pose until you change it. */
    MPX_GAIT_RETURNS = 1,  /**< Performs once, returns to standing itself.   */
    MPX_GAIT_CYCLES  = 2,  /**< Repeats until stopped.                       */
}} mpx_gait_kind_t;

typedef struct {{
    mpx_gait_t       gait;
    const char      *wire_name;   /**< What the firmware is sent.            */
    const char      *description;
    mpx_gait_kind_t  kind;
    int              typical_ms;  /**< One performance; 0 = runs until stopped. */
}} mpx_gait_info_t;

static const mpx_gait_info_t MPX_GAITS[] = {{
{table}
}};

#define MPX_GAIT_COUNT ((int)(sizeof(MPX_GAITS) / sizeof(MPX_GAITS[0])))

/** Look a gait up in the catalogue. Returns 0 if the value is not a gait. */
static inline const mpx_gait_info_t *mpx_gait_info(mpx_gait_t g)
{{
    for (int i = 0; i < MPX_GAIT_COUNT; ++i)
        if (MPX_GAITS[i].gait == g) return &MPX_GAITS[i];
    return 0;
}}

/** The name the firmware knows a gait by, or "" if there is no such gait.
 *  {{@link mpx_gait}} uses this, so a gait value that is not in the catalogue
 *  becomes a refused call rather than an undefined move. */
static inline const char *mpx_gait_name(mpx_gait_t g)
{{
    const mpx_gait_info_t *info = mpx_gait_info(g);
    return info ? info->wire_name : "";
}}

/** How long one performance of a gait naturally takes, in ms.
 *  0 means it runs until you stop it. {{@link mpx_gait_play}} uses this. */
static inline int mpx_gait_typical_ms(mpx_gait_t g)
{{
    const mpx_gait_info_t *info = mpx_gait_info(g);
    return info ? info->typical_ms : 0;
}}

/** What a gait does when it finishes: holds, returns, or cycles. */
static inline mpx_gait_kind_t mpx_gait_kind(mpx_gait_t g)
{{
    const mpx_gait_info_t *info = mpx_gait_info(g);
    return info ? info->kind : MPX_GAIT_HOLDS;
}}

/** One line describing a gait, for logs and menus. */
static inline const char *mpx_gait_description(mpx_gait_t g)
{{
    const mpx_gait_info_t *info = mpx_gait_info(g);
    return info ? info->description : "";
}}

#ifdef __cplusplus
}}
#endif

#endif /* MPX_GAITS_H */
'''


def _differs(sdk_enum: str, wire: str) -> bool:
    return sdk_enum.replace("MPX_GAIT_", "").replace("_", "").lower() != wire.lower()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    text = render(parse_firmware(), json.loads(META.read_text(encoding="utf-8")))
    have = OUT.read_text(encoding="utf-8") if OUT.is_file() else None

    if args.check:
        if have != text:
            print(f"STALE  {OUT.relative_to(ROOT)}")
            print("       run: python tools/gen_gaits.py --write")
            return 1
        print(f"  ok    {OUT.relative_to(ROOT)}")
        return 0

    if args.write:
        OUT.write_text(text, encoding="utf-8")
        print(("  unchanged " if have == text else "  updated   ") + str(OUT.relative_to(ROOT)))
        return 0

    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
