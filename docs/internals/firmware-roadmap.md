# Firmware changes that would keep makers in the SDK

The goal behind this SDK is that **adding a movement should never be a firmware
operation**. Getting there is not mainly about adding host functions — ABI v3
already reaches every movement capability `robot.h` exposes, and
[firmware-coverage.md](../internals/firmware-coverage.md) fails the build if
that stops being true.

What is left is *shape*. A skill today is a script that runs once, alone, for at
most sixty seconds, on its own thread, while the gait task stands aside. Several
ordinary things a maker wants are not hard in that model — they are impossible
in it, and the only way to do them is to patch firmware.

These are ranked by how much each one removes a reason to fork.

---

## 1. `on_tick` — let a skill run inside the control loop

**The problem.** `gait_task()` is the real-time loop: it generates a frame,
flushes it, and yields, about every 10 ms. A skill does not run in that loop. It
runs on a separate thread, and while it runs the gait task deliberately skips
its own flush:

```c
// robot.cc, gait_task()
if (!wasm::is_running()) {
    flush();
}
```

That is a sensible way to stop the two fighting, and it means a skill is
all-or-nothing: either the firmware is moving the robot or you are.

So anything that has to *react continuously* — stay level on a slope, stiffen a
leg when it takes load, stabilise while the built-in walk runs, respond to being
picked up — has nowhere to live. Every one of those is a firmware patch today.

**The change.** An optional second export, called by the gait task each tick:

```c
MPX_EXPORT void on_tick(int dt_ms);   /* optional; called every gait tick */
```

Run it inside the loop, after the gait generates its frame and before the flush,
with a hard budget — a few hundred microseconds — measured every call. Overrun
twice and the skill is evicted with a logged reason. That keeps the loop
real-time whatever a maker writes.

**Why it is the biggest one.** It changes what a skill *is*: from a script that
plays a movement to a controller that participates in one. Reactive behaviour
stops being a firmware concept.

---

## 2. Let a skill register as a gait

**The problem.** Adding a named movement means three firmware edits — the
`GaitCmd` enum, the name table in `host_robot_gait()`, and the `switch` in
`gait_task()` — plus a reflash. And then the web UI still has to learn about it.

For the *one thing this SDK is for*, the supported path is currently to modify
firmware.

**The change.** Let an installed skill declare what it provides:

```json
{ "slug": "moonwalk", "provides_gait": "moonwalk" }
```

The gait dispatcher tries the built-in table first and falls through to the
installed skills. `GET /v1/robot/gait` returns firmware gaits and skill gaits in
one list, so the web UI, the marketplace and `mpx-cli gaits` show them
identically, and a skill-provided move is triggerable from the phone exactly
like `advance`.

**Why.** "Add a new move" stops being a firmware operation at all. This is the
change that most directly serves the goal.

---

## 3. An overlay buffer — compose instead of take over

**The problem.** The four control layers replace one another rather than stack.
"The built-in walk, plus a tail wiggle" means reimplementing the walk, because
there is no way to add to what the gait generator produced.

**The change.** One additive array applied in the flush path:

```c
mpx_overlay_set(MPX_RL_HIP, +8.0f);   /* added on top of whatever is driving */
mpx_overlay_clear();
```

```c
// robot.cc, in flush()
goal[i] += s_overlay[i];      // cleared when a skill ends
```

Perhaps thirty lines of firmware, clamped to a small range so an overlay cannot
tip the robot on its own.

**Why.** A large class of "I just want the walk but slightly different" forks
becomes a five-line skill. It also pairs with `on_tick`: an overlay written from
a tick handler is a stabiliser.

---

## 4. Behaviours: long-running, and able to start at boot

**The problem.** 60 seconds, one at a time, and nothing runs at power-on. So
anything that should simply *be true about the robot* — it balances, it reacts
when lifted, it idles with a breathing motion — cannot be a skill.

**The change.** A second run mode alongside the one-shot: no watchdog kill, but
the skill must return from `on_tick` within budget, which is a stronger
guarantee than a timeout anyway. Plus an autorun slot so one behaviour can be
marked to start at boot, and a documented way to stop it from the web UI.

**Why.** Personality and reactive behaviour is most of what people actually want
a quadruped to have, and today all of it lives in firmware.

---

## 5. Deal with the Lua path

**The problem.** There is a second scripting API in the firmware —
`lua/lua_bindings.cc`, about 40 KB, reachable over `/v1/lua/run`,
`/v1/lua/enqueue` and `/v1/lua/save`. It exposes its own `gait`, `ik_fr`,
`imu_read`, `flush`, `get_config`, and offsets, plus `fs` and `crypto` — so it
currently has **more** access than a sandboxed WASM skill does.

Two hand-maintained movement APIs over one robot will drift, and the drift is
silent. It also splits the answer to "how do I make my robot move" in two, which
is exactly the confusion this restructure set out to remove.

**The change.** Pick one, deliberately:

* If Lua stays, generate its bindings from `abi/host_functions.json` like every
  other language, and bring its capabilities in line with the sandbox rather
  than above it.
* If it does not, deprecate the endpoints and say so in the docs.

Either is fine. Leaving it undecided is the expensive option.

---

## 6. Let skills write to the telemetry stream

**The problem.** `/v1/telemetry/stream` already exists as a WebSocket. A skill
cannot write to it — its only output is text through `print`. When you cannot
see what your control loop is doing, a serial monitor and a firmware build start
to look reasonable.

**The change.**

```c
mpx_trace("knee_err", err_deg);        /* named float, into the stream */
```

`mpx-cli trace` plots it in the terminal; the PWA plots it on a chart. Cheap,
and it removes one of the strongest remaining pulls toward firmware.

---

## 7. Unify the two angle frames — measured, and deliberately not done

**The problem.** Two raw frames run in opposite directions: the GAIT frame that
`s_goal_pos[]` and `set_servo_angle()` speak, and the AT32 frame the driver
boards, the feedback cache and Servo Studio speak, with `at32 == 1024 - gait`.
Confusing them is not a compile error. It has already happened once —
`read_moving()` compared a measured AT32 value against a commanded gait value,
so every pose away from dead centre read as "still moving" forever.

**What the numbers say.** The proposed change was to normalise on one internal
frame and convert once at the driver-board boundary. Modelling the whole path
natively (`mangdang/tools/frame_check.cc`) shows that does not pay:

* Flipping the internal frame and scaling the obvious way changes **1020 of
  1024** wire positions by one deci-degree. Small, and a silent recalibration
  of all twelve joints against offsets already stored in NVS.
* The only bit-identical version keeps the existing expression, i.e. converts
  back to the gait frame inside `sync_write()`. **The mirror does not go away;
  it moves.**

So the change is either a quiet recalibration or cosmetic, on the one code path
where a sign error mirrors every leg.

**What was done instead.** An audit of every site where a measured value meets a
commanded one: `read_moving()` (fixed), `read_angle_cdeg()` (converts),
`read_position()` and `servo_read*()` and Studio (deliberately AT32, documented).
**No live frame bug remains** — the mirror is contained at three named
boundaries.

And the model became a permanent test:

```bash
c++ -std=c++17 -O1 -o frame_check tools/frame_check.cc && ./frame_check
```

It runs in a second with no robot, and asserts the properties that matter — a
command survives the round trip, a positive command raises the measured angle,
an overlay agrees in sign with a command, and the frames really are opposed.
Reintroduce the mirror and it fails loudly rather than at walking speed.

**When to revisit.** If the driver boards change again, the conversion has to be
rewritten anyway and the frames should be unified in the same operation, with
`frame_check.cc` as the safety net. Doing it now buys tidiness and risks a robot.

---

## 8. Triggers

**The problem.** A skill only ever runs because a human pressed run. No skill can
say "start me when the IMU says I have been picked up" or "when a chat message
arrives".

**The change.** A small event table in the manifest, dispatched by firmware:

```json
{ "on": ["boot", "imu.lifted", "chat.command:dance"] }
```

**Why.** It is the difference between a robot that performs tricks and a robot
that behaves. Worth doing after 1–4.

---

## Suggested order

| | Change | Effort | Removes the need to fork for |
|---|---|---|---|
| 1 | `on_tick` | medium | anything reactive or closed-loop |
| 2 | skills register as gaits | medium | adding a named movement |
| 3 | overlay buffer | small | "the built-in walk, but…" |
| 4 | behaviours + autorun | medium | always-on personality |
| 5 | decide about Lua | small | — (prevents future drift) |
| 6 | `mpx_trace` | small | debugging a control loop |
| 7 | one angle frame | large | — (deletes a bug class) |
| 8 | triggers | medium | event-driven behaviour |

1, 3 and 6 together are a modest amount of firmware work and would close most of
the remaining gap. 2 is the one that changes the story.

---

## What is already fine

Worth saying, because these are the parts not to disturb:

* **The sandbox boundary.** Memory isolation, the watchdog, and the forced bus
  release on exit are what make it safe to run a stranger's skill. Every change
  above keeps them.
* **Deliberate omissions.** Servo Studio's mode switch is withheld from skills
  because a human is watching a joint move; the calibration ADC parameters are
  read-only for the same reason. Both are right.
* **The generated ABI.** `tools/gen_abi.py --check` means the firmware table is
  the only place a host function exists. Keep new work inside that pattern.

See also: [ABI and how to add a host function](abi.md) ·
[firmware coverage](../internals/firmware-coverage.md)
