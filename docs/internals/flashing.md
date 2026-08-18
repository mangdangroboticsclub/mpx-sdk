# Building and flashing the firmware

The SDK in this repo describes **ABI v4**. A robot on older firmware will load
a v4 module and then fail to instantiate it, because the module imports symbols
that firmware does not provide — which shows up as a trap on the first host
call unless the skill starts with `MPX_REQUIRE_ABI()`.

Check what a robot is running before anything else:

```bash
mpx-cli doctor
```

```
  ok    ABI  v4, 70 host functions
```

---

## Flashing

The firmware lives in the `mangdang` repository, beside this one.

```bash
cd ../mangdang
idf.py build
idf.py -p COM<n> flash monitor
```

> **If you do not have the firmware source**, you cannot use the commands
> above. Use the prebuilt image for your SDK version instead — see the release
> notes for this SDK for where to get it and how to apply it. The ABI version
> is in the release title; it must match the one `mpx-cli doctor` prints.

---

## What to check after flashing

| Check | Expect |
|---|---|
| `mpx-cli doctor` | `ABI v4, 70 host functions`, robot reachable |
| `mpx-cli deploy examples/01-gaits` | walks, turns, stands — the drive section curves rather than turning in steps |
| `mpx-cli deploy examples/02-feet` | the body moves while the feet stay planted |
| `mpx-cli deploy examples/05-sensing` | joint feedback and IMU values in `mpx-cli logs` |
| `mpx-cli deploy examples/06-together` | the full routine, then it **stays running** as a behaviour |
| `mpx-cli trace` (while 06 runs) | live `roll` and `trim` values |
| `mpx-cli movements` | `greet` appears alongside the built-in movements |
| `mpx-cli stop` | the behaviour ends and the robot stands |
| `GET /v1/robot/status` | the same twelve calibration offsets as before |
| Servo Studio degree readout | unchanged |
| A skill calling `mpx_bus_stage()` without `mpx_bus_take()` | returns `-2` |
| `mpx_gain_set(1, MPX_PARAM_RANGE_POSITION_DEG, 300)` | returns `-4`, read-only |
| A skill that claims `MPX_OWN_FEET` then calls `mpx_gait()` | returns `-7` |
| A skill with no `mpx_take()` call at all | behaves exactly as it did on v2 |

The gait command path is unchanged, so **NVS calibration stays valid and
nothing needs recalibrating.**

---

## What v3 changed in the firmware

v3 added the capabilities the board always had but a skill could not reach,
plus the arbitration that makes the control layers composable.

| File | Change |
|---|---|
| `sdk/wasm_host_functions.h` | `MPX_ABI_VERSION` → 3; `MPX_ERR_BUSY`; 15 new symbols; the control-domain enum |
| `sdk/wasm_host_functions.cc` | the 15 implementations; one `control_allows()` guard added to each of the seven existing write paths |
| `wasm/wasm_sandbox.h` / `.cc` | per-run clock, parameter table, the optional `on_stop` call, gait halt on watchdog kill |
| `network/http_server.cc` | `POST /v1/skills/run` accepts an optional `params` string |

## What v4 changed

v4 is **additive**: every v3 symbol keeps its name, signature and meaning, so a
v3 module runs unchanged. The version still moves because a v4 module will not
run on v3 firmware, and discovering that as a trap on the first host call is
exactly what the version check exists to prevent.

What it adds is *shape* — the three things that turn a skill from a script that
plays once into something that behaves:

| File | Change |
|---|---|
| `sdk/wasm_host_functions.h` / `.cc` | `MPX_ABI_VERSION` → 4; six new symbols: `mpx_overlay`, `mpx_overlay_get`, `mpx_overlay_clear`, `mpx_tick_every`, `mpx_tick_stop`, `mpx_trace` |
| `robot/robot.cc` | the overlay array, applied in `flush()` and cleared when a skill ends |
| `wasm/wasm_sandbox.cc` | the tick loop, its budget, and the three-overrun eviction |
| `util/trace_ring.h` / `.cc` | the 256-sample named-value ring behind `mpx_trace` |
| `skills/registry.*` | the `mpx` custom section: `provides_gait`, `behaviour`, `on`, `autorun` travel inside the `.wasm` |
| `skills/runner.*` | one skill at a time, `OneShot` vs `Behaviour`, and a truthful answer about what is running |
| `skills/movement.*` | one namespace for movements — built-in gaits and skill-provided ones in one list |
| `skills/events.*` | `boot`, `imu.lifted`, `imu.fallen`, `imu.shaken`, `chat:<word>`, with per-event cooldowns |
| `skills/autorun.*` | the boot slot, behind an NVS-counted safe mode |
| `network/http_server.cc` | `/v1/trace`, `/v1/skills/{registry,status,stop,safe-mode/clear}` |

Nothing was removed and no existing behaviour changed for a skill that does not
call the new functions. The arbitration guards are still no-ops until something
calls `mpx_control_take()`.

---

## If a skill traps immediately after flashing

It was built against the old ABI. `mpx-cli deploy` again. Adding
`MPX_REQUIRE_ABI()` to the top of `on_start()` turns that into one clear log
line instead of an unexplained trap.

---

## If you change the firmware

Any change to the host-function table or to `robot/robot.h` must be followed by
regenerating this repo's ABI and coverage files **in the same change**:

```bash
python tools/gen_abi.py --emit-c
python tools/gen_coverage.py
python tools/check.py          # what CI runs
```

Otherwise the SDK describes a firmware that no longer exists, which is the one
failure this repo is built to make impossible. See
[abi.md](abi.md) for how a host function gets added.
