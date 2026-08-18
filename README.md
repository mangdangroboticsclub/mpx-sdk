# MPX SDK

**Write movements and behaviours for the MPX-Dog / Mini Pupper quadruped and
push them to the robot over Wi-Fi in one command.**

```c
#include "mpx.h"

MPX_EXPORT void on_start(void)
{
    MPX_REQUIRE_ABI();

    mpx_gait(MPX_GAIT_FORWARD);   /* the firmware keeps walking... */
    mpx_tick_hz(25.0f);           /* ...while your code runs 25 times a second */
}

MPX_EXPORT void on_tick(int dt_ms)
{
    float roll, pitch;
    mpx_imu_tilt(&roll, &pitch);

    mpx_overlay_lean(-roll * 0.45f);   /* trim the walk, don't replace it */
    mpx_trace_f("roll", roll);         /* and watch it happen: mpx-cli trace */
}
```

```bash
mpx-cli deploy
```

Builds it, uploads it, runs it, and tells you what happened.

That skill walks and keeps itself level on a slope. It is twelve lines, it runs
in a sandbox, and it needed no firmware.

---

## Who this is for

**If you own an MPX-Dog** and want it to do something new, you do not need this
repository. Open the robot's web UI, browse the marketplace, install a skill.
The rest of this page is about *making* those skills.

**If you want to make one**, this SDK is the supported way. You write one C
file; the robot runs it in a sandbox. You never touch firmware, never reflash
to change a movement, and cannot brick anything from inside a skill.

---

## Get moving

```bash
pip install -e cli          # or open this folder in VS Code -> Reopen in Container
mpx-cli doctor              # what is missing, and what to type about it
mpx-cli init my_move && cd my_move
mpx-cli deploy
mpx-cli logs -f
```

`doctor` is worth running first every time something is odd. It checks the
headers, the ABI, your compilers, the project you are standing in, and whether
the robot answers — the five things that account for nearly every first-hour
problem.

Everything above works with no account and no internet. The robot is on your
Wi-Fi, `mpx-cli` talks to it directly, and nothing leaves the room. Only
`publish` and `install` touch a server, and only if you ask them to.

Then read these four, in order:

| | |
|---|---|
| **[docs/SETUP.md](docs/SETUP.md)** | install, find the robot, make it move — ten minutes |
| **[docs/MOVEMENT.md](docs/MOVEMENT.md)** | everything about making it move and behave; the first part needs no code |
| **[docs/WORKFLOW.md](docs/WORKFLOW.md)** | the daily loop — deploy, trace, tune, simulate, publish |
| **[docs/REFERENCE.md](docs/REFERENCE.md)** | every function, error, command and manifest field. Generated |

---

## How it works

A *skill* is a WebAssembly module. You export `on_start`; the robot calls it.
Export `on_tick` as well and you keep running.

```
  your .c file
       │  mpx-cli build      clang, targeting wasm32
       ▼
  a .wasm module (a few KB)
       │  mpx-cli deploy     HTTP, over Wi-Fi
       ▼
  the robot's flash
       │  the sandbox        WAMR, 128 KB of memory, its own watchdog
       ▼
  on_start()   ──calls──►  70 host functions  ──►  gait generator
  on_tick()                                   ──►  inverse kinematics
       │                                       ──►  the servo bus
       │                                       ──►  12 servos
       └──────────►  overlay, applied on top of whatever is driving them
       └──────────►  trace, out to `mpx-cli trace`
```

The sandbox is the point. Your skill cannot reach memory it does not own,
cannot crash the firmware, and cannot outlive its budget. When it ends —
normally, cancelled, or timed out — the firmware takes the servo bus back,
clears your overlay and stops your ticks whether you released them or not.
**That is what makes it reasonable to hand a stranger's code to a robot with
12 motors in it.**

Everything else follows from that boundary. Host functions are the only way
across it, which is why the ABI is versioned, generated, and checked.

### The four ways to move

Layered. Use the highest one that does what you need; each step down gives more
control and takes more responsibility.

| | Header | You provide | The robot provides |
|---|---|---|---|
| **Gaits and driving** | `mpx/robot.h` | a name, or a velocity | the entire walk |
| **Feet** | `mpx/leg.h` | foot positions | the joint angles |
| **Joints** | `mpx/leg.h` | joint angles | the bus transaction |
| **Motors** | `mpx/bus.h` | angles *and* Kp/Kd | nothing |

They are not four separate worlds. Whichever you use, one call sends the frame
and one rule decides who owns the joints — [how motion
works](docs/MOVEMENT.md) is the page that explains both.

### And three ways to keep running

The four layers above make a robot that **performs**. These make one that
**behaves** — and they are the reason you should not need to patch firmware.

| | Header | What it changes |
|---|---|---|
| **Ticking** | `mpx/live.h` | export `on_tick` and your code runs repeatedly, at a rate you pick. Balancing, reacting to load, following something — a controller, not a script |
| **Overlay** | `mpx/live.h` | a clamped per-joint offset **added** to whatever is already driving the robot. The built-in walk keeps walking; you add the lean, the limp, the tail wiggle |
| **Trace** | `mpx/live.h` | named numbers out of a running loop, plotted by `mpx-cli trace`. Because a control loop you cannot see is one you will end up debugging in firmware |

And four fields in `manifest.json` change what a skill *is*, with no code at all:

| | |
|---|---|
| `"provides_gait": "moonwalk"` | your skill joins the movement list. The phone triggers it exactly like `advance` |
| `"behaviour": true` | no 60-second watchdog. It runs until stopped — so `on_stop` is now your job |
| `"on": ["imu.lifted"]` | the firmware starts it. Events: `boot`, `imu.lifted`, `imu.fallen`, `imu.shaken`, `chat:<word>` |
| `"autorun": true` | it starts at power-on, behind a safe-mode guard that cannot leave you with a brick |

On top of all of it:

| | |
|---|---|
| `mpx/motion.h` | keyframes, easing, timelines — **where you author a movement** |
| `mpx/math.h` | `sin`, `sqrt`, `atan2`, easing. A skill has no libm; this is why |
| `mpx/sys.h` | logging, a clock, per-run parameters, `on_start` / `on_stop` |
| `mpx/gaits.h` | the 46 built-in movements, with descriptions and durations |
| `mpx/geometry.h` | the robot's real dimensions, generated from the firmware |

```bash
mpx-cli gaits            # browse the built-in movements
mpx-cli gaits wiggle     # search them
mpx-cli movements        # built-in AND skill-provided, one list
```

---

## Everything the robot can do, a skill can do

That is a strong claim, so it is enforced rather than promised.
`tools/gen_coverage.py` reads the firmware's public movement header
(`robot/robot.h`) and fails the build if it grows a capability the SDK cannot
reach. Today: **all 47 functions in it are accounted for** — 40 exposed,
5 boot-time plumbing, 2 withheld on purpose with the reason written down.

See **[firmware coverage](docs/internals/firmware-coverage.md)** for the
function-by-function table, and
**[firmware roadmap](docs/internals/firmware-roadmap.md)** for what is still
outside that header.

If you find something the firmware can do and a skill cannot, that is a bug in
this SDK. Please report it rather than forking the firmware.

---

## The commands you will actually use

| | |
|---|---|
| `mpx-cli doctor` | is my setup going to work? **run this first** |
| `mpx-cli init <name>` | scaffold a skill (`--lang c` / `ts` / `wat`) |
| **`mpx-cli deploy`** | **build + upload + run** |
| `mpx-cli logs -f` | the robot's own log, live over Wi-Fi |
| `mpx-cli trace` | plot the numbers a running skill emits |
| `mpx-cli run --param tempo=1.6` | run again with different settings, no rebuild |
| `mpx-cli stop` | end the running skill — the only way a behaviour ends |
| `mpx-cli gaits` / `movements` | the built-in catalogue, and everything installed |
| `mpx-cli safe-mode` | autorun disabled itself? this says why |
| `mpx-cli ls` / `delete` | what is on the robot |
| `mpx-cli sync` | refresh a project's generated bindings after an ABI change |
| `mpx-cli publish .` / `install` | share, and install other people's |

Run from inside a skill directory and every path comes from `manifest.json`, so
you never retype the name. Full list:
[REFERENCE.md](docs/REFERENCE.md#commands).

Set the robot's address once, in a `.env` beside your project:

```
MPX_HOST=192.168.2.1
```

---

## Languages

**C is the one to pick.** The friendly layer — timelines, easing, maths,
geometry, named joints, overlays — is C, and so is every example.

AssemblyScript (`--lang ts`) and WebAssembly text (`--lang wat`) get the raw
host functions and nothing else: centidegrees, manual frame sends, no maths.
They work, they are generated from the same ABI, and `mpx-cli sync` keeps them
current — but you are writing at the level of the wire protocol.

---

## Repository layout

```
docs/           SETUP, MOVEMENT, WORKFLOW, REFERENCE — plus internals/
sdk/include/    THE headers. One copy. mpx.h includes them all.
cli/            mpx-cli
examples/       01 … 06, in reading order
sim/            MuJoCo model and runner
abi/            the ABI, the gait catalogue and the coverage map, machine-readable
tools/          the generators and the CI checks
```

`sdk/include/` is the **only** copy of the headers in existence. Projects do not
vendor them; `mpx-cli` points the compiler at this one. The generated files in
`sdk/` and `docs/` come from the firmware and fail CI if they drift — see
[docs/internals/abi.md](docs/internals/abi.md) for why that turned out to
matter.

---

## Requirements

| | |
|---|---|
| Firmware | **ABI v4** — see [docs/internals/flashing.md](docs/internals/flashing.md) |
| Toolchain | WASI SDK for C; AssemblyScript for TS; WABT for WAT. All in the dev container. |
| Skill limits | 256 KB module, 128 KB memory, one at a time |
| Run time | 60 s — **unless** the manifest says `"behaviour": true` |
| Tick rate | 10–1000 ms; three overruns stops the loop |
| Overlay | ±20° per joint |

Full table: [WORKFLOW.md](docs/WORKFLOW.md#the-limits).

---

## When it does not work

```bash
mpx-cli doctor      # is the setup right?
mpx-cli logs -f     # what is the robot actually saying?
```

Then [the symptom table](docs/REFERENCE.md#when-something-goes-wrong) — what
each one almost always means.

If something behaves differently from what the documentation says, treat the
documentation as the thing that is wrong, and please report it.

---

## Coming from v2

Read **[RESTRUCTURE.md](RESTRUCTURE.md)** — every change, the reason for it, and
a name-by-name migration table.

Short version: `#include "mpx_compat.h"` instead of `"mpx_host.h"` and your
existing skills keep compiling. That shim is tested in CI, and it ships for one
release.
