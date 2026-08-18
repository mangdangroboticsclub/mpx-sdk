# 03 — Joints  ·  Layer 3

**You solve the leg. The firmware just carries the numbers to the servos.**

```bash
mpx-cli deploy examples/03-joints
```

## What this layer is

Twelve numbers, in degrees, straight through. No solver, no interpretation. You
get exactly what you ask for — including a leg folded into the body, if that is
what you asked for.

## When to use it

When the built-in IK cannot express what you want. It places **feet**, so
anything that is not a foot on the floor needs this layer: a waving paw, a leg
held out, a joint moved for its own sake. Also when you need a different leg
model, or a loop closed on measured angles.

## The rule that catches everyone

**Nothing moves until `mpx_frame_send()`.**

```c
mpx_joint_to(MPX_FR_SHOULDER, 20.0f);
mpx_joint_to(MPX_FR_KNEE,    -25.0f);
mpx_frame_send();                       /* ← once per frame, not per joint */
```

Set every joint you want for this frame, then send once. Sending after each
joint gives you a robot that judders, because each send is a separate bus
transaction.

## Angles

Degrees **from centre**, ±135°. Centre means something physical: **all twelve
joints at 0 is the standing pose.** That is how the robot is calibrated, which
is why everything measures from there.

```c
MPX_FR MPX_FL MPX_RR MPX_RL        /* front/rear, right/left */
MPX_HIP MPX_SHOULDER MPX_KNEE      /* hip outwards           */
MPX_FR_KNEE                        /* or name one directly   */
```

## Doing your own kinematics

A WASM skill has **no libm** — no `sin`, no `sqrt`, no `atan2`. `mpx/math.h`
provides them. Use it: writing your own `atan` from the Taylor series is off by
up to **3.5°** inside a leg's working range, which is a real bug people ship.

`mpx_ik2()` solves a two-link leg if you just want the angles:

```c
float shoulder, knee;
mpx_ik2(x_mm, z_mm, &shoulder, &knee);
```

## Closing a loop — and the mistake that diverges

```c
float measured = mpx_joint_at(MPX_FR_KNEE);     /* same frame as _to() */
float error    = target - measured;
mpx_joint_to(MPX_FR_KNEE, target + error * 0.25f);
```

`mpx_joint_at()` reads back in the **same frame** `mpx_joint_to()` writes.
There is a raw reading underneath (`mpx_joint_raw()`) that runs the *opposite*
way — a loop built on that one makes the error term the wrong sign and diverges
instead of converging, silently and at speed.

Watch it settle:

```bash
mpx-cli trace
```

## What it costs

Everything is yours: balance, reachability, the maths. The firmware will
faithfully carry out a pose that puts the robot on its face.

## Next

[04-motors](../04-motors) — when *how hard* a joint holds its position is part
of the movement.
