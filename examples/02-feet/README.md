# 02 — Feet  ·  Layer 2

**You say where a foot should be. The firmware solves the leg.**

```bash
mpx-cli deploy examples/02-feet
```

## What this layer is

Inverse kinematics: you give a position in space, and something works backwards
to the joint angles that put the foot there. The firmware does that for you —
and it is the *same* solver the gait generator uses, so your poses sit in the
same frame as the built-in movements and inherit the same calibration.

## When to use it

When you want poses the built-in gaits do not have, but you do not want to own
the trigonometry. Bowing, crouching, stretching, leaning, placing a foot
somewhere specific — all of it is natural here and awkward one layer up.

## Coordinates, for one leg, relative to its own hip

```
      +x forward          x      mm, forward positive
        ↑                 splay  degrees, sideways swing at the hip
        │                 z      mm, UP positive
   hip ─┼──→ +y left
        │                 So a foot on the floor is NEGATIVE z.
        ↓                 About −70 mm is standing.
      foot
```

The sign of `z` is the thing people get wrong first. Up is positive, the floor
is below the hip, therefore standing is a negative number.

```c
mpx_feet_to(0.0f, 0.0f, MPX_STAND_Z_MM);        /* all four, same place */
mpx_foot_to(MPX_FR, 20.0f, 0.0f, -55.0f);       /* one leg              */
```

`MPX_STAND_Z_MM` and the robot's link lengths come from `mpx/geometry.h`,
generated from the firmware's own kinematics headers — not estimates.

## A trick worth knowing

Moving all four feet *backwards together* moves the **body forwards**. The robot
rides over its own feet without stepping. That is how the sway in this example
works, and it is the basis of most "look alive" idle motions.

## What it costs

**Balance is now yours.** The gait generator kept the robot standing; here,
nothing does. Lift a leg the robot is standing on and it falls over. This
example plants three feet before it lifts the fourth, on purpose.

## Next

[03-joints](../03-joints) — when the built-in solver cannot express what you
want. A waving paw, for instance, is not a foot on the floor.
