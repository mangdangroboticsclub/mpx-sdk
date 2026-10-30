# Consolidated Developer CLI — Design

> **Status:** Draft — for review before implementation
> **Repo:** `mpx-tool` (this repository holds the consolidated CLI and its documentation)
> **Related repos (kept as-is):** `mpx-sdk` (robot/WASM skill SDK), `mpx-cloud-sdk` (AWA/web skill SDK)

## 1. Purpose

Today there are two developer CLIs with overlapping responsibilities:

| Tool | Runtime | Family | Produces | Talks to |
|------|---------|--------|----------|----------|
| `mpx-cli` (in `mpx-sdk/mpx-cli`) | Python (stdlib only) | robot / WASM | `.wasm` skills in C / WAT / AssemblyScript | MPX-Dog robot (ESP32) + marketplace gateway |
| `mpx-awa` (in `mpx-cloud-sdk/mpx-awa`) | Node (stdlib only) | merchant web / AWA | `.js` skills for headless browser (AWA worker/GCS) | AWA worker + GCS emulator + marketplace gateway |

Both share the **same marketplace gateway** (`/v1/auth/*`, `/v1/publish`), the **same account model** (`username~slug` skill IDs), and **structurally identical publish payloads** — they differ only in `skill_type` (`WASM` vs `AWA`) and the target backends (robot vs worker/GCS).

**Goal:** consolidate both into a **single, globally-installable Python CLI** so a developer has exactly one tool (`mpx`) for scaffolding, building, and publishing *either* family of skills — while leaving `mpx-sdk` and `mpx-cloud-sdk` untouched as the source-of-truth for their respective SDK files and templates. The merged CLI lives in **this** repo, `mpx-tool`.

### Terminology (internal names)

To avoid confusion between the two legacy tool names, we introduce two neutral, internal **command families**:

- **`move`** — the robot skill family formerly served by `mpx-cli` (WASM/C/WAT/AssemblyScript skills uploaded to the MPX-Dog robot).
- **`web`** — the merchant web-automation family formerly served by `mpx-awa` (AWA/JS skills run in the headless-browser worker).

These names are *internal/subcommand* identifiers (e.g. `mpx move build …`, `mpx web session …`). The top-level product name is still `mpx`. The legacy names (`mpx-cli`, `mpx-awa`) are retained only as backwards-compatible aliases for a transition period.

---

## 2. Goals & non-goals

### Goals
- **One install.** A single global Python package, distributed via PyPI, installed with `pipx`/`pip` on Windows, macOS, and Linux (see §7).
- **One command surface.** `mpx init/build/publish/login/…` where the target family is selected by subcommand (`move` vs `web`) or by the scaffolded project's declared `skill_type`.
- **Cross-OS, reproducible WASM builds.** The native WASM toolchain (WASI SDK, WABT, AssemblyScript) is never installed on the host; it is delivered through a **Docker toolchain image** so `move` builds behave identically everywhere (§6.1).
- **Reproducible web dev/test backend.** `mpx-awa`'s `web` commands depend on a running **AWA worker + GCS emulator**; these are provided as pinned, long-running containers rather than host installs (§6.2).
- **Reuse, don't rewrite.** Migrate `mpx-awa`'s Node commands into Python and merge them with `mpx-cli`, reusing the stdlib-only HTTP/token/client patterns that already exist in `mpx-cli`.
- Keep `mpx-sdk` and `mpx-cloud-sdk` unchanged as authoritative sources for templates/headers.

### Non-goals
- Not modifying `mpx-sdk` / `mpx-cloud-sdk` internals. They remain upstream SDK packages; `mpx-tool` may *vendor* or *reference* their template/header files at build/packaging time.
- No native code in the Python package (remains pure Python, stdlib-only).
- Not (yet) shipping native Homebrew/winget/MSI packages (see §8 for future work).

---

## 3. High-level architecture

```
┌────────────────────────────  mpx (Python package in mpx-tool)  ────────────────────────────┐
│                                                                                          │
│   mpx CLI (entry: mpx = mpx_tool.cli:main)                                               │
│        │                                                                                 │
│        ├── move …            robot/WASM family (ex mpx-cli)                              │
│        │     init · scaffold · build · validate · upload · run · list · delete           │
│        │                                                                                 │
│        ├── web …             merchant web family (ex mpx-awa)                            │
│        │     init · scaffold · seed · session · readme · list · delete                   │
│        │                                                                                 │
│        └── shared …          marketplace / auth (COMBINED from both)                     │
│              login · signup · logout · publish · search · info · versions                │
│                                                                                          │
└───────────────┬───────────────────────────────────────────────────────────────┘
                │
   ┌────────────▼─────────────┐     ┌───────────────────────────────────────────┐
   │ 1) move TOOLCHAIN image  │     │ 2) web RUNTIME image (+ GCS emulator)    │
   │ (WASI SDK, WABT, ASC)    │     │    AWA worker: Express + Chromium + V8   │
   │ ephemeral · one-shot     │     │    isolates · long-running services      │
   │ run only when compiling  │     │    (dev/test backend for web family)     │
   └──────────────┬───────────┘     └──────────────────────┬────────────────────┘
                  │                                        │
        ┌─────────▼─────────┐                  ┌───────────▼──────────┐
        │ MPX-Dog robot     │                  │ Marketplace gateway  │
        │ (move deploy)     │                  │ /v1/auth/* /v1/publish│
        └───────────────────┘                  └──────────────────────┘
```

Two distinct Docker artifacts serve the two families (see §6): a short-lived **`move` toolchain image** used only during compilation, and a set of long-running **`web` runtime containers** (AWA worker + GCS emulator) that the developer starts for local dev/test.

**Key idea:** the two families share the *account/marketplace* plumbing (`login`, `publish`, `search`, `info`, `versions`) and differ only in (a) what they scaffold, (b) which artifact they build/publish, and (c) which runtime backend they target at deploy/test time. Importantly, the two families lean on **two different Docker artifacts**: `move` needs only a *compiler* image at build time, while `web` needs a *runtime* backend (headless-browser worker + object storage) for local testing.

---

## 4. Proposed package layout (`mpx-tool`)

```
mpx-tool/
├── pyproject.toml               # single source of truth; entry `mpx`
├── README.md
├── docs/
│   └── 001-consolidated-cli-design.md   # this doc
├── src/
│   └── mpx_tool/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py               # argparse dispatch + family routing
│       ├── config.py            # env vars, defaults, gateway locations
│       ├── sdk/
│       │   ├── gateway.py       # marketplace gateway HTTP client (pub/sub/auth)
│       │   ├── auth.py          # token/state file management (unified)
│       │   ├── robot.py         # MPX-Dog robot HTTP client (move family)
│       │   ├── awa_worker.py    # AWA worker HTTP client (web family)
│       │   ├── gcs.py           # GCS-emulator client (web family seed/list/delete)
│       │   └── docker.py        # auto-pull/run registry helper for images (move + web)
│       ├── commands/
│       │   ├── auth.py          # signup / login / logout (shared)
│       │   ├── publish.py       # publish (shared; detects skill_type)
│       │   ├── search.py / info.py / versions.py   # marketplace browse (shared)
│       │   ├── move/
│       │   │   ├── init.py      # ex mpx-cli init (C/WAT/TS)
│       │   │   ├── build.py     # ex mpx-cli build → docker toolchain
│       │   │   ├── upload.py / run.py / list_.py / delete.py
│       │   └── web/
│       │       ├── init.py      # ex mpx-awa init (JS skill)
│       │       ├── seed.py / list_.py / delete.py / readme.py
│       │       └── session.py
│       │   └── resource/        # vendored templates + SDK headers (see §4.1)
│       │       ├── move/        # copied from mpx-sdk at packaging: mpx_host.h, mpx_env.ts,
│       │       │                #   *.template, host_functions*.md, GUIDE templates
│       │       └── web/         # copied from mpx-cloud-sdk: skill.js, manifest.json, GUIDE.md
│       │                        #   templates + handlers/helpers
```

### 4.1 Template sourcing

We **do not edit** `mpx-sdk` or `mpx-cloud-sdk`. Their template/header files are **copied into `mpx_tool/commands/resource/` and kept in the CLI package for now** (Decision #6). Origin is recorded in a `SOURCE` manifest so a later automated sync from the upstream repos can be added without rework.

---

## 5. Command surface & migration mapping

### 5.1 Marketplace & auth (shared, consolidated)

These commands currently exist in **both** tools and hit the **same gateway**. We keep one implementation.

| Unified command | Legacy `mpx-cli` | Legacy `mpx-awa` | Notes |
|-----------------|------------------|------------------|-------|
| `mpx login` | `mpx-cli login` | `mpx-awa login` | same `/v1/auth/login` |
| `mpx signup` | `mpx-cli signup` | `mpx-awa signup` | same `/v1/auth/signup` |
| `mpx logout` | `mpx-cli logout` | `mpx-awa logout` | |
| `mpx publish <dir>` | `mpx-cli publish <dir>` | `mpx-awa publish <domain>` | **skill_type inferred from the project's manifest** (WASM vs AWA). One code path. |
| `mpx search` | `mpx-cli search` | — | marketplace browse |
| `mpx info` | `mpx-cli info` | — | |
| `mpx versions` | `mpx-cli versions` | — | |
| `mpx update-manifest [dir]` | — | — | **new**: interactive editor for `manifest.json` (`slug`/`title`/`version`/`readme`/`domain`), plus `--slug/--title/--version/--readme/--domain/--dry-run` for scripts. Also registered as `mpx move update-manifest` and `mpx web update-manifest`. |

`publish` is the highest-leverage merge: the wire payload is already identical except `skill_type`/`source_language`, which we read from each scaffold's manifest. Semver-bump-on-`409` logic (already in `mpx-cli`) is reused for both families. Semver parsing lives in `mpx_tool/manifest.py` so `init`, `publish`, and `update-manifest` validate identically.

### 5.2 `mpx move …` — robot family (ex `mpx-cli`)

| Unified | Legacy `mpx-cli` |
|---------|------------------|
| `mpx move init <name> --lang c\|wat\|ts` | `init` |
| `mpx move build <src>` | `build` (runs in Docker toolchain) |
| `mpx move upload <wasm>` | `upload` |
| `mpx move run <skill>` | `run` |
| `mpx move list` | `list` (skills on device) |
| `mpx move delete <skill>` | `delete` |
| (shared) `mpx login/publish` | auth/publish (WASM) |

### 5.3 `mpx web …` — merchant web family (ex `mpx-awa`)

| Unified | Legacy `mpx-awa` |
|---------|------------------|
| `mpx web init <domain>` | `init` |
| `mpx web seed <domain>` | `seed` (GCS) |
| `mpx web list` | `list` (GCS) |
| `mpx web delete <domain>` | `delete` (GCS) |
| `mpx web readme <domain>` | `readme` |
| `mpx web session start\|list\|get\|action\|end` | `session` |
| `mpx web up` / `mpx web down` | (runtime containers) |
| (shared) `mpx login/publish` | auth/publish (AWA) |

### 5.4 Backwards-compatible aliases (transitional)

To avoid breaking existing scripts, the merged CLI accepts legacy entry names during a transition window:

```bash
mpx-cli build ...      # aliases to: mpx move build ...
mpx-awa publish ...    # aliases to: mpx web publish ...   (or mpx publish)
```

These are thin re-dispatch shims only; they are removed once the migration cutover is complete.

### 5.5 Suggested `--help` model

Family is chosen by the subcommand name, not a global flag:

```
mpx                         # top-level help (move, web, login, publish, ...)
mpx move --help             # robot development: init/build/upload/run/list/delete
mpx web --help             # incl. web up / web down (bring up the worker + GCS, auto-pull)
mpx publish --help          # auto-detects family from ./manifest.json in the target dir
```

Where a project is family-agnostic (both produce `manifest.json` with `skill_type`), `mpx publish` inspects that field and behaves accordingly. `mpx init` requires an explicit family (`mpx move init` vs `mpx web init`).

### 5.6 Command API — finalized naming (Decision #4)

Decision: the robot toolchain flow uses one uniform **`mpx move …`** grouper (short), including **`mpx move list`**. Keeping everything under a single grouper means a future rename is a one-place change rather than mixing `move` and `robot`. Verbs `build`, `seed`, `session` are kept.

**Shared (account / marketplace):**

```bash
mpx login                     # authenticate (stores one unified token)
mpx signup                    # create account
mpx logout
mpx publish                   # publish ./project — auto-detects skill_type from manifest
mpx search [<query>]          # browse marketplace
mpx info <skill_id>
mpx versions <skill_id>
```

**Robot skills:**

```bash
mpx move init <name> --lang c|wat|ts
mpx move build <src>          # WASM build in the toolchain image
mpx move upload <x.wasm>      # push the compiled skill to the robot
mpx move run <skill>
mpx move list                 # list skills currently on the robot device
mpx move delete <skill>
```

**Web/merchant skills — `mpx web …`:**

```bash
mpx web init <domain>
mpx web seed <domain>         # upload to GCS for local test
mpx web session <id> ...      # session start/get/action/end
mpx web list                  # list seeded web skills
mpx web delete <domain>
mpx web readme <domain>
mpx web up | mpx web down     # start/stop the worker + GCS runtime (auto-pull)
```

**Naming rules (finalized):**
- The robot toolchain flow uses the uniform `move` grouper (`mpx move …`), including `mpx move list` — one group means future renames are a single source change.
- Where a verb would otherwise collide across families (e.g. `list`/`delete`), the grouper disambiguates: `mpx move list` vs `mpx web list`, `mpx move delete` vs `mpx web delete`.
- Keep tokens short and stable for automation/scripts.

### 5.7 `init` parity & the project metadata contract (Decision #8)

`mpx move init` and `mpx web init` are one implementation contract with a
family-specific file payload, so a developer learning one already knows the other:

| Aspect | Behavior (both families) |
|--------|--------------------------|
| Flags | `--dir`, `--slug`, `--title`, `--version`, `--yes` (move also `--lang c\|wat\|ts`) |
| Prompts | slug → title → version, current/derived value as default; skipped when `--yes` or stdin is not a TTY |
| Validation | slug collision check against the gateway (`check_slug`), semver required for `version` |
| Existing dir | `❌ Directory "…" already exists.` and exit code `1` |
| Output | `✓ Created …` per file, then Configuration / Next steps / Metadata summary |
| Manifest | `slug`, `title`, `skill_type`, `source_language`, `version`, `readme` (+ web-only `domain`, `actions`, `capabilities`, `urls`, `timeout`, `memoryLimitMB`) |
| Docs | move and web → `GUIDE.md`. Both carry the generated **"Updating this GUIDE and the manifest metadata"** section (field table + change checklist + `update-manifest` usage) |

Shared code lives in `src/mpx_tool/commands/scaffold.py` (prompts, resource loading,
file writer, slug derivation/collision check, summary printer) and
`src/mpx_tool/manifest.py` (semver parsing, manifest read/write, generated doc
section). The scaffolders must not duplicate any of it.

---

## 6. Container strategy (two distinct artifacts)

Docker is used in **two very different ways** for the two families. Treat them as separate artifacts with separate lifecycles — combining them into one image would conflate an ephemeral build tool with a long-running service.

### 6.1 `move` toolchain image (compiler — ephemeral)

The native C→WASM toolchain is a heavy, OS-specific dependency. Per decision, we ship it as a **reusable Docker image** used only to compile — never installed on the host.

- **Image spec** is derived from the existing `mpx-sdk/.devcontainer/Dockerfile`, which already pins WASI SDK 24, WABT 1.0.41, Node 22 + `assemblyscript` (npm).
- **Multi-arch:** build/publish for `linux/amd64` and `linux/arm64` (`docker buildx`) so Apple Silicon/ARM behave identically; Docker Desktop handles Windows/macOS.
- **Distributed on Docker Hub** (see §6.4) — customers `pull` it by pinned tag; they never build it locally.
- `mpx move build` compiles **inside the container** via a bind-mounted working directory: `docker run --rm -v "$PWD":/work -w /work <image> clang --target=wasm32-wasip1 …`. If the pinned image is not present locally, `build` **auto-pulls** it from Docker Hub (see §6.4/§6.5).
- **Fallback:** if `docker` is unavailable, fall back to locally-detected toolchains via the existing `WASI_CC`/PATH/`/opt` detection, so offline/no-Docker users are not blocked.

### 6.2 `web` runtime image + GCS emulator (dev/test services — long-running)

`mpx-awa`'s `web` functionality is **not just a compiler** — its `seed`/`session` commands talk to a running **AWA worker** (a Node/Express server that launches Chromium and runs skills in V8 isolates) and a **GCS object store** (an emulator locally, real GCS in production). To test a web skill locally, the developer must run these services.

**Source of truth** for this runtime is the existing `mpx-cloud-sdk` infrastructure, which we do **not** modify:
- `mpx-cloud-sdk/Dockerfile` — the AWA **worker image** (multi-stage: `node:20-slim`, Chromium, Playwright, `isolated-vm`).
- `mpx-cloud-sdk/docker-compose.yml` — starts `awa-worker` (mapped to host port `9808`) and joins an external `mpx-shared-mesh` network shared with a separately-run **GCS emulator** (`localhost:4443`, e.g. `~/mpx-gcp-cloudstorage`).

**How `mpx_tool` consumes it:**
- The `web` commands (`seed`, `list`, `delete`, `readme`, `session`) already speak HTTP to the worker and GCS; the containerized runtime is *separate* from the CLI. So the CLI and its documentation must **reference and orchestrate** these images, not rebuild them.
- **`mpx web up`** auto-pulls the pinned worker + GCS images from Docker Hub, then starts them via `docker compose up -d` with the correct env (ports `9808`/`4443`, `MPX_GATEWAY_URL`, bucket, provider/proxy vars); **`mpx web down`** runs `docker compose down` (see §6.5).
- Long-running services (worker, GCS) are **not** something the pure-Python CLI should embed; they stay containers referenced by name + Docker Hub tag (§6.4), started on demand via `mpx web up`.

### 6.3 Relationship to `mpx-sdk` / `mpx-cloud-sdk`

Both Docker artifacts are derived from those two repos but **kept as upstream sources of truth** (§2). `mpx-tool` pins image tags/versions and documents how to build or pull them; it does not modify their Dockerfiles.

### 6.4 Image registry & tagging (Docker Hub)

Images are **built once, published to Docker Hub, and pulled by customers**. Developers never build the images locally; the CLI references them by registry + tag and `docker pull`s as needed.

Proposed namespaces (confirm in Decision #8):

| Image | Docker Hub reference (proposed) | Lifecycle | Based on |
|-------|---------------------------------|-----------|----------|
| `move` toolchain (compiler) | `mangdang/mpx-move-toolchain:<semver>` | ephemeral | `mpx-sdk/.devcontainer/Dockerfile` |
| `web` AWA worker | `mangdang/mpx-web-worker:<semver>` | long-running | `mpx-cloud-sdk/Dockerfile` |
| GCS emulator | (external upstream — e.g. a pinned `fake-gcs-server` image or existing `~/mpx-gcp-cloudstorage` image) | long-running | external repo |

**Tagging rules:**
- Immutable semver tags (e.g. `mangdang/mpx-move-toolchain:24.1.0`) map 1:1 to the pinned compiler/worker versions.
- A `:latest` convenience tag may exist but is never used in CI or pinned docs.
- The Python package records the expected image URI + tag per command so the CLI always pulls/uses the exact same artifact.

**Publication plumbing:** a CI `docker buildx build --push --platform linux/amd64,linux/arm64` step publishes both images to Docker Hub on release (see §10).

### 6.5 Image lifecycle (auto-pull — no orchestration subcommand)

There is **no dedicated container-orchestration subcommand** (a `mpx services` layer was considered and dropped). Docker images are pulled **automatically, on demand**, by whichever command needs them:

- **`move`** → the toolchain is stateless and one-shot. `mpx move build` **auto-pulls** the pinned compiler image from Docker Hub if it is not already present locally, runs the compile inside it (`docker run --rm …`), and exits. There is nothing to start/stop — no daemon, no running state — so no `up`/`down` exists for it.
- **`web`** → the worker + GCS are genuine long-running services, so the `web` family exposes lightweight bring-up/tear-down commands (**`mpx web up`** / **`mpx web down`**). Both **auto-pull** the pinned images from Docker Hub first, then `web up` runs `docker compose up -d` (exposing `9808`/`4443`) and `web down` runs `docker compose down`.

This keeps the mental model simple: images appear on demand, and there is no separate “services” concept to reason about.

---

## 7. Distribution & global install (all three OSes)

The package is **pure Python, stdlib-only**, so there is no native compilation step and the wheel is identical everywhere.

**Canonical install (recommended) — `pipx`:**

```bash
# Windows / macOS / Linux — identical command
pipx install mpx
```

`pipx` isolates the package in its own venv but exposes the `mpx` console script globally; it sidesteps PEP-668 (externally-managed system Pythons on modern Linux) and never pollutes system site-packages.

**Alternative — plain `pip` (user or venv):**

```bash
pip install --user mpx        # older setups
python -m pip install mpx      # inside an activated venv
```

**Per-OS prerequisites (only two things to install before `mpx`):**

| OS | Python 3.10+ | Docker (toolchain image for `mpx move build`, and AWA worker + GCS for `mpx web`) |
|----|--------------|-----------------------------------------------|
| Windows | `winget install Python.Python.3.12` (check “Add to PATH”) or python.org | Docker Desktop |
| macOS | `brew install python@3.12` (prefer over Apple’s `/usr/bin/python3`) | Docker Desktop / colima |
| Linux | `apt install python3-pip` (or `python3-venv`) / distro equivalent | Docker Engine |

### 7.1 Docker usage & auto-pull lifecycle (clarified)

Docker is a prerequisite for both families, but there is no separate orchestrator — images are auto-pulled on demand:

| Docker usage | Family | When | Driven by | Lifecycle |
|--------------|--------|------|-----------|-----------|
| Pull + run **toolchain image** to compile (auto-pull if absent) | `move` | at build time | `mpx move build` | ephemeral, one-shot |
| Pull + run **AWA worker** + **GCS emulator** for local dev/test | `web` | at dev/test time | `mpx web up` / `mpx web down` | long-running services |

So using each family is straightforward: `mpx move build` handles its own image pull; before web dev/test, run `mpx web up` (auto-pulls worker + GCS), then `mpx web down` to stop. Everything is reproducible because images are pinned on Docker Hub.

---

## 8. Future work (explicitly out of scope for v1)

- Native packaging: Homebrew formula (`brew install mangdang/mpx/mpx`), `winget`/MSI manifest, OS packages.
- Publishing `mpx-tool` itself (bootstrap from source) as the single canonical distribution point.
- Interactive `mpx configure` to record the canonical default gateway and default robot host.

---

## 9. Decisions (resolved)

1. **Top-level name.** `mpx` is the PyPI package name *and* the console command / entry point.
2. **Default gateway URL.** `http://skills.mangdang.org:8080`, overridable via `MPX_GATEWAY_URL`.
3. **Auth / state files.** Unify into a **single** session token + state file set (no per-family split). Existing `~/.mpx-cli-token` / `~/.mpx-awa-token` credentials are migrated once on first run.
4. **Command naming.** Confirmed: the robot toolchain flow lives uniformly under `mpx move …` (including `mpx move list`) — one grouper so a future rename is a single change. Verbs `build`, `seed`, `session` are kept as-is. See §5.6. Legacy `mpx-cli` / `mpx-awa` aliases are retained only during the transition window.
5. **Porting source.** The redundant `mpx-awa-service` copy is removed; the `web` family is ported from the canonical `mpx-cloud-sdk/mpx-awa`.
6. **Templates.** Copy the `resource/` SDK/template files into the CLI package and keep them there for now (automated upstream sync can be added later).
7. **Web runtime topology.** Reuse the upstream worker + GCS `docker-compose`; pull the AWA worker + GCS images from Docker Hub (see §6.4 / §6.5).
8. **Image names.** Flexible until the first push. Tentative names: `mangdang/mpx-move-toolchain` and `mangdang/mpx-web-worker` — confirm before publishing; GCS emulator image pinned separately.
9. **Orchestration.** Automatic — there is no `services`/orchestration subcommand. `mpx web up` / `mpx web down` pull + manage the worker + GCS containers; `mpx move build` auto-pulls its toolchain image on demand.

---

## 10. Migration path (incremental)

Proposed sequence so each step is independently shippable and testable:

1. **Bootstrap `mpx-tool`** package with `pyproject.toml`, `mpx` entry, minimal `cli.py`.
2. **Port auth/marketplace plumbing** (shared): unify `gateway.py`, `auth.py`; add `skill_type`/`source_language` parameters to `publish`; reconcile token/gateway defaults (Decision #2/#3).
3. **Define image registry** (`mangdang/mpx-move-toolchain`, `mangdang/mpx-web-worker`) + CI `docker buildx --push` for `linux/amd64,linux/arm64` (Decision #8).
4. **Implement auto-pull helpers** (`sdk/docker.py`): pull-and-run used by `move build` and by `web up`; no orchestration subcommand (Decision #9).
5. **Port `move` family** from `mpx-cli` (init/build/upload/run/list/delete) with `build` → auto-pull + run of the toolchain image.
6. **Port `web` family** from `mpx-awa` (init/seed/list/delete/readme/session) plus `sdk/gcs.py`, `sdk/awa_worker.py`.
7. **Add `web up` / `web down`** to manage the worker + GCS containers (auto-pull from Docker Hub).
8. **Vendor templates** into `commands/resource/` and add sync manifest.
9. **Wire aliases** (`mpx-cli`/`mpx-awa` transitional re-dispatch).
10. **Distribute**: publish the Python wheel to PyPI + push the Docker images to Docker Hub; document `pipx install mpx` across Windows/macOS/Linux (this design doc’s §7).
11. Remove transitional aliases after cutover.

---

## 11. Summary

A single stdlib-only Python package in `mpx-tool` gives developers one global `mpx` CLI covering both **move** (robot/WASM) and **web** (AWA/JS) skill families, sharing one marketplace/auth implementation. Portability is guaranteed by a pinned, multi-arch Docker strategy made of **two distinct artifacts**: an ephemeral **`move` compiler toolchain image**, and long-running **`web` runtime containers** (AWA worker + GCS emulator). `mpx-sdk` and `mpx-cloud-sdk` remain untouched as upstream sources of truth.
