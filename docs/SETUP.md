# Setup

**Get from nothing to a robot that moved because of you.** Ten minutes.

---

## 1. Install

The dev container has everything — Python, the C toolchain, AssemblyScript,
WABT. Open the folder in VS Code and choose **Reopen in Container**.

Otherwise, Python 3.10+ and:

```bash
pip install -e cli
```

Then whichever compiler matches your language. **C is the one to pick** — the
friendly API is C, and so is every example.

| Language | Needs | Where |
|---|---|---|
| **C** | WASI SDK | [releases](https://github.com/WebAssembly/wasi-sdk/releases) → `/opt/wasi-sdk` |
| TypeScript | AssemblyScript | `npm install -g assemblyscript` |
| WAT | WABT | [releases](https://github.com/WebAssembly/wabt/releases) → `/opt/wabt` |

---

## 2. Find the robot

Power it on. It makes a Wi-Fi network called **MPX-Dog** — join it, and the
robot is at **192.168.2.1**. Open that in a browser and you get the control UI.

Write the address down once, in a `.env` beside your project:

```
MPX_HOST=192.168.2.1
```

You should never need to type `--ip` again. If you have put the robot on your
own Wi-Fi instead, use the address it reports there.

---

## 3. Check everything at once

```bash
mpx-cli doctor
```

```
SDK
  ok    headers  /home/you/mpx-sdk/sdk/include  (found by searching upward)
  ok    ABI  v4, 70 host functions

Toolchains
  ok    WASI SDK  20.0

Project
  warn  no manifest.json here
          Not a problem — you are just not standing in a skill.
            mpx-cli init my_move

Robot
  ok    reachable  192.168.2.1:80 — 3 skill(s) installed

Looks good. Try:  mpx-cli deploy
```

One command for every question of the *is it me or is it broken* kind: where the
headers came from, which ABI they describe, which compilers exist, whether your
project agrees, whether the robot answers. Anything wrong prints the fix.

**Run this first whenever something is odd.** It covers nearly every first-hour
problem.

---

## 4. Make it move

```bash
mpx-cli init my_move && cd my_move
mpx-cli deploy
```

```
✅ Compiled my_move.c → my_move.wasm
   📦 Size: 2.1 KB
📤 Uploading to 192.168.2.1:80…
▶️  Running 'my_move.wasm'…
✅ my_move.wasm — ok (2.3s)
```

That is build, upload and run in one command. The robot just moved.

Open `src/my_move.c` and change something. Run `mpx-cli deploy` again. That loop
is the job.

---

## What you got

```
my_move/
├── manifest.json    name, version, and what this skill declares
├── Makefile         a convenience wrapper
├── README.md
└── src/
    └── my_move.c    ← edit this
```

**There is no `include/`, on purpose.** The SDK headers live in exactly one
place and `mpx-cli` points the compiler at them. Vendoring a copy per project is
how a project ends up describing a different ABI than the robot is running —
this repo once had four copies and two had gone stale.

(AssemblyScript and WAT resolve imports by path, so those projects do keep one
generated file. `mpx-cli sync` refreshes it.)

---

## Firmware

Everything here assumes the robot is running **ABI v4** firmware. If host calls
trap immediately, that is the mismatch — `MPX_REQUIRE_ABI()` at the top of your
skill turns it into a clear log line instead of a puzzle.

Flashing is in [internals/flashing.md](internals/flashing.md).

---

**Next:** [MOVEMENT.md](MOVEMENT.md) — how to make the robot do something you
designed.
