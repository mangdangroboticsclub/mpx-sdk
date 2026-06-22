# MPX-SDK — Minipupper Skill Development Kit

**Build, deploy, and run WebAssembly skills on MangDang Minipupper/MPX quadruped robots.**

This SDK provides `mpx-cli`, a cross-platform CLI tool for developing robot behaviours in **C/C++**, **WebAssembly Text (WAT)**, or **AssemblyScript (TypeScript)**, compiling them to `.wasm`, and uploading them via Wi-Fi to the robot's ESP32-S3 firmware over HTTP.

---

## Repository Structure

```
mpx-cli/                          # Python package (install via pip)
├── pyproject.toml
└── src/mpx_cli/
    ├── cli.py                    # Argument parser & dispatch
    ├── commands/
    │   ├── init.py               # Project scaffolding
    │   ├── build.py              # WASM compilation + static analysis
    │   ├── upload.py             # HTTP upload to robot
    │   ├── run.py                # Remote execution
    │   ├── list_skills.py        # List installed skills
    │   └── delete.py             # Remove a skill
    └── sdk/
    │   ├── connection.py         # Robot HTTP client (urllib only)
    │   ├── toolchain.py          # Toolchain detection & compilation
    │   ├── mpx_host.h            # C host function declarations
    │   └── mpx_env.ts            # AssemblyScript host function declarations
    └── templates/
        ├── skill.c               # C skill template
        ├── skill.wat             # WAT skill template
        └── skill.ts              # AssemblyScript skill template

examples/
├── hello-wasm/                   # Minimal C + WAT examples
└── robot-demo/                   # Full gait sequence demo (C)
```

---

## Quick Start (Dev Container — Recommended)

Open this repo in VS Code and **Reopen in Container**. The dev container includes Python 3.12 and all three WASM toolchains pre-installed. The CLI is installed automatically via `postCreateCommand`.

```bash
# Verify everything is ready
mpx-cli build --show-toolchains

# Scaffold a new skill
mpx-cli init my-skill --lang c

# Build
mpx-cli build my-skill/src/my-skill.c -o my-skill/build/my-skill.wasm --validate

# Upload & run (when connected to robot AP: 192.168.2.1)
mpx-cli upload my-skill/build/my-skill.wasm --ip 192.168.2.1
mpx-cli run my-skill.wasm --ip 192.168.2.1

# List installed skills
mpx-cli list --ip 192.168.2.1
```

---

## Installing Outside the Dev Container

If you're not using the dev container, install the toolchains manually for your language of choice.

### 1. Install `mpx-cli`

```bash
# Python ≥ 3.10 required — no external packages (stdlib only)
pip install -e mpx-cli/

# Verify
mpx-cli --version
```

### 2. Install Toolchain(s)

Pick the toolchain(s) for your target language:

#### C / C++ — WASI SDK

```bash
export WASI_VERSION=24
wget https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-${WASI_VERSION}/wasi-sdk-${WASI_VERSION}.0-x86_64-linux.tar.gz
tar xzf wasi-sdk-${WASI_VERSION}.0-x86_64-linux.tar.gz
sudo mv wasi-sdk-${WASI_VERSION}.0-x86_64-linux /opt/wasi-sdk
export PATH="/opt/wasi-sdk/bin:$PATH"

# Or set WASI_CC env var instead of adding to PATH
export WASI_CC=/opt/wasi-sdk/bin/clang
```

**macOS (ARM/x64):** Replace `x86_64-linux` with `x86_64-macos` or `aarch64-macos`.

#### WebAssembly Text (WAT) — WABT

```bash
# Debian/Ubuntu
sudo apt install wabt

# macOS
brew install wabt

# Or manual install
export WABT_VERSION=1.0.41
wget https://github.com/WebAssembly/wabt/releases/download/${WABT_VERSION}/wabt-${WABT_VERSION}-linux-x64.tar.gz
tar xzf wabt-${WABT_VERSION}-linux-x64.tar.gz
sudo mv wabt-${WABT_VERSION} /opt/wabt
export PATH="/opt/wabt/bin:$PATH"
```

#### AssemblyScript (TypeScript) — `asc`

```bash
# Requires Node.js 16+
npm install -g assemblyscript
```

### 3. Verify

```bash
mpx-cli build --show-toolchains
```

Each detected toolchain is shown with a green checkmark. Missing toolchains are flagged — you only need the ones matching your source language.

---

## Dev Container Contents

The `.devcontainer/` provides a reproducible environment with:

| Package | Version | Purpose |
|---------|---------|---------|
| Python | 3.12-slim-bookworm | Runtime for `mpx-cli` |
| Node.js | 22.x | AssemblyScript compiler host |
| WASI SDK | 24 | C/C++ → WASM (`clang --target=wasm32-wasip1`) |
| WABT | 1.0.41 | WAT → WASM (`wat2wasm`) |
| AssemblyScript | latest (npm) | TypeScript → WASM (`asc`) |

VS Code extensions (`ms-python.python`, `dtsvet.vscode-wasm`, `ms-vscode.cpptools-extension-pack`) are included automatically.

---

## Commands

| Command | Description |
|---------|-------------|
| `init <name> --lang c\|wat\|ts` | Scaffold project with Makefile, SDK headers, and template source |
| `build <source> [-o output] [--validate] [--inspect]` | Compile `.c`/`.wat`/`.ts` → `.wasm` |
| `upload <wasm_file> [--ip] [--port]` | Upload skill to robot (`POST /v1/skills/upload`) |
| `run <skill_name> [--ip] [--port]` | Execute a skill on the robot |
| `list [--ip] [--port] [--all]` | List installed skills (alias: `ls`) |
| `delete <name> [--ip] [--port] [-y]` | Delete a skill from the robot |

---

## Supported Languages

| Language | Toolchain | Extension |
|----------|-----------|-----------|
| C / C++ | WASI SDK (`clang` → `wasm32-wasip1`) | `.c`, `.cc`, `.cpp` |
| WebAssembly Text | WABT (`wat2wasm`) | `.wat` |
| AssemblyScript | `asc` (npm) | `.ts` |

The `build` command auto-selects the compiler based on file extension.

---

## Build Validation

`mpx-cli build` runs mandatory static analysis before allowing deployment:

1. **Entry point export check** — verifies the binary exports `on_start` (the sandbox entry hook)
2. **Footprint limit** — rejects binaries exceeding **128 KB** (WAMR heap allocation maximum)

_Note_: File size limit is subject to change

---

## Host Functions

Skills communicate with the robot via host functions registered under the `"env"` module. Declared in [`mpx_host.h`](mpx-cli/src/mpx_cli/sdk/mpx_host.h) (C) and [`mpx_env.ts`](mpx-cli/src/mpx_cli/sdk/mpx_env.ts) (AssemblyScript).

| Category | Functions |
|----------|-----------|
| Logging | `print(ptr, len)` |
| Gaits | `robot_gait(name)` — `"advance"`, `"jump"`, `"turnL"`, `"turnR"`, `"step"`, `"back"`, `"left"`, `"right"`, `"init"`, `"none"`, `"roll"`, `"pitch"`, `"stretch"`, `"twerk"`, `"jumpfwd"` |
| Config | `robot_set_config(period, height, up_height, stride, tilt)`, getters for each |
| Servo | `robot_set_servo_angle(id, centideg)`, `robot_flush()`, `robot_set_servo_speed()`, `robot_read_position()` |
| Calibration | `robot_set_offset()`, `robot_get_offset()`, `robot_ping_servo()` |
| Utility | `robot_delay_ms(ms)` — only reliable way to pause (busy-loops run at near-zero wall time in the interpreter) |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MPX_HOST` | `192.168.2.1` | Robot IP address |
| `MPX_PORT` | `80` | Robot HTTP API port |

---

## Examples

```bash
# Minimal C skill
mpx-cli build examples/hello-wasm/src/test_skill.c --validate

# Minimal WAT skill
mpx-cli build examples/hello-wasm/src/test_skill.wat --validate

# Full robot demo (gait sequence)
mpx-cli build examples/robot-demo/src/robot_skill.c --validate --inspect
```

## Robot API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/skills/list` | List installed `.wasm` skills |
| `POST` | `/v1/skills/run` | Execute a skill |
| `POST` | `/v1/skills/upload?name=<fn>` | Upload a `.wasm` (raw binary, max 256 KB) |
| `GET` | `/v1/fs/list` | List all files on LittleFS |
| `GET` | `/v1/fs/info` | Filesystem usage |
| `POST` | `/v1/fs/delete` | Delete a file |
| `GET` | `/v1/robot/status` | Current robot state |
| `POST` | `/v1/robot/gait` | Set gait mode |
| `POST` | `/v1/robot/config` | Update robot config |

---

## Requirements

- **Python ≥ 3.10** (no external packages — stdlib only)
- **WASI SDK**, **WABT**, or **asc** (depending on your source language — see install instructions above)
- **MPX-Dog robot** running firmware with the HTTP API

## License

[Apache 2.0](LICENSE)