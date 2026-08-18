#!/usr/bin/env python3
"""Generate sdk/include/mpx/params.h from the driver board's parameter table.

These indices are a wire protocol: `servo_set_gain(id, N, v)` writes whatever
the driver board keeps at slot N. Getting N wrong does not fail — it sets a
different parameter, silently, and `mpx_gain_save()` can burn that into the
board's flash where a reboot will not clear it.

This SDK had them hand-written, and hand-written meant wrong:

    firmware slot 4 = reverse_motor        SDK called 4 = KP_POSITION
    firmware slot 5 = kp_position          SDK called 5 = KD_POSITION
    firmware slot 6 = kd_position          SDK called 6 = KI_POSITION (no such thing)
    firmware slot 8 = kff_current          SDK called 8 = KI_CURRENT  (no such thing)
    firmware slot 9 = max_pwm_duty_cycle   SDK called 9 = CURRENT_LIMIT (no such thing)

So `mpx_gain_set(j, MPX_PARAM_KP_POSITION, 95.0f)` wrote 95.0 into
*reverse_motor* — reversing one joint's direction, persistently. Everything
above that joint then walked mirrored, with nothing on screen to explain it.

That is the whole argument for generating this file. Two inputs:

  * robot/driver_board.h   the DB_PARAM_* enum — the slots themselves
  * robot/driver_board.c   param_names[] — what each slot is called
  * sdk/wasm_host_functions.cc  param_is_read_only() — which are refused

    python tools/gen_params.py --check     verify (CI)
    python tools/gen_params.py --write     regenerate
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FW = ROOT.parent / "mangdang" / "main"
OUT = ROOT / "sdk" / "include" / "mpx" / "params.h"

# What each slot is for, in words. The firmware carries the name and the
# number; a person has to supply the meaning.
NOTES = {
    "reverse_position_sensor": ("Flip which way the position sensor counts.",
                                "Calibration. Changing it re-defines every angle."),
    "min_position_adc":        ("Bottom of the sensor's usable range.", "Calibration."),
    "max_position_adc":        ("Top of the sensor's usable range.", "Calibration."),
    "range_position_deg":      ("Degrees the raw range spans.", "Calibration."),
    "reverse_motor":           ("Flip which way the motor drives.",
                                "DANGEROUS. One joint moving opposite to the other "
                                "eleven is how a robot destroys itself."),
    "kp_position":             ("Stiffness: how hard it pulls to target. Stock 65.", ""),
    "kd_position":             ("Damping: resists overshoot. Stock 800.", ""),
    "kp_current":              ("Gain of the inner current loop.",
                                "Torque response. Raise it and the joint feels "
                                "sharper; too far and it buzzes."),
    "kff_current":             ("Current fed forward from the position error.",
                                "Anticipation. Helps a joint under constant load "
                                "(the robot's own weight) stop sagging."),
    "max_pwm_duty_cycle":      ("Ceiling on drive effort, 0..1.",
                                "Your torque limit. Lower it to make a joint "
                                "physically unable to hurt anything."),
}


def parse():
    hdr = (FW / "robot" / "driver_board.h")
    src = (FW / "robot" / "driver_board.c")
    sdk = (FW / "sdk" / "wasm_host_functions.cc")
    for p in (hdr, src, sdk):
        if not p.is_file():
            sys.exit(f"error: {p} not found — this generator reads the firmware repo.")

    body = re.search(r"DB_PARAM_REVERSE_POSITION_SENSOR\s*=\s*0,(.*?)DB_PARAM_COUNT",
                     hdr.read_text(encoding="utf-8", errors="replace"), re.S)
    if not body:
        sys.exit("error: DB_PARAM_* enum not found")
    slots = ["DB_PARAM_REVERSE_POSITION_SENSOR"]
    for line in body.group(1).splitlines():
        line = re.sub(r"/\*.*?\*/", "", line).strip().rstrip(",").strip()
        m = re.match(r"^(DB_PARAM_\w+)$", line)
        if m:
            slots.append(m.group(1))

    names = re.search(r"param_names\[DB_PARAM_COUNT\]\s*=\s*\{(.*?)\};",
                      src.read_text(encoding="utf-8", errors="replace"), re.S)
    if not names:
        sys.exit("error: param_names[] not found")
    wire = re.findall(r'"([a-z_]+)"', names.group(1))

    if len(wire) != len(slots):
        sys.exit(f"error: {len(slots)} enum slots but {len(wire)} names — "
                 f"the firmware's own table disagrees with itself.")

    ro = set(re.findall(r"param ==\s*(DB_PARAM_\w+)",
                        sdk.read_text(encoding="utf-8", errors="replace")))
    return list(zip(range(len(slots)), slots, wire)), ro


def render(rows, ro) -> str:
    lines, table = [], []
    for idx, enum, name in rows:
        sdk_name = "MPX_PARAM_" + name.upper()
        what, note = NOTES.get(name, ("", ""))
        flag = "  /* read-only from a skill */" if enum in ro else ""
        lines.append(f"    {sdk_name:<34} = {idx},{flag}")
        table.append(f"    {{ {sdk_name:<34}, \"{name}\","
                     f" {'1' if enum in ro else '0'} }},")

    docs = "\n".join(
        f" *   {('MPX_PARAM_' + n.upper()):<34} {NOTES.get(n, ('',''))[0]}"
        + (f"\n *   {'':34} {NOTES[n][1]}" if NOTES.get(n, ('',''))[1] else "")
        for _, _, n in rows)

    return f'''/* mpx/params.h — the driver board's tunable parameters.
 *
 * Each of these is a slot on the servo's own controller. `mpx_gain_set()`
 * writes one; `mpx_gain_save()` can burn it into the board's flash, where a
 * reboot will not clear it.
 *
 * THE NUMBERS ARE A WIRE PROTOCOL. Writing the wrong slot does not fail — it
 * sets a different parameter. That is why this file is generated from the
 * firmware's own table rather than typed.
 *
{docs}
 *
 * READ-ONLY FROM A SKILL: the calibration parameters decide what every angle
 * MEANS. Change one and every command afterwards means something different,
 * including the built-in gaits'. They return MPX_ERR_READONLY here; change
 * them from Servo Studio, with a human watching the joint move.
 *
 * GENERATED by `python tools/gen_params.py --write` from
 * mangdang/main/robot/driver_board.{{h,c}} and the firmware's read-only list.
 */
#ifndef MPX_PARAMS_H
#define MPX_PARAMS_H

#ifdef __cplusplus
extern "C" {{
#endif

typedef enum {{
{chr(10).join(lines)}
}} mpx_param_t;

typedef struct {{
    mpx_param_t  param;
    const char  *name;      /**< What the firmware and Servo Studio call it. */
    int          read_only; /**< 1 = refused from a skill.                   */
}} mpx_param_info_t;

static const mpx_param_info_t MPX_PARAMS[] = {{
{chr(10).join(table)}
}};

#define MPX_PARAM_COUNT ((int)(sizeof(MPX_PARAMS) / sizeof(MPX_PARAMS[0])))

/** The firmware's name for a parameter, or "". */
static inline const char *mpx_param_name(mpx_param_t p)
{{
    for (int i = 0; i < MPX_PARAM_COUNT; ++i)
        if (MPX_PARAMS[i].param == p) return MPX_PARAMS[i].name;
    return "";
}}

/** 1 if a skill may not write this one. Checking beats discovering. */
static inline int mpx_param_read_only(mpx_param_t p)
{{
    for (int i = 0; i < MPX_PARAM_COUNT; ++i)
        if (MPX_PARAMS[i].param == p) return MPX_PARAMS[i].read_only;
    return 0;
}}

#ifdef __cplusplus
}}
#endif

#endif /* MPX_PARAMS_H */
'''


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    rows, ro = parse()
    text = render(rows, ro)
    have = OUT.read_text(encoding="utf-8") if OUT.is_file() else None

    if args.check:
        if have != text:
            print(f"STALE  {OUT.relative_to(ROOT)}\n       run: python tools/gen_params.py --write")
            return 1
        print(f"  ok    {OUT.relative_to(ROOT)}  ({len(rows)} parameters)")
        return 0
    if args.write:
        OUT.write_text(text, encoding="utf-8")
        print(("  unchanged " if have == text else "  updated   ") + str(OUT.relative_to(ROOT)))
        return 0
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
