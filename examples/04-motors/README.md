# 04 — Motors  ·  Layer 4

**You own the motor's control loop — the target angle and the gains.**

```bash
mpx-cli deploy examples/04-motors
```

## What this layer is

Every layer above sends a target angle and the servo decides how to get there.
Here you set that decision too: **Kp** is how hard the motor pulls towards its
target, **Kd** damps the approach.

## When to use it

When stiffness is part of the movement. Landing softly. Going compliant so a
leg can be pushed by hand. Holding a pose against a load. **Nothing above this
layer can express any of that** — it is the only reason to come down here.

```c
mpx_bus_take();
mpx_gains_all(65.0f, 800.0f);                              /* stock */
mpx_gain_set(MPX_FR_KNEE, MPX_PARAM_KP_POSITION, 95.0f);   /* one stiffer */
mpx_bus_stage(MPX_FR_KNEE, -18.0f, 400.0f, 0.0f, 0.0f);
mpx_bus_send();
mpx_bus_release();
```

## Three things to know before you run it

**1. Taking the bus parks the gait.** You cannot walk while you hold it. The
sequence is: take → set gains → release → walk.

**2. Gains persist after you let go.** They live on the driver board, not in
your skill. Leave one joint at Kp 95 and every built-in gait afterwards walks
slightly wrong, with nothing on screen to explain why. **Always
`mpx_gains_stock()` on the way out** — this example does it in `on_stop` too, so
a crash cannot leave the robot mistuned.

**3. Five parameters are refused from a skill.** Three are calibration —
`MIN_POSITION_ADC`, `MAX_POSITION_ADC`, `RANGE_POSITION_DEG` — and decide what
every angle *means*. The other two, `REVERSE_MOTOR` and
`REVERSE_POSITION_SENSOR`, flip a *direction*: write one and a single joint
drives opposite to the other eleven, which is a robot tearing at its own legs.
All five return `MPX_ERR_READONLY`, and `mpx_gain_save()` would have burnt the
mistake into flash where a reboot will not clear it.

Ask before you write, rather than finding out:

```c
if (!mpx_param_read_only(p)) mpx_gain_set(j, p, v);
```

Change them from Servo Studio, with a human watching the joint move.

## The rest of the control loop

Kp and Kd shape the **position** loop — *where* the joint goes. Underneath it
the board runs a **current** loop, deciding how the motor produces the torque
the position loop asked for:

```c
mpx_current_kp (MPX_FR_KNEE, 40.0f);   /* crisper torque; too high and it buzzes */
mpx_current_kff(MPX_FR_KNEE, 12.0f);   /* stops it sagging under weight          */
mpx_max_effort (MPX_FR_KNEE, 0.6f);    /* 0..1 — a physical torque ceiling       */
```

`kff_current` is the useful one. A pure Kp loop has to be *off target* to
produce force, so a joint sags under constant load — which on a quadruped is
the robot's own weight. Feed-forward supplies that standing torque up front and
the droop goes away.

`mpx_max_effort_all(0.6f)` caps every joint at once. It is the cheapest safety
measure available while you are developing a movement near furniture.

## The thing only this layer can do

Change stiffness *during* a motion:

```c
float soft = 90.0f - 60.0f * t;                       /* stiff → compliant */
mpx_bus_stage(MPX_FR_KNEE, -18.0f * t, 400.0f, soft, 900.0f);
mpx_bus_send();
```

The knee goes soft as it arrives, so it settles instead of slamming. That is
not a pose — it is a *feel*, and it is invisible to every other layer.

## A note on angle frames

`mpx_bus_stage()` takes the same relative degrees as the rest of the SDK.
There is also `mpx_bus_stage_abs()`, which takes the driver board's own
0–270° frame where 135 is centre. Prefer the first: one angle convention in
your code is worth more than matching the wire.

## What it costs

The safety net is gone. A bad gain makes a joint oscillate or go limp under
load. Keep `MPX_PARAM_CURRENT_LIMIT` set — it is what stops a stalled motor
cooking itself.

## Next

[06-together](../06-together) — all four layers in one routine, and knowing
when to come back **up**.
