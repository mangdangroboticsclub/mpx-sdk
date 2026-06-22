"""mpx-cli init — scaffold a new skill development project."""

from __future__ import annotations

import argparse
from pathlib import Path
from mpx_cli.sdk.toolchain import detect_all

# ── Template sources (embedded as Python strings) ───────────────

_skill_c = """\
/* {name}.c — MPX-Dog WASM Skill
 *
 * Compile:
 *   mpx-cli build {name}.c
 *
 * Upload & run:
 *   mpx-cli upload {name}.wasm
 *   mpx-cli run {name}.wasm
 */

#include <string.h>
#include "mpx_host.h"

/* Entry point called by the sandbox */
void on_start(void)
{{
    const char *msg = "Hello from {name}!\\n";
    print((int)msg, (int)strlen(msg));

    /* Ping servo 1 to verify the bus is alive */
    int model = robot_ping_servo(1);
    if (model > 0) {{
        print((int)"Servo bus OK\\n", 14);
    }}

    /* Set gait parameters: 100ms period, 70mm height, 10mm lift,
     * 10mm stride, 10° tilt */
    robot_set_config(100, 70, 10, 10, 10);

    /* Walk forward for 2 seconds, then stop */
    robot_gait((int)"advance");
    robot_delay_ms(2000);
    robot_gait((int)"none");

    print((int)"Done\\n", 5);
}}
"""

_skill_wat = """\
;; {name}.wat — MPX-Dog WASM Skill
;;
;; Compile:
;;   mpx-cli build {name}.wat
;;
;; Upload & run:
;;   mpx-cli upload {name}.wasm
;;   mpx-cli run {name}.wasm
;;
;; Imports below match the host functions registered in the
;; ESP32 firmware under the "env" module.

(module
    ;; Import host functions from the "env" module
    (import "env" "print" (func $print (param i32 i32)))
    (import "env" "robot_gait" (func $robot_gait (param i32)))
    (import "env" "robot_delay_ms" (func $robot_delay_ms (param i32)))

    ;; Export linear memory (1 page = 64 KB)
    (memory (export "memory") 1)

    ;; Strings at fixed offsets
    (data (i32.const 0) "Hello from {name}!")
    (data (i32.const 64) "advance")
    (data (i32.const 128) "none")

    ;; Entry point — called by the sandbox as "on_start"
    (func (export "on_start")
        ;; Print greeting
        i32.const 0
        i32.const 18
        call $print

        ;; Start advancing gait
        i32.const 64
        call $robot_gait

        ;; Walk for 2 seconds
        i32.const 2000
        call $robot_delay_ms

        ;; Stop
        i32.const 128
        call $robot_gait
    )
)
"""

_skill_ts = """\
// {name}.ts — MPX-Dog WASM Skill (AssemblyScript)
//
// Compile:
//   mpx-cli build {name}.ts
//
// Upload & run:
//   mpx-cli upload {name}.wasm
//   mpx-cli run {name}.wasm

import {{
    print, robot_gait, robot_delay_ms,
    robot_set_config, robot_ping_servo,
}} from "../include/mpx_env";

export function on_start(): void {{
    const msg = "Hello from {name}!\\n";
    const encoded = String.UTF8.encode(msg);
    print(changetype<usize>(encoded), encoded.byteLength as i32);

    const model = robot_ping_servo(1);
    if (model > 0) {{
        const ok = String.UTF8.encode("Servo bus OK\\n");
        print(changetype<usize>(ok), ok.byteLength as i32);
    }}

    robot_set_config(100, 70, 10, 10, 10);

    const advance = String.UTF8.encode("advance");
    robot_gait(changetype<usize>(advance));
    robot_delay_ms(2000);

    const stop = String.UTF8.encode("none");
    robot_gait(changetype<usize>(stop));
}}
"""

_readme_template = """\
# {name} — MPX-Dog WASM Skill

## Prerequisites

- **mpx-cli** — install with `pip install -e tools/`
- **WASI SDK** (for C) — `/opt/wasi-sdk/bin/clang`
- **WABT** (for WAT) — `/opt/wabt/bin/wat2wasm`
- **AssemblyScript** (for TS) — `npm install -g assemblyscript`

## Quick Start

```bash
# Build
mpx-cli build src/{name}.{ext}

# Validate
mpx-cli build src/{name}.{ext} --validate

# Upload to robot (connected via WiFi)
mpx-cli upload src/{name}.wasm

# Run on robot
mpx-cli run {name}.wasm
```

## Host Functions

All host functions are registered under the `"env"` module. For C skills,
copy `mpx_host.h` from the mpx_cli SDK into your project:

```bash
cp <mpx_cli_path>/sdk/mpx_host.h include/
```

Then `#include "mpx_host.h"` in your source.

See `docs/WASM_SANDBOX.md` in the MPX-Dog firmware repository for the
full reference.

## Safety

- Linear memory: 128 KB max (PSRAM)
- Execution timeout: 60 seconds
- No direct hardware access — use host functions only
"""


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

    # Write README
    _write(out_dir / "README.md", _readme_template.format(name=name, ext=ext))

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


# ── Embedded mpx_host.h content ──────────────────────────────────

MPX_HOST_H_CONTENT = """\
/* mpx_host.h — MPX-Dog WASM Skill Host Function Reference
 *
 * All functions are registered under the "env" module by the
 * ESP32 firmware. Include this header in your C/C++ skills.
 */

#ifndef MPX_HOST_H
#define MPX_HOST_H

#ifdef __cplusplus
extern "C" {
#endif

/* ── SDK / Logging ───────────────────────────────────────────── */
extern void print(int ptr, int len);
static inline void MPX_print(const char *str, int len) { print((int)str, len); }
#define MPX_LOG(msg)  MPX_print((msg), (int)(sizeof(msg) - 1))

/* ── High-Level Gait Control ─────────────────────────────────── */
extern void robot_gait(int name_ptr);
extern int  robot_get_mode(void);

/* ── Configuration ───────────────────────────────────────────── */
extern void robot_set_config(int period, int height,
                             int up_height, int stride, int tilt);
extern int  robot_get_period(void);
extern int  robot_get_height(void);
extern int  robot_get_up_height(void);
extern int  robot_get_stride(void);
extern int  robot_get_tilt(void);

/* ── Low-Level Servo Control ─────────────────────────────────── */
extern void robot_set_servo_angle(int id, int centideg);
extern void robot_flush(void);
extern void robot_set_servo_speed(int id, int speed);
extern int  robot_read_position(int id);

/* ── Calibration ─────────────────────────────────────────────── */
extern void robot_set_offset(int id, int centideg);
extern int  robot_get_offset(int id);
extern int  robot_ping_servo(int id);

/* ── Utility ─────────────────────────────────────────────────── */
extern void robot_delay_ms(int ms);

#ifdef __cplusplus
}
#endif

#endif /* MPX_HOST_H */
"""

# ── Embedded mpx_env.ts content ─────────────────────────────────

MPX_ENV_TS_CONTENT = """\
/**
 * mpx_env.ts — MPX-Dog WASM Host Function Declarations (AssemblyScript)
 *
 * Import host functions into your skill:
 *
 *   import {
 *     print, robot_gait, robot_delay_ms,
 *     robot_set_config, robot_ping_servo,
 *   } from "../include/mpx_env";
 */

@external("env", "print")
export declare function print(ptr: usize, len: i32): void;
@external("env", "robot_gait")
export declare function robot_gait(name_ptr: usize): void;
@external("env", "robot_get_mode")
export declare function robot_get_mode(): i32;
@external("env", "robot_set_config")
export declare function robot_set_config(
    period: i32, height: i32,
    up_height: i32, stride: i32, tilt: i32,
): void;
@external("env", "robot_get_period")
export declare function robot_get_period(): i32;
@external("env", "robot_get_height")
export declare function robot_get_height(): i32;
@external("env", "robot_get_up_height")
export declare function robot_get_up_height(): i32;
@external("env", "robot_get_stride")
export declare function robot_get_stride(): i32;
@external("env", "robot_get_tilt")
export declare function robot_get_tilt(): i32;
@external("env", "robot_set_servo_angle")
export declare function robot_set_servo_angle(id: i32, centideg: i32): void;
@external("env", "robot_flush")
export declare function robot_flush(): void;
@external("env", "robot_set_servo_speed")
export declare function robot_set_servo_speed(id: i32, speed: i32): void;
@external("env", "robot_read_position")
export declare function robot_read_position(id: i32): i32;
@external("env", "robot_set_offset")
export declare function robot_set_offset(id: i32, centideg: i32): void;
@external("env", "robot_get_offset")
export declare function robot_get_offset(id: i32): i32;
@external("env", "robot_ping_servo")
export declare function robot_ping_servo(id: i32): i32;
@external("env", "robot_delay_ms")
export declare function robot_delay_ms(ms: i32): void;
"""
