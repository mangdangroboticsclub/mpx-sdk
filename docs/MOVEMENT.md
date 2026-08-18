# Movement

**Everything about making this robot move.**

The first part needs no code — it is for anyone with a robot. The rest is for
making a new one.

---

# Part 1 — What the robot already does

A movement is something the robot performs when you name it. `advance` walks
forward. `twerk` is a crowd-pleaser. There are **46 built in**, and skills can
add more.

```bash
mpx-cli gaits                # the catalogue, with descriptions
mpx-cli gaits look           # search it
mpx-cli movements            # built-in AND skill-provided
```

## Three kinds — this is the thing people trip over

| Kind | At the end of its motion it… | How many |
|---|---|---|
| **Holds** | stays in that pose until you change it | 17 |
| **Returns** | performs once, comes back to standing itself | 8 |
| **Cycles** | repeats until stopped | 21 |

`lookup` **holds**, `jump` **returns**, `advance` **cycles**.

So *"the robot is stuck looking at the ceiling"* is not a fault — it is a
`holds` movement doing exactly what it says. Send `init` to stand again.

The kind is in the catalogue and in `mpx/gaits.h`, both generated from the
firmware, so they cannot disagree with what the robot does.

## Steering instead of naming

Named gaits are discrete. For *"forward at 40 mm/s while turning gently"* the
robot takes a velocity — the same path the phone's joystick uses:

```c
mpx_drive_mm_s(40.0f, 0.0f, 15.0f);   /* forward, sideways, turn */
mpx_stop();
```

Walk speed is capped at **200 mm/s**.

## Leaning without stepping

```c
mpx_body(roll, pitch, yaw);       /* degrees */
mpx_body_speed(60);               /* deg/s — glide instead of snap */
```

Clamped by the firmware to **roll ±25°, pitch ±20°, yaw ±30°**, so the robot
cannot be asked to tip itself over this way.

---

# Part 2 — The mental model

Three facts. Get these and the API stops looking arbitrary.

## Coordinates

```
            +z  up
             │
             │        +x  forward  (nose)
             │      ╱
             │    ╱
    ─────────┼──────────  +y  left
            ╱│
```

**x** forward · **y** left · **z** up — so a foot below its hip is a *negative*
z. About −70 mm is standing.

## Units — degrees, everywhere that matters

| | |
|---|---|
| Joint angles | **degrees** from centre, ±135° |
| Foot positions | **millimetres** |
| Body attitude | **degrees** |
| Walk speed | **mm/s** |
| Time | **milliseconds** |

Centre is `0` and means something physical: **all twelve joints centred is the
standing pose.** That is how the robot is calibrated, which is why everything
measures from there.

The robot's real dimensions live in `mpx/geometry.h`, generated from the
firmware's own kinematics headers — thigh **50 mm**, calf **60 mm**, hips
**±59 mm** fore/aft and **±23.5 mm** left/right.

Do not retype them. This SDK shipped a 56 mm calf against the firmware's 60 mm
until a generator caught it, and a 4 mm error does not announce itself: the leg
still moves, it just lands somewhere else.

## The twelve joints

```c
MPX_FR  MPX_FL  MPX_RR  MPX_RL           /* front/rear, right/left */
MPX_HIP  MPX_SHOULDER  MPX_KNEE          /* hip outwards           */

mpx_joint_to(MPX_FR_KNEE, -8.0f);        /* name one directly      */
mpx_joint(MPX_FL, MPX_KNEE)              /* or compose, for loops  */
```

**hip** swings the leg sideways · **shoulder** swings it fore and aft ·
**knee** bends it.

## Nothing moves until you send the frame

```c
mpx_joint_to(MPX_FR_SHOULDER, 12.0f);
mpx_joint_to(MPX_FR_KNEE,     -8.0f);
mpx_frame_send();                    /* ← once per frame, not per joint */
```

Sending per joint gives you a robot that judders.

---

# Part 3 — Making a new one

## Which layer?

**Use the highest one that does what you need.** Each step down gives more
control and takes more responsibility.

| I want to… | Use |
|---|---|
| use a movement the robot has | `mpx_gait(MPX_GAIT_FORWARD)` |
| steer continuously | `mpx_drive_mm_s(40, 0, 15)` |
| **choreograph a shape over time** | **`mpx_stance_play()`** |
| place feet, let the robot solve the leg | `mpx_foot_to(MPX_FR, x, splay, z)` |
| set joint angles myself | `mpx_joint_to(MPX_FR_KNEE, deg)` |
| own the motor's control loop | `mpx_bus_take()` |

**Most new movements are timelines.** If you are writing a `for` loop full of
constants, you probably want the timeline instead.

## A complete movement

```c
#include "mpx.h"

MPX_EXPORT void on_start(void)
{
    MPX_REQUIRE_ABI();

    mpx_stance_key_t bow[] = {
        {    0, mpx_stance_stand(),              MPX_EASE_LINEAR },
        {  700, mpx_stance_front(22.0f, -52.0f), MPX_EASE_INOUT  },
        { 1600, mpx_stance_stand(),              MPX_EASE_OUT    },
    };
    mpx_stance_play(bow, 3, mpx_play(50, mpx_parami("repeats", 1)));
}
```

Keyframes with easing. The timeline interpolates, holds the frame rate off the
robot's clock, sends one frame per tick, and stops cleanly if cancelled.

Easing curves: `MPX_EASE_LINEAR`, `_IN`, `_OUT`, `_INOUT`. Using them is most of
the difference between a movement that looks mechanical and one that does not.

## Your own kinematics

If you want to solve the leg yourself, `mpx/math.h` has what a WASM skill
otherwise lacks — there is no libm in the sandbox:

```c
mpx_sin  mpx_cos  mpx_tan  mpx_sqrt  mpx_atan2  mpx_acos  mpx_asin
mpx_clamp  mpx_lerp  mpx_remap  mpx_deg  mpx_rad  mpx_ease
```

Use them. Writing your own `atan` from the Taylor series is off by up to **3.5°**
inside a leg's working range — a real bug people have shipped.

`mpx_ik2()` solves a two-link leg for you if you just want the angles.

## Composing, not replacing

The layers are not separate worlds. Two rules make them work together.

**Overlays add.** A small per-joint offset on top of whatever is already driving
the robot:

```c
mpx_gait(MPX_GAIT_FORWARD);   /* the firmware keeps walking */
mpx_overlay_lean(6.0f);       /* ...leaning into it         */
```

Clamped to **±20°** per joint, cleared when your skill ends. A garnish cannot
become a fall.

**Ownership is explicit.** For real authority over the joints, take it:

```c
if (mpx_take(MPX_OWN_JOINTS) != MPX_OK) return;   /* MPX_ERR_BUSY if taken */
```

## Making it react

A movement plays. A behaviour responds. Export `on_tick` and you run inside the
loop:

```c
MPX_EXPORT void on_start(void) {
    mpx_gait(MPX_GAIT_FORWARD);
    mpx_tick_hz(50.0f);
}

MPX_EXPORT void on_tick(int dt_ms) {
    float roll, pitch;
    mpx_imu_tilt(&roll, &pitch);
    mpx_overlay_lean(mpx_clamp(-roll * 0.45f, -8.0f, 8.0f));
    mpx_trace_f("roll", roll);
}
```

`on_tick` runs **after** `on_start` returns, never alongside it — so there is no
shared state to guard and no locking to write.

It is paced on the skill's own thread rather than called from the gait task,
because that loop is what keeps the robot standing and arbitrary skill code does
not belong inside it. A tick is therefore not phase-locked to a gait frame,
which does not matter for trimming and stabilising. Overrun three ticks in a row
and the loop stops, with the reason in the log.

## Sensing

```c
mpx_imu_t d;  mpx_imu(&d);            /* ax ay az gx gy gz */
mpx_imu_tilt(&roll, &pitch);          /* degrees, the useful form */

mpx_joint_at(MPX_FR_KNEE);            /* measured angle, degrees   */
```

**Close loops on `mpx_joint_at()`.** It is in the same frame as
`mpx_joint_to()`. The raw `mpx_joint_raw()` is in the opposite frame, and a loop
built on it diverges instead of converging.

## Giving it a name the robot knows

Declare it in `manifest.json` and your movement joins the catalogue:

```json
{
  "provides_gait": "moonwalk",
  "behaviour": false,
  "on": ["imu.lifted", "chat:moonwalk"],
  "autorun": false
}
```

```bash
mpx-cli deploy
mpx-cli movements        # "moonwalk" now sits beside "advance"
```

Triggerable from the phone exactly like a built-in. **No firmware edit.**

| Field | What it changes |
|---|---|
| `provides_gait` | joins the movement list; the phone triggers it by name |
| `behaviour` | no 60-second watchdog — runs until stopped |
| `on` | the firmware starts it on an event |
| `autorun` | starts at power-on |

Events: `boot`, `imu.lifted`, `imu.fallen`, `imu.shaken`, `chat:<word>`. One
skill runs at a time, so an event during a run is dropped, not queued, and each
event has a 4-second cooldown.

**A behaviour makes `on_stop` your job** — removing the watchdog is the point,
so parking the robot on the way out is yours to get right.

**Autorun cannot brick the robot.** Three boots that do not stay up for 20
seconds and the firmware disables it, comes up bare, and says why.
`mpx-cli safe-mode --clear` re-enables it.

## Owning the motor

The lowest layer: per-joint Kp/Kd and direct current control.

```c
mpx_bus_take();                                   /* parks the gait */
mpx_gain_set(MPX_FR_KNEE, MPX_PARAM_KP_POSITION, 95.0f);
mpx_bus_stage(MPX_FR_KNEE, deg, 400.0f, 0, 0);
mpx_bus_send();
mpx_bus_release();
```

Two things bite here. `mpx_bus_*` speaks the **absolute** 0–270° frame, not the
±135° one — that is deliberate, so you cannot reach it by accident. And you
cannot walk while holding the bus: take it, set gains, release, then gait.

Five parameters return `MPX_ERR_READONLY` from a skill: the three calibration
slots, plus `REVERSE_MOTOR` and `REVERSE_POSITION_SENSOR`. Change those from
Servo Studio, with a human watching the joint move.


### Where Kp and Kd live

Three places, and it matters which you use.

| | How | Persists? |
|---|---|---|
| **From a skill** | `mpx_gain_set()`, `mpx_gains_all()` | until reboot — and until *you* reset it |
| **Servo Studio** | robot web UI → Settings → Servo Testing | until reboot |
| **Burnt to flash** | `mpx_gain_save()` | **survives reboot** |

**Skills and Servo Studio write the same four slots on the same driver board.**
`mpx_gain_set()` reaches `driver_board_set_param()`, and so does the Studio
table — so a number you find with the Studio's live scope is the number you
paste into your skill, unconverted.

Kp and Kd shape the **position** loop — where the joint goes. Underneath it the
board runs a **current** loop, deciding how the motor produces the torque the
position loop asked for. That is what you reach for when a joint arrives in the
right place but arrives *badly*:

| Gain | Stock | Studio step | One joint | All twelve |
|---|---|---|---|---|
| Kp position | `65` | 0.01 | `mpx_gain_set(j, MPX_PARAM_KP_POSITION, v)` | `mpx_gains_all(kp, kd)` |
| Kd position | `800` | 0.01 | `mpx_gain_set(j, MPX_PARAM_KD_POSITION, v)` | ↑ same call |
| Kp current | `0.0006` | 0.0001 | `mpx_current_kp(j, v)` | `mpx_current_all(kp, kff)` |
| Kff current | `0.00022` | 0.00001 | `mpx_current_kff(j, v)` | ↑ same call |
| Max PWM duty | — | 0.01 | `mpx_max_effort(j, 0..1)` | `mpx_max_effort_all(0..1)` |

**Two bulk calls, one per loop — not one call taking four numbers.** That is
deliberate. A single `mpx_gains_all(65, 800, 0.0006, 0.00022)` puts values five
orders of magnitude apart side by side as unlabelled arguments, where swapping
two is both catastrophic and invisible; this SDK has already shipped that
mistake once. Split by loop, every argument list holds numbers of the same size.

Max PWM duty is in neither, because it is a torque **ceiling** rather than a
tuned gain — if it rode along with the gains, every stiffness change would
quietly reset a safety limit you set on purpose.

**Do not carry a number across the two loops.** They are in different units and
about five orders of magnitude apart: `65` is a sane position gain and a
catastrophic current gain — the joint sings, gets hot, and nothing on screen
says why. Scale from `MPX_KP_CURRENT_STOCK` and `MPX_KFF_CURRENT_STOCK` rather
than typing an absolute value.

`mpx_gains_stock()` restores all four on all twelve joints. Max PWM duty is a
safety ceiling rather than a tuned gain, so it has no stock value and is not
part of that; `mpx_max_effort_all(1.0f)` gives the authority back and
`mpx_max_effort_all(0.6f)` is the cheapest safety measure available while you
are developing a movement.

`mpx_max_effort_all(0.6f)` caps every joint at once, which is the cheapest
safety measure available while you are developing a movement.

**Five slots are refused from a skill.** Three are calibration; the other two,
`REVERSE_MOTOR` and `REVERSE_POSITION_SENSOR`, flip a *direction* — write one
and a single joint drives opposite to the other eleven, which survives the skill
that did it. `mpx_param_read_only()` tells you which, so you can ask rather than
find out. All five are still settable from Servo Studio, where a human is
watching the joint move.

The slot numbers are a wire protocol, so `mpx/params.h` is **generated from the
driver board's own table**. It was hand-written once and was wrong: slot 4 is
`reverse_motor`, not `KP_POSITION`, so asking for stiffness reversed a joint.

Gains live on the driver board, not in your skill, so **they outlive the skill
that set them.** Leave one joint at Kp 95 and every built-in gait afterwards
walks slightly wrong with nothing on screen to explain it. Restore them in
`on_stop` as well as at the end of `on_start`, so a trap cannot leave the robot
mistuned.

Servo Studio is the right tool for *finding* a value — live scope, step the
joint, watch the overshoot. Put the number you found into your skill.

---

# Part 4 — The five things that catch people

**A `holds` movement is still holding when your skill exits.** Whatever pose you
finish in is where the robot stays. End with `mpx_stand()`.

**Nothing moves until `mpx_frame_send()`.** One send per frame, not per joint.

**There is no libm.** Use `mpx/math.h`.

**A skill is killed at 60 seconds** unless it declares `"behaviour": true`.

**Only one skill runs at a time.** A skill cannot start another;
`mpx_gait()` on a skill-provided name returns `MPX_ERR_STATE` rather than
nesting.

---

# Part 5 — Recipes

**Walk a square**

```c
for (int i = 0; i < 4; ++i) {
    mpx_drive_for(1.0f, 0.0f, 0.0f, 2000);
    mpx_gait_for(MPX_GAIT_TURN_LEFT, 900);
}
mpx_stand();
```

**Wave a paw**

```c
mpx_stand();
mpx_take(MPX_OWN_JOINTS);
for (int i = 0; i < 60; ++i) {
    mpx_joint_to(MPX_FR_SHOULDER, 40.0f);
    mpx_joint_to(MPX_FR_KNEE, -30.0f + 15.0f * mpx_sind(i * 24.0f));
    mpx_frame_send();
    mpx_sleep(20);
}
mpx_stand();
```

**Body sway with the feet planted**

```c
for (int i = 0; i < 90; ++i) {
    float sway = 18.0f * mpx_sind(i * 4.0f);
    mpx_feet_to(sway, 0.0f, MPX_STAND_Z_MM);
    mpx_sleep(20);
}
```

**Working examples:** [01-gaits](../examples/01-gaits) ·
[02-feet](../examples/02-feet) · [03-joints](../examples/03-joints) ·
[04-motors](../examples/04-motors) · [05-together](../examples/06-together)
[02-gaits](../examples/01-gaits) · [05-timeline](../examples/06-together) ·
[06-own-ik](../examples/03-joints) · [09-live](../examples/06-together) ·
[10-behaviour](../examples/06-together)

---

**Next:** [WORKFLOW.md](WORKFLOW.md) — parameters, tracing, publishing ·
[REFERENCE.md](REFERENCE.md) — every function, every error, every command.
