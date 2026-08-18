# 05 — Sensing

**The robot can feel itself. This is how you use that.**

```bash
mpx-cli deploy examples/05-sensing
mpx-cli trace                      # in another terminal
```

Then **tilt the robot** — it stays level. **Push a front leg** — it yields.

## Why this is not "layer 5"

The four layers are about **output**: gaits, feet, joints, motors. Sensing is the
other axis — it is **input**, and it works with all four. You can read the IMU
and respond with a gait (layer 1) or with a single joint (layer 3). Nothing here
replaces a layer; it decides what you ask that layer for.

## What you can read

**The IMU** — six axes, at whatever rate you ask:

```c
mpx_imu_t d;
mpx_imu(&d);                       /* d.ax d.ay d.az  g   */
                                   /* d.gx d.gy d.gz  dps */
mpx_imu_tilt(&roll, &pitch);       /* degrees — usually what you want */
```

`az` is about **1.0 g** when the robot is upright and near **0** in free fall,
which is how the firmware's own `imu.lifted` trigger works.

**Every joint** reports back:

```c
mpx_joint_at(MPX_FR_KNEE);         /* measured angle, degrees */
mpx_joint_load(MPX_FR_KNEE);       /* what it is fighting     */
mpx_joint_current(MPX_FR_KNEE);    /* mA                      */
mpx_joint_temp_c(MPX_FR_KNEE);     /* °C — servos do cook     */
mpx_joint_moving(MPX_FR_KNEE);     /* 0 or 1                  */
mpx_battery_v();                   /* volts                   */
```

## B — staying level

Read the tilt, command the opposite:

```c
mpx_body(mpx_clamp(-roll * 0.8f, -20.0f, 20.0f), ..., 0.0f);
```

Counter-rotating the **body** keeps the feet planted, so this is safe on a
slope. A gain of `1.0` would be exact levelling; less is calmer, and calmer is
almost always what you want on a real robot.

## C — feeling a push

Load is what the servo is fighting against. Push a leg and it rises.

**Treat load as "something is happening", not as a measurement.** It is noisy,
unsigned, and varies between servos. This example uses a threshold and a decay
rather than a number it trusts:

```c
if (load > 120) yield += 1.5f;     /* give way   */
else            yield *= 0.90f;    /* spring back */
```

Yielding to a push is most of the difference between a robot that feels alive
and one that feels like a machine.

## D — closing a loop, correctly

```c
float error = target - mpx_joint_at(MPX_FR_KNEE);
mpx_joint_to(MPX_FR_KNEE, target + error * 0.25f);
```

**`mpx_joint_at()` reads back in the same frame `mpx_joint_to()` writes.** There
is a raw reading underneath (`mpx_joint_raw()`) that runs the *opposite* way — a
loop built on it makes the error term the wrong sign and diverges instead of
converging, silently and at speed. This is the single easiest way to hurt a
robot with a sensor, and the reason `mpx_joint_at()` exists.

## Watching it

```bash
mpx-cli trace                  # live sparklines
mpx-cli trace --csv > run.csv  # for a real plot
```

`mpx_trace_f()` is how you tune any of this. Guessing at a gain and watching the
robot is much slower than watching the number.

## Doing it continuously

This example runs its loops inside `on_start`, which is simple to read and ends
when the skill ends. For sensing that should run *while other things happen* —
a stabiliser under a walk — use `on_tick`. [06-together](../06-together) shows
that.

## Next

[06-together](../06-together) — all four layers plus sensing, in one routine.
