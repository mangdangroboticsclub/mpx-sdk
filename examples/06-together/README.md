# 06 — All four layers together

**Real movements mix layers. The skill is knowing when to come back up.**

```bash
mpx-cli deploy examples/06-together
mpx-cli movements          # "greet" is now in the list
mpx-cli trace              # watch it level itself
mpx-cli stop               # the only way a behaviour ends
```

## What it does

A short greeting, then it stays behind and keeps itself level.

| | | Why that layer |
|---|---|---|
| **L1** | walks in | walking is solved; do not re-solve it |
| **L2** | bows | a pose the gaits do not have, but still feet on the floor |
| **L3** | waves a paw | a waving paw is *not* a foot on the floor, so the IK cannot express it |
| **L4** | goes soft to be patted | "be compliant" is invisible to every layer above |
| **L1** | walks off | back up, immediately |

**That last row is the point of this example.** Each layer is used for the one
moment that needs it, and the routine returns to the highest layer that works as
soon as it can. Staying at layer 4 to walk would mean writing a gait generator.

## The layer ladder, in host calls

The examples import this many host functions:

```
  01-gaits     5
  02-feet      5
  03-joints   10
  04-motors   11
  05-together 25
```

Lower layers are not more powerful — they are more *work*. The count is the
cost.

## From script to behaviour

`on_start` runs once and returns. Then `on_tick` takes over at 25 Hz:

```c
mpx_tick_hz(25.0f);                     /* at the end of on_start */
```

```c
MPX_EXPORT void on_tick(int dt_ms) {
    float roll, pitch;
    mpx_imu_tilt(&roll, &pitch);
    mpx_overlay_lean(mpx_clamp(-roll * s_gain, -8.0f, 8.0f));
    mpx_trace_f("roll", roll);
}
```

`on_tick` runs **after** `on_start` returns, never alongside it — so there is no
shared state to guard and no locking to write.

An **overlay** *adds* to whatever is already driving the robot rather than
replacing it, clamped to ±20° by the firmware. A trim cannot become a fall.

## Four fields that change what this skill *is*

Look at `manifest.json`. None of this is code:

```json
{
  "provides_gait": "greet",
  "behaviour": true,
  "on": ["imu.lifted"],
  "params": [ ... ]
}
```

| | |
|---|---|
| `provides_gait` | it joins the movement list; the phone triggers `greet` like any built-in |
| `behaviour` | no 60-second watchdog — it runs until stopped |
| `on` | the firmware starts it when the robot is picked up |
| `params` | tunable at run time, no rebuild; the web UI renders a slider |

```bash
mpx-cli run --param gain=0.9 --param speed=80
```

## What a behaviour makes your job

**`on_stop` matters now.** Removing the watchdog is the whole point, so parking
the robot on the way out is yours to get right. This one clears its overlay,
releases anything it holds, restores stock gains and stands — and it runs
however the skill ends, including a trap.

## Next

[MOVEMENT.md](../../docs/MOVEMENT.md) for the whole picture ·
[WORKFLOW.md](../../docs/WORKFLOW.md) for params, tracing and publishing.
