# Workflow

**How the day actually goes** once you are set up.

---

## The loop

```bash
mpx-cli deploy        # build + upload + run
mpx-cli logs -f       # what the robot is saying
```

That is it. Nearly all your time is those two commands. Paths come from
`manifest.json`, so you never retype the skill's name.

A failing skill exits non-zero and says why, rather than printing a green tick:

```
❌ my_move.wasm — trapped during execution (0.4s)
   'mpx-cli logs' shows what the robot logged.
```

---

## Tune without rebuilding

Declare parameters in `manifest.json`:

```json
"params": [
  {"name": "gain",  "type": "float", "default": 0.45, "min": 0.0, "max": 1.5},
  {"name": "repeats","type": "int",  "default": 1,    "min": 1,   "max": 10}
]
```

Read them:

```c
float gain = mpx_paramf("gain", 0.45f);
int   n    = mpx_parami("repeats", 1);
```

Change them:

```bash
mpx-cli run --param gain=0.9 --param repeats=3
```

Nothing is rebuilt. The robot's web UI renders a slider per parameter with no
extra work from you — which is what makes a skill something other people can
actually use.

---

## Watch a control loop

`print` answers *did I get here*. It does not answer *what is my knee error
doing*.

```c
mpx_trace_f("roll", roll_deg);
```

```bash
mpx-cli trace                    # live sparklines in the terminal
mpx-cli trace --signal roll      # just one
mpx-cli trace --csv > run.csv    # for a real plot
```

Tuning a gain becomes watching a chart instead of guessing. The robot holds the
last **256 samples** — a *what just happened* window, not a recording facility.
Trace one or two signals, not ten.

---

## Simulate — when it earns its keep

```bash
python sim/mjsim.py build/my_move.wasm
```

Runs the *same* `.wasm` through physics and reports whether the robot fell, how
far it travelled, and how closely each joint tracked. Writes an HTML replay you
can scrub through.

**Worth it for gaits and anything where the robot might tip.** For ordinary
skills `mpx-cli deploy` is faster.

It proves your skill runs, terminates and stays in range. It does **not** prove
your kinematics describe reality — a wrong link length is consistent in
simulation and wrong on the bench.

---

## Share it

```bash
mpx-cli login yourname
mpx-cli publish .
```

Others install it with:

```bash
mpx-cli install yourname~my_move
```

A skill that declares `provides_gait` arrives as a **movement** on their robot,
not just a file — it shows up in their movement list and on their phone.

The robot keeps its own record of what is installed, so a second phone or laptop
sees it and can remove it.

---

## The commands

| | |
|---|---|
| `mpx-cli doctor` | is my setup right? **run this first** |
| `mpx-cli init <name>` | scaffold (`--lang c` / `ts` / `wat`) |
| **`mpx-cli deploy`** | **build + upload + run** |
| `mpx-cli logs -f` | the robot's own log, live |
| `mpx-cli trace` | plot what a running skill emits |
| `mpx-cli gaits` | the built-in movement catalogue |
| `mpx-cli movements` | every movement, built-in and skill-provided |
| `mpx-cli run --param k=v` | run again, different settings, no rebuild |
| `mpx-cli stop` | end the running skill or behaviour |
| `mpx-cli safe-mode` | autorun disabled itself? this says why |
| `mpx-cli sync` | refresh generated bindings after an ABI change |
| `mpx-cli ls` / `delete` | what is on the robot |
| `mpx-cli publish .` / `install` | share, and install others' |

Every command takes `--ip` / `--port`; set `MPX_HOST` once instead.

Full options: [REFERENCE.md](REFERENCE.md).

---

## The limits

| | |
|---|---|
| Module size | 256 KB |
| Linear memory | 128 KB |
| Run time | 60 s — unless `"behaviour": true` |
| Concurrency | one skill at a time |
| Tick rate | 10–1000 ms; three overruns stops the loop |
| Overlay | ±20° per joint |
| Trace history | 256 samples |
| Joint range | ±135° |
| Walk speed | 200 mm/s |

---

## When it does not work

```bash
mpx-cli doctor      # is the setup right?
mpx-cli logs -f     # what is the robot actually saying?
```

Those two answer most of it. The symptom table is in
[REFERENCE.md](REFERENCE.md#when-something-goes-wrong).

If the SDK behaves differently from what is written here, treat the
documentation as the thing that is wrong, and please report it.

---

**Next:** [MOVEMENT.md](MOVEMENT.md) if you have not read it ·
[REFERENCE.md](REFERENCE.md) when you need an exact name.
