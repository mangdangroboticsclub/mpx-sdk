# Changelog

## ABI v4 — live control

Three firmware additions, and the SDK layer over them. All additive: every v3
symbol keeps its name, signature and meaning, so a v3 skill runs unchanged.
The version still moves because a v4 module will not load on v3 firmware, and
`MPX_REQUIRE_ABI()` says so instead of trapping on the first host call.

Until now a skill was a script: it ran once, alone, while the gait task stood
aside. These are the three things that were impossible in that model, and each
one was a reason to patch firmware instead.

### `on_tick` — running inside the control loop

Export `on_tick(int dt_ms)` and call `mpx_tick_every(ms)` (or `mpx_tick_hz()`)
from `on_start`. Your code then runs repeatedly after `on_start` returns.

It is paced on the skill's own thread rather than called from `gait_task()`.
That loop runs at priority 22 and is what keeps the robot standing; putting
downloaded code inside it means one slow skill can stall it. The cost is that a
tick is not phase-locked to a gait frame, which does not matter for what this
is for. Overrun three ticks in a row and the loop stops, with the reason in the
log. Ticks share the run's 60 s budget.

### Overlay — composing with the gait instead of replacing it

`mpx_overlay_at()`, `mpx_overlay_leg()`, `mpx_overlay_lean()`,
`mpx_overlay_pitch()`. A per-joint offset added in `flush()` to the outgoing
frame only, so it never accumulates and never takes ownership of anything.
Clamped to ±20° by the firmware, and cleared when a skill ends however it ends.

"The built-in walk, but leaning into the turn" used to mean writing your own
walk.

### Trace — seeing what a control loop is doing

`mpx_trace_f("roll", v)` puts named numbers in a 256-sample ring, served at
`GET /v1/trace` with the same cursor contract as `/v1/logs`. `mpx-cli trace`
draws them live; `--csv` gives you a real plot.

Names are sanitised at the write boundary, since they come from inside the
sandbox and end up inside JSON.

### Also

- `examples/06-together` — all three together: stay level while the firmware walks.
- `docs/guide/live-control.md`.
- `mpx-cli trace`.
- `tools/check.py` and `mpx-cli init` now read the ABI version instead of
  hardcoding it. The check said "expected 3" on the day the firmware moved to 4.


## v3 — the restructure

Full reasoning in [RESTRUCTURE.md](RESTRUCTURE.md). Migration is one line:
`#include "mpx_compat.h"` instead of `"mpx_host.h"`.

**Requires ABI v3 firmware.** A v3 module imports symbols v2 firmware does not
provide, so it will not instantiate. See
[docs/internals/flashing.md](docs/internals/flashing.md).

### Added

- **`mpx/motion.h`** — poses, stances, keyframes, easing, timelines. Authoring
  a movement no longer means writing a frame loop.
- **`mpx/math.h`** — `sin` `cos` `tan` `sqrt` `atan2` `acos` `asin`, seven
  easing curves, `lerp` / `clamp` / `remap`. `sqrt` is a native WASM
  instruction and exact; the transcendentals are measured against libm.
- **`mpx_drive(fwd, strafe, turn)`** — continuous −1…1 steering. The phone
  UI's own path, previously unreachable from a skill.
- **`mpx_millis()` / `mpx_sleep_until()`** — there was no time source at all.
  Absolute-deadline sleeping, so a timed loop cannot drift.
- **Per-run parameters** — `mpx_paramf()` / `mpx_parami()`,
  `mpx-cli run --param name=value`, declared in `manifest.json` for a UI.
- **`on_stop(reason)`** — an optional export, so a skill can park deliberately.
- **Opt-in control arbitration** — `mpx_take()` / `mpx_release()` / `mpx_owner()`
  and `MPX_ERR_BUSY`, so a fight between control layers is loud instead of silent.
- **`mpx_foot(leg, x, splay, z)`** — one call instead of four, so a leg can be
  a loop variable.
- `mpx_set_walk_speed()`, `mpx_set_all_servo_speed()`, `mpx_reset_offsets()`,
  `mpx_read_temperature_c()` — present in the firmware, absent from the ABI.
- **`mpx-cli gaits`** — the catalogue, searchable, with descriptions and
  whether each one holds, returns or cycles.
- **`mpx-cli doctor`** — headers, ABI, compilers, project and robot in one
  pass, with the fix for anything wrong.
- **`mpx-cli sync`** — refresh a project's generated bindings; `--check` fails
  a build when they are stale.
- **`tools/check.py`** — generated-file sync, doc link check, example structure,
  and a compile of every example with an import check against the ABI.
- **`.github/workflows/check.yml`** — runs all of it, plus scaffolds and builds
  a fresh skill in each of the three languages, plus compiles a v2 skill
  through `mpx_compat.h`.

### Changed

- **One header tree** under `sdk/include/mpx/`, one `mpx_` prefix, one angle
  convention (degrees relative to centre), one frame protocol
  (`mpx_frame_send()` / `mpx_ticker_wait()`).
- **`mpx-cli init` no longer vendors the headers.** The compiler is pointed at
  the single copy. `manifest.json` records `"abi"`, and `build` warns on
  mismatch instead of letting it trap at run time.
- **The scaffold is a real movement**, and uses the API the docs recommend.
- **Documentation split by reader** into `docs/start`, `guide`, `reference`,
  `internals`. `README.md` is one page that points at the right one.
- **Examples are a numbered curriculum**, one concept each.
- `mpx-cli/` → `cli/`, `model/` → `sim/model/`, `tools/mjsim.py` → `sim/mjsim.py`.

### Removed

Moved to `_to_delete/` so the diff is reviewable and nothing is lost.

- The 45 one-line gait wrappers. `mpx_gait_for(g, ms)` replaces all of them.
- `examples/_to_delete/` — seven projects, two of which the old `WORKFLOW.md`
  cited as *the* worked examples.
- `my_skill/` (an ABI v1 header that would trap), `easytest/`,
  `mpx-dance-sdk/` (absorbed into `mpx/motion.h`), `dance-stanford-show/`.
- Committed `build/`, `mjsim-run.html`, `MUJOCO_LOG.TXT`.
- `HOST_FUNCTIONS.md` (now generated), `WORKFLOW.md` (split between
  `docs/internals/flashing.md`, `docs/guide/simulate.md` and this file).

### Fixed

- `.devcontainer/post-create.sh` installed from `mpx-cli/` (now `cli/`) and
  told new users to build `examples/hello-wasm/src/test_skill.c`, which had not
  existed for some time. It now installs from `cli/`, exports
  `MPX_SDK_INCLUDE`, and runs `mpx-cli doctor`.
- `sim/mjsim.py` searched `model/` for `robot.xml`; the model is in `sim/model/`.

- `MPX_EASE_SINE` returned 0.9999982 at t = 1, so every keyframe would have
  landed a fraction short of the authored pose. Endpoints now snap exactly.
- The `init` scaffold printed a 13-byte string literal with length 14.
- `WORKFLOW.md` referenced `examples/walk-with-gains`, which was in
  `_to_delete/`. The link checker in `tools/check.py` makes that class of
  mistake impossible to commit.

---

## v2 — error codes

Every host function returns `int32_t`. Seventeen of them previously computed an
error code that the WAMR signature discarded, so a misspelled gait name, an
out-of-range servo id and a successful call were indistinguishable from inside
a skill.

Added `mpx_abi_version()`, `robot_read_angle_cdeg()` (a read in the *same*
frame as the write, so a closed loop converges instead of diverging), the
`servo_*` bus family, and made three calibration parameters read-only from a
skill.

## v1

Original.
