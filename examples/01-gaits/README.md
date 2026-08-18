# 01 — Gaits and driving  ·  Layer 1

**You say what you want. The robot works out every joint angle, every frame.**

```bash
mpx-cli deploy examples/01-gaits
```

## What this layer is

The firmware contains a gait generator: a real-time loop that decides where all
twelve joints should be, 100 times a second, to make the robot walk. You do not
see any of that. You say `advance` and it walks.

**This is the only layer where a mistake in your maths cannot put the robot on
its side — because there is no maths.**

## When to use it

Whenever it can do what you want. Most skills should live mostly here and drop
a layer only for the specific moment that needs it. Walking is a genuinely hard
problem and it is already solved for you.

## The one thing to understand: gait *kind*

| Kind | At the end of its motion it… | Example |
|---|---|---|
| **CYCLES** | repeats until stopped | `advance`, `twerk` |
| **RETURNS** | performs once, stands again by itself | `jump`, `frontkick` |
| **HOLDS** | stays in that final pose | `lookup`, `init` |

This catches everyone once. A `HOLDS` gait is *still holding* when your skill
exits — so "the robot is stuck looking at the ceiling" is not a fault, it is
`lookup` doing exactly what it says.

```c
mpx_gait_for(MPX_GAIT_FORWARD, 2000);   /* CYCLES → give it a duration */
mpx_gait_once(MPX_GAIT_JUMP);           /* RETURNS → knows its own length */
mpx_gait(MPX_GAIT_LOOK_UP);             /* HOLDS → you must end it */
```

```bash
mpx-cli gaits            # all 46, with kind and description
```

## Naming versus steering

Named gaits are discrete. When you want *"forward at 40 mm/s while turning
gently"*, use a velocity instead — the same path the phone's joystick uses:

```c
mpx_drive_mm_s(60.0f, 0.0f, 15.0f);   /* mm/s, mm/s, deg/s */
mpx_stop();
```

## What it costs

You cannot shape the motion. The gait is what it is — you choose which one and
how long, and that is the whole of your control. If you need a pose the gait
generator does not produce, that is [layer 2](../02-feet).

## Next

[02-feet](../02-feet) — when you want poses the gaits do not have.
