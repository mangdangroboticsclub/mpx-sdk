# What changed, and why

A record of the v2 → v3 restructure: what moved, what it replaced, and the
reasoning. If you only want to get your existing skills building again, jump to
[Migration](#migration).

---

## The problem

The old documentation was unusually good. The API underneath it was not.

The clearest symptom was the README's section 5, *"Things that will bite you"* —
eight paragraphs of careful warnings. Every one of them described a mistake the
API permitted and could instead have made impossible:

| The warning | What it was really saying |
|---|---|
| "Nothing moves until `robot_flush()`" | the send is easy to forget |
| "Angles are centidegrees relative to centre" | there were four ways to express one joint angle |
| "There are two angle frames and they run opposite ways" | a closed loop on the wrong pair *diverges* |
| "There is no libm — write your own `atan`, and not the Taylor one" | numerical analysis was a prerequisite for a leg |
| "`robot_delay_ms()` is the only way to wait" | there was no clock at all |
| "Leave the robot somewhere safe" | there was no way to clean up |

The fix for that list is not more documentation. It is to move the warnings
into the function names and the type system, and then let the docs get shorter.

Three further problems were structural rather than stylistic:

**Composition was undefined.** `examples/four-ways` demonstrated the four
control layers one after another. A real movement needs them at the same time,
and nothing anywhere answered "if a gait is running and I place a foot, who
wins?" The firmware had an answer — a shared goal buffer, last writer per 15 ms
tick — but it was not part of the API's contract.

**The SDK did not expose everything the board could do.** `robot::joy_input()`
— the continuous velocity path the phone UI's thumbsticks use — was not in the
ABI. "Walk forward slowly while turning gently" was trivial from the phone and
impossible from a skill.

**Headers were copied per project.** `mpx-cli init` vendored `mpx_host.h` into
every new skill, freezing an ABI snapshot. The repository contained four copies;
two had diverged, and `my_skill/include/mpx_host.h` still described ABI v1 and
would have loaded and then trapped on its first host call. That is not a
discipline failure. A snapshot of a moving target goes stale by default.

---

## What was done

### 1. One API, three invariants

The 1324-line `mpx_host.h` became a layered tree under `sdk/include/mpx/`.
Everything is `static inline` over the raw imports, so the layering costs
nothing: the hello example is 1.7 KB and uses `mpx.h`.

```
mpx/sys.h      log, time, parameters, errors, lifecycle, the ticker
mpx/math.h     sin cos sqrt atan2 acos, easing curves
mpx/motion.h   poses, stances, keyframes, timelines      ← author here
mpx/robot.h    gaits, driving, body attitude, arbitration
mpx/gaits.h    the catalogue (generated)
mpx/leg.h      feet, joints, frames, two-link IK
mpx/bus.h      lock, gains, torque, stage/commit
mpx/abi.h      the raw host imports (generated)
```

Three rules run through all of it:

**One prefix.** Everything is `mpx_`. Previously there were four — `print`,
`MPX_*`, `robot_*`, `servo_*` — with no rule for which was which.

**One angle representation.** Float degrees, relative to centre, everywhere in
`sys`/`robot`/`leg`/`motion`. Chosen because the robot is calibrated so that
all twelve joints centred *is* the standing pose, which makes `0` mean
something. The absolute frame survives only in `mpx/bus.h`, where every
function says `_abs_` in its name, plus `MPX_ABS_FROM_REL()` /
`MPX_REL_FROM_ABS()` to convert. The two frames can no longer be mixed silently.

**One frame protocol.** `mpx_frame_send()` replaces both `robot_flush()` and
`servo_commit()` at their respective layers, and in a timed loop
`mpx_ticker_wait()` sends for you — so the most-forgotten call disappears from
correctly-written code entirely.

### 2. Forty-five wrappers deleted

`robot_look_upper_left(ms)`, `robot_backleg_lift_right(ms)`, `robot_move_lb(ms)`
and forty-two siblings were each `gait(X); delay(ms); gait(NONE);`. They tripled
the header's length, buried the real API, and hard-coded a policy — always
return to `NONE` — that is wrong the moment you chain two moves.

They are now two functions and a data table:

```c
mpx_gait(g);                 mpx_gait_for(g, ms);      mpx_gait_once(g);
```

`mpx/gaits.h` carries, per gait, a description, whether it **holds / returns /
cycles**, and a duration that suits it. That answers the question the wrappers
never did: *what does `buttshrugR` actually look like, and will it still be
doing it when my skill exits?*

```bash
mpx-cli gaits            # all 46
mpx-cli gaits wiggle     # search
```

### 3. A maths library

`mpx/math.h` replaces the copy-pasted `f_sqrt` / `f_atan2` in every example.

Two things make it better than what it replaces:

- **WebAssembly has native instructions** for `sqrt`, `abs`, `floor`, `ceil`,
  `trunc`, `min`, `max` and `copysign`. `mpx_sqrt()` is one instruction and
  **exact** — not an approximation at all.
- **The transcendentals are measured, not estimated.** Verified against the C
  library over the full argument range:

  | | measured worst-case error |
  |---|---|
  | `mpx_sin`, `mpx_cos` | 3.7 × 10⁻⁶ |
  | `mpx_atan`, `mpx_atan2`, `mpx_acos`, `mpx_asin` | 1.2 × 10⁻⁵ rad = **0.0007°** |
  | `mpx_sqrt` | 0 (exact) |

  A servo step is about 0.264°, so the angular error is roughly 380× finer than
  the hardware can express. The old README's warning about the Taylor series
  being off by 3.5° is now moot: `mpx_atan` is minimax.

Plus seven easing curves. Building this found a real bug while it was being
written: `MPX_EASE_SINE` is built on `mpx_cos` and inherited its 3.7 × 10⁻⁶, so
it returned 0.9999982 at t = 1 — and a timeline reads `ease(1)` as *you have
arrived*, so every keyframe would have landed a fraction short of the pose that
was authored. The endpoints now snap exactly.

### 4. A motion layer

`mpx/motion.h` is the answer to "how do I make a new movement". You describe
key moments; it interpolates, sends at a steady frame rate, honours
cancellation, and lands exactly on the final key.

```c
mpx_stance_key_t bow[] = {
    {    0, mpx_stance_stand(),              MPX_EASE_LINEAR },
    {  450, mpx_stance_crouch(20.0f),        MPX_EASE_IN     },
    { 1100, mpx_stance_front(22.0f, -52.0f), MPX_EASE_OUT    },
    { 2600, mpx_stance_stand(),              MPX_EASE_BACK   },
};
mpx_stance_play(bow, 4, mpx_play(50, repeats));
```

Two keyframe types, because the distinction matters: interpolating **feet**
gives straight-line foot paths (right for anything touching the floor);
interpolating **joints** gives arcs at the foot (right for a wave).

This is where the orphaned `mpx-dance-sdk/` belongs. That folder had exactly the
right idea — a codegen, a JSON choreography format with beat slots, `moves.h`,
`timetable.h` — but it was unreferenced by the README, built by its own
Makefile, and shipped a 63-line stub `mpx_host.h`. Its concepts are now first
class; the folder is retired.

### 5. Four capabilities the board had and the ABI did not

| Added | Wraps | Why it mattered |
|---|---|---|
| `mpx_drive(f, s, t)` | `robot::joy_input` | continuous −1…1 steering — the phone UI's own path. Gaits are a switch; this is a stick. |
| `mpx_millis()`, `mpx_sleep_until()` | new | there was **no time source at all**. You could not measure a frame, hold a rate, or run for a wall-clock duration. |
| `mpx_set_walk_speed()`, `mpx_set_all_servo_speed()`, `mpx_reset_offsets()`, `mpx_read_temperature_c()` | existing `robot::` functions | present in the firmware, absent from the ABI |
| `mpx_param_f/i()`, the `on_stop` export | new | a skill took no arguments and had no cleanup hook |

`mpx_sleep_until()` takes an absolute deadline rather than a duration, which is
what stops per-frame overhead accumulating: 600 frames of `delay(16)` run long
by 600 frames' worth of host calls; 600 frames of `sleep_until(start + n × 16)`
cannot drift.

### 6. Arbitration, opt-in

```c
mpx_take(MPX_OWN_FEET);      /* I am placing feet; nothing else may */
...
mpx_release();
```

While a domain is claimed, a call belonging to a different one returns
`MPX_ERR_BUSY` instead of quietly interleaving at 66 Hz.

**It is opt-in and that is deliberate.** Until a skill calls `mpx_take()`, the
owner is `MPX_OWN_NONE` and every write path behaves exactly as it did in v2 —
so no existing skill changes meaning. In the firmware this is one
`control_allows()` guard on each of the seven write paths, and each is a no-op
until something claims a domain.

`docs/guide/how-motion-works.md` is the page that documents all of this: the
chain from a host call to a motor, the four writers, the 15 ms tick, both angle
frames, and a decision tree for which layer to use. It is the page that did not
exist before.

### 7. `on_start` / `on_stop`, and per-run parameters

```c
MPX_EXPORT void on_start(void);
MPX_EXPORT void on_stop(int reason);      /* optional */
```

`on_stop` runs when the skill ends so you can park deliberately. It honestly
does **not** run after the 60-second watchdog, because by then the module has
been torn down; on that path the firmware halts the gait instead — that stops
motion without guessing at a pose, and the docs say so rather than implying a
guarantee that does not exist.

Parameters make one skill cover many variations:

```c
const float tempo = mpx_paramf("tempo", 1.0f);
```

```bash
mpx-cli run --param tempo=1.6 --param repeats=3
```

The second argument is the fallback, so a run supplying nothing behaves exactly
as written. Declare them in `manifest.json` and the robot's web UI renders a
control for each.

### 8. One copy of the headers

`mpx-cli init` no longer vendors anything. `sdk/toolchain.py:sdk_include_dir()`
finds the one `sdk/include/`, honouring `$MPX_SDK_INCLUDE`, and passes `-I`.
`manifest.json` records `"abi": 3`, and `mpx-cli build` warns when that
disagrees with the SDK — before upload, rather than as a trap at run time.

AssemblyScript resolves imports by path, so it still gets one copied file — but
it is generated and stamped, so drift is detectable rather than invisible.

### 8b. One command that answers "is my setup right"

The biggest integration cost was never any single missing piece — it was that
each question needed a different command and some idea of how the pieces fit.

```bash
mpx-cli doctor
```

Checks, in one pass: where the SDK headers resolved from and how, which ABI
they describe, which compilers exist, whether the project you are standing in
agrees with the SDK, and whether the robot answers. Anything wrong prints the
command that fixes it.

`mpx-cli sync` is its companion: C projects copy nothing and it says so;
AssemblyScript and WAT projects keep one generated file each, stamped with its
ABI, so `sync` refreshes it and `sync --check` fails a build when it is stale.

### 9. Generators, so the docs cannot rot

```
mangdang/main/sdk/wasm_host_functions.h      ← the NativeSymbol table
        │  tools/gen_abi.py
        ├─▶ abi/host_functions.json
        ├─▶ sdk/assemblyscript/mpx_env.ts
        ├─▶ sdk/wat/host-functions.md
        ├─▶ docs/reference/host-functions.md
        ├─▶ docs/reference/errors.md
        └─▶ sdk/include/mpx/abi.h            (checked, not overwritten)

sdk/include/mpx/gaits.h  ─┐ tools/gen_docs.py
mpx_cli's argparse       ─┴─▶ docs/guide/gaits.md, docs/reference/cli.md
```

`--check` on both, in CI. The previous docs referenced
`examples/walk-with-gains` as *the* worked example while that example sat in a
folder literally named `_to_delete/`. Generated pages cannot do that.

### 10. Documentation split by reader

The three root files each tried to serve three audiences. `WORKFLOW.md` in
particular was written in release-note voice — *"It now tells you the truth"*,
*"One open item: needs your gateway to confirm"* — which is a changelog, not a
guide.

```
docs/start/       a maker's first hour, in order
docs/guide/       building something specific
docs/reference/   lookup, mostly generated
docs/internals/   changing the SDK or the firmware
docs/troubleshooting.md
```

`README.md` is now one page whose job is to point at the right one of those.

### 11. The examples are a curriculum

Eight numbered examples, each one concept, each under 100 lines, each with a
README saying what to notice. `05-timeline` is the flagship. `08-imu-balance`
is new: a closed loop on the robot's own senses, which is the thing a
pre-baked animation can never do and the reason to write C rather than author
in a browser.

The scaffold `mpx-cli init` writes is now one of them in spirit rather than the
worst code in the repository — the old template used `print()` and
`robot_gait((int)"advance")`, precisely the two things the README told you not
to do, told you to run a three-command loop `deploy` had replaced, and passed
`14` as the length of a 13-byte string literal.

### 12. Deleted

Moved to `_to_delete/` rather than removed, so you can review the diff and
recover anything: `examples/_to_delete/` (seven projects, two of them cited by
`WORKFLOW.md` as *the* worked examples), the committed `build/`,
`mjsim-run.html` (102 KB of generated artefact), `MUJOCO_LOG.TXT`, `easytest/`
(a scratch copy of the template), `my_skill/` (the ABI v1 header),
`mpx-dance-sdk/`, `dance-stanford-show/`, the old flat examples, and
`HOST_FUNCTIONS.md` / `WORKFLOW.md`.

`model/` moved to `sim/model/`, `tools/mjsim.py` to `sim/mjsim.py`, `mpx-cli/`
to `cli/`. `sim/mjsim.py`'s model search and `.devcontainer/post-create.sh`
were updated to match — both still pointed at the old layout, and the
post-create script was also telling new users to build
`examples/hello-wasm/src/test_skill.c`, which had not existed for some time.

`_to_delete/README.md` lists everything in there and why, so deleting it is a
decision you can make from the folder itself.

---

## What was kept, deliberately

- **`abi/host_functions.json` + a generator.** The right design, already there.
  Verified in sync across C, AssemblyScript and WAT before any of this started.
  Everything above builds on it.
- **`sdk/project.py`** — manifest-derived paths so `deploy` needs no arguments.
  Its docstring explains *why*, which is the standard the rest now meets.
- **ABI v2's decisions**: return codes on every host function, `mpx_strerror`,
  `mpx_abi_version()`, the bus lock, and making calibration parameters
  read-only from a skill. All correct.
- **The README's symptom→cause table**, expanded into
  `docs/troubleshooting.md`.
- **`examples/four-ways`'s teaching instinct**, spread across the numbered
  curriculum and `how-motion-works.md`.

---

## Migration

### The one-line version

```diff
-#include "mpx_host.h"
+#include "mpx_compat.h"
```

`mpx_compat.h` forwards every v2 name to its v3 equivalent at zero cost. It
will be removed after one release.

### Names

| v2 | v3 |
|---|---|
| `MPX_LOG(s)` | unchanged |
| `MPX_print(s, n)` | `mpx_log_n(s, n)` |
| `MPX_print_int(v)` | `mpx_log_i("label", v)` |
| `robot_gait_enum(GAIT_ADVANCE)` | `mpx_gait(MPX_GAIT_FORWARD)` |
| `robot_walk_forward(ms)` | `mpx_gait_for(MPX_GAIT_FORWARD, ms)` |
| `robot_look_upper_left(ms)` *(and 44 more)* | `mpx_gait_for(MPX_GAIT_LOOK_UP_LEFT, ms)` |
| `robot_stand()` | `mpx_stand()` |
| `robot_set_servo_angle(id, cdeg)` | `mpx_joint_to(joint, deg)` — **degrees, not centidegrees** |
| `robot_set_servo_deg(id, deg)` | `mpx_joint_to(joint, deg)` |
| `robot_read_angle_cdeg(id)` | `mpx_joint_at(joint)` — degrees |
| `robot_read_position(id)` | `mpx_joint_raw(joint)` — still absolute, still diagnostics only |
| `robot_flush()` | `mpx_frame_send()`, or let `mpx_ticker_wait()` do it |
| `robot_delay_ms(ms)` | `mpx_sleep(ms)`; prefer `mpx_sleep_to()` in a loop |
| `robot_ik_fr(x, t, z)` | `mpx_foot_to(MPX_FR, x, t, z)` |
| `robot_set_body_pose(r, p, y)` | `mpx_body(r, p, y)` |
| `robot_set_attitude_speed(d)` | `mpx_body_speed(d)` |
| `robot_set_config(a,b,c,d,e)` | `mpx_gait_config_set(cfg)` |
| `servo_lock()` / `servo_unlock()` | `mpx_bus_take()` / `mpx_bus_release()` |
| `servo_set_gain(id, p, v)` | `mpx_gain_set(joint, p, v)` |
| `servo_stage(id, abs_deg, …)` | `mpx_bus_stage(joint, **rel_deg**, …)` or `mpx_bus_stage_abs()` |
| `servo_commit()` | `mpx_bus_send()` |
| `SERVO_FR_KNEE` | `MPX_FR_KNEE` |
| `GAIT_ADVANCE` | `MPX_GAIT_FORWARD` |
| `MPX_OK`, `MPX_ERR_*` | unchanged, plus `MPX_ERR_BUSY` (−7) |

**The one to be careful with:** `mpx_joint_to()` takes **degrees**, where
`robot_set_servo_angle()` took centidegrees. A mechanical find-and-replace
gives you angles 100× too small. `mpx_compat.h` keeps the old function with the
old units, so port that call site deliberately.

### Firmware

You must flash ABI v3. A v3 module imports symbols v2 firmware does not
provide, so it will not instantiate. See
[docs/internals/flashing.md](docs/internals/flashing.md) for the build and the
post-flash checklist.

### Checklist for an existing skill

1. `#include "mpx.h"`, or `"mpx_compat.h"` to defer the work
2. Add `MPX_REQUIRE_ABI();` as the first line of `on_start()`
3. Add `MPX_EXPORT` to `on_start` (and add `on_stop` while you are there)
4. Change centidegree call sites to degrees
5. Set `"abi": 3` in `manifest.json`
6. `mpx-cli deploy`

---

## Verification

Everything in this restructure was compiled and, where it could be, measured.

| | |
|---|---|
| All 8 examples + the scaffold + a legacy-through-shim skill | compile clean at `-Wall -Wextra -Wconversion` for `wasm32` |
| Every import in every module | resolves against the generated `abi/host_functions.json` |
| Each of the 10 headers | compiles standalone, and as C++ |
| `mpx/math.h` | checked against the C library over the full argument range |
| `tools/gen_abi.py --check`, `tools/gen_docs.py --check` | in sync |
| The WAT scaffold | parses, validates, assembles; its imports resolve |
| `mpx-cli doctor` / `sync` / `gaits` / `init --lang c\|ts\|wat` / `--param` | run |
| `.github/workflows/check.yml` | runs all of the above on every push |

**What has not been verified: the firmware does not compile here.** These
changes were made without an ESP-IDF toolchain or hardware, so
`main/sdk/wasm_host_functions.{h,cc}`, `main/wasm/wasm_sandbox.{h,cc}` and the
`POST /v1/skills/run` handler need `idf.py build` and the checklist in
[docs/internals/flashing.md](docs/internals/flashing.md) before you trust any
of it on a real robot.
