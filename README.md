# mpx

**One developer CLI for MPX skills** — scaffold, build, test and publish robot skills
(WASM, the `move` family) and merchant web skills (AWA, the `web` family).

## Install

```bash
pipx install mpx            # recommended, works on Windows/macOS/Linux
```

## Upgrading the tool

The tool ships the skill SDK header (`mpx_tool/commands/resource/move/mpx_host.h`)
inside the package, and `mpx move build` compiles your source against *that* copy.
A firmware release that changes host-function signatures therefore only reaches
your skills after the CLI itself is upgraded — editing an `include/` copy in your
project is not enough, because the build does not use it.

```bash
pipx upgrade mpx                                   # installed from PyPI
pipx install --force /path/to/mpx-tool             # installed from a local checkout
mpx --version                                      # confirm the new version
```

`pipx upgrade mpx` reports `unchanged ... installed from the local source` for a
local checkout, and that is not an error: a local install is only refreshed by
re-running `pipx install --force` on the directory (or `pipx reinstall mpx`).

After upgrading, rebuild every project (`rm -rf build && mpx move build src/<name>.c`);
binaries produced by the previous tool keep the old import types and are not
repaired by re-uploading them. See the next section for the whole procedure.

## Upgrading skills to a new host ABI

The firmware registers each host function as a WAMR native symbol with an exact
signature string — `($i)i`, `(fff)i`, `()i` and so on. WAMR requires the type a
skill *imports* to match that string character for character; a mismatch does not
warn at build time, it fails at runtime on the robot, on the first call:

```
failed to check signature '($i)i' and resolve pointer params for import function (env print)
warning: failed to link import function (env, print)
E wasm_sandbox: WASM execution failed: Exception: failed to call unlinked import function (env, print)
```

Those three lines mean one thing: **the binary was built against an older SDK
header than the firmware implements**. Nothing is wrong with the upload, the
network or the marketplace.

Upgrade procedure:

1. Upgrade the CLI, so the bundled header matches the firmware (previous section).
2. Delete the stale output: `rm -rf build` (an incremental build can keep an old
   object; the import types live in the linked module, not in your source).
3. Rebuild: `mpx move build src/<name>.c`.
4. Confirm the result column changed:
   `mpx move build src/<name>.c --inspect` — every host import must show its
   return type, e.g. `env.print : (i32, i32) -> i32`, not `-> nil`.
5. Upload and run: `mpx move upload build/<name>.wasm` then `mpx move run <name>.wasm`.
6. If it still traps, the firmware and the CLI disagree on the ABI version: call
   `mpx_abi_version()` in the skill (or read it from the firmware source) and
   upgrade whichever side is older. As of host ABI v2, `print`, `robot_gait`,
   `robot_set_config`, `robot_delay_ms`, the `robot_ik_*` family and the other
   setter host functions return `int` (0 or a negative error code) instead of
   `void`.

A v1 binary can never be made to run on v2 firmware and a v2 binary cannot run on
v1 firmware — recompile, do not re-upload. Publish the rebuild so the marketplace
stops serving the old bytes.

## Command surface

```bash
# Account & marketplace (shared)
mpx signup <username>
mpx login <username>
mpx logout
mpx publish [dir]           # reads manifest.json to pick the skill family
mpx search [query]
mpx info <skill_id>
mpx versions <skill_id>
mpx update-manifest [dir]   # edit manifest.json metadata (also: mpx move|web update-manifest)

# Robot skills (WASM)
mpx move init <name> --lang c|wat|ts
mpx move build <src> [--validate] [--inspect]
mpx move upload <x.wasm>
mpx move run <skill>
mpx move list
mpx move delete <skill>

# Web skills (AWA)
mpx web init <domain>
mpx web up                  # start worker + GCS (auto-pull Docker Hub images)
mpx web seed <domain>
mpx web session start <skill_id> --robot <uuid>
mpx web session list | get | action | end
mpx web list
mpx web readme <skill_id>
mpx web delete <domain>
mpx web down
```

## Scaffolding

Both `init` commands follow one contract: same flags, same prompt order, same
slug-collision check, same exit codes, same console summary.

```bash
mpx move init <name> --lang c|wat|ts      # -> Makefile, src/, include/, GUIDE.md
mpx web init <domain> | <slug>@<domain>   # -> manifest.json, skill.js, GUIDE.md
```

Flags shared by both:

```bash
--dir/-d DIR      output directory (default: ./<target>)
--slug/-s SLUG    marketplace slug (default: derived from name/domain)
--title/-t TITLE  marketplace title
--version V       initial version (default: 1.0.0, must be X.Y.Z)
--yes/-y          accept defaults, never prompt
```

On a TTY without `--yes`, both prompt for slug → title → version and warn when the
slug is already taken on the gateway. An existing target directory fails with
exit code `1`.

## Project metadata

Each scaffolded project has a `manifest.json` that `mpx publish` reads:

- **Both families** — `slug`, `title`, `version`, `readme`, `skill_type`,
  `source_language`
- **Web only** — `domain`, `actions`, `capabilities`, `urls`, `timeout`,
  `memoryLimitMB`

The generated `GUIDE.md` documents its family's fields and ends with an
**"Updating this GUIDE and the manifest metadata"** section: the field table, a
checklist for behavior changes, and how to re-publish.

Edit metadata through the CLI rather than by hand:

```bash
mpx update-manifest .        # or: mpx move update-manifest . / mpx web update-manifest .
```

It prompts per field with the current value as the default. For scripted updates
pass `--slug/--title/--version/--readme/--domain`, and `--dry-run` to preview.
Keep the GUIDE prose in sync manually — no generator rewrites it.

## Prerequisites

- Python ≥ 3.10 (stdlib only, no external packages)
- Docker (toolchain image for `mpx move build`; AWA worker + GCS for `mpx web`)

## Design

See `docs/001-consolidated-cli-design.md`.
