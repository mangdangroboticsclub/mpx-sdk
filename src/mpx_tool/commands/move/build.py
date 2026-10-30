"""mpx move build — compile C/WAT/TS sources to WASM.

Compilation runs inside the pinned Docker toolchain image
(``mangdang/mpx-move-toolchain``); the image is auto-pulled on first
use. If Docker is unavailable, we fall back to locally-detected
toolchains (WASI_CC/clang, wat2wasm, asc).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from mpx_tool.config import MOVE_TOOLCHAIN_IMAGE
from mpx_tool.sdk.docker import DockerError, docker_available, ensure_image, run_image

# ── Local toolchain detection (fallback) ─────────────────────────

def _find_binary(candidates: list[str]) -> str | None:
    for cand in candidates:
        if cand and os.path.isfile(cand):
            return cand
    for cand in candidates:
        resolved = shutil.which(cand or "")
        if resolved:
            return resolved
    return None


def _detect_cc() -> str | None:
    return _find_binary([os.environ.get("WASI_CC", ""), "/opt/wasi-sdk/bin/clang", "clang"])


def _detect_wat2wasm() -> str | None:
    return _find_binary(["/opt/wabt/bin/wat2wasm", "wat2wasm"])


def _detect_asc() -> str | None:
    return _find_binary(["asc"])


def detect_all() -> dict[str, str | None]:
    return {
        "wasi": _detect_cc(),
        "wabt": _detect_wat2wasm(),
        "asc": _detect_asc(),
    }


# ── CLI parser ───────────────────────────────────────────────────

def add_move_build_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("build", help="Compile a C/WAT/TS source file to .wasm")
    p.add_argument("source", nargs="?", help="Source file (.c, .wat, .ts)")
    p.add_argument("-o", "--output", default=None, help="Output .wasm path (default: build/<name>.wasm)")
    p.add_argument("--validate", action="store_true", help="Run wasm-validate on the output")
    p.add_argument("--inspect", action="store_true", help="Show imports/exports via wasm-objdump")
    p.add_argument("--show-toolchains", action="store_true", help="List detected toolchains and exit")
    p.add_argument(
        "--local",
        action="store_true",
        help="Use locally-installed toolchains instead of the Docker image",
    )


# ── Build implementation ─────────────────────────────────────────

def _default_build_output(source: Path) -> Path:
    return source.parent.parent / "build" / f"{source.stem}.wasm"


def _rel_path(path: Path, cwd: Path) -> str:
    """Path relative to cwd using POSIX separators, or absolute if outside.

    The result is embedded into container-side paths like ``/work/<rel>``
    and handed to Linux tools (clang/wat2wasm/asc), so it must always use
    forward slashes even on Windows (where ``Path`` uses backslashes).
    """
    try:
        return path.resolve().relative_to(cwd).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _compile_in_docker(source: Path, output: Path, cwd: Path) -> None:
    ensure_image(MOVE_TOOLCHAIN_IMAGE)

    ext = source.suffix.lower()
    rel_src = _rel_path(source, cwd)
    rel_out = _rel_path(output, cwd)
    work_src = f"/work/{rel_src}"
    work_out = f"/work/{rel_out}"

    if ext in (".c", ".cc", ".cpp"):
        args = [
            "--target=wasm32-wasip1",
            "-nostartfiles",
            "-Wl,--no-entry",
            "-Wl,--export=on_start",
            "-Wl,--import-undefined",
        ]
        # Auto-add -I flags for nearby include/ directories
        seen: set[str] = set()
        for candidate in [
            source.parent / "include",
            source.parent.parent / "include",
            cwd / "include",
        ]:
            resolved = candidate.resolve()
            inc = _rel_path(resolved, cwd)
            if resolved.is_dir() and inc not in seen:
                args.append(f"-I/work/{inc}")
                seen.add(inc)
        args += ["-o", work_out, work_src]
        binary = "clang"
    elif ext == ".wat":
        args = [work_src, "-o", work_out]
        binary = "wat2wasm"
    elif ext == ".ts":
        args = [work_src, "--importMemory", "--exportRuntime", "--outFile", work_out]
        binary = "asc"
    else:
        print(f"❌ Unsupported extension '{ext}' — use .c, .cc, .cpp, .wat, or .ts")
        raise SystemExit(1)

    output.parent.mkdir(parents=True, exist_ok=True)
    run_image(MOVE_TOOLCHAIN_IMAGE, [binary, *args], workdir="/work", cwd=str(cwd))


def _run_local(cmd: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stderr or proc.stdout)
    except FileNotFoundError:
        return -1, "command not found"
    except subprocess.TimeoutExpired:
        return -1, "timed out"


def _compile_local(source: Path, output: Path, cwd: Path) -> None:
    ext = source.suffix.lower()
    output.parent.mkdir(parents=True, exist_ok=True)

    if ext in (".c", ".cc", ".cpp"):
        cc = _detect_cc()
        if not cc:
            print("❌ WASI SDK not found — install clang for wasm32 or use the Docker image")
            raise SystemExit(1)
        cmd = [
            cc,
            "--target=wasm32-wasip1",
            "-nostartfiles",
            "-Wl,--no-entry",
            "-Wl,--export=on_start",
            "-Wl,--import-undefined",
            "-o", str(output),
        ]
        for candidate in [source.parent / "include", source.parent.parent / "include", cwd / "include"]:
            if candidate.is_dir():
                cmd.extend(["-I", str(candidate)])
        cmd.append(str(source))
    elif ext == ".wat":
        wat2wasm = _detect_wat2wasm()
        if not wat2wasm:
            print("❌ WABT (wat2wasm) not found")
            raise SystemExit(1)
        cmd = [wat2wasm, str(source), "-o", str(output)]
    elif ext == ".ts":
        asc = _detect_asc()
        if not asc:
            print("❌ AssemblyScript compiler (asc) not found")
            raise SystemExit(1)
        cmd = [asc, str(source), "--importMemory", "--exportRuntime", "--outFile", str(output)]
    else:
        print(f"❌ Unsupported extension '{ext}' — use .c, .cc, .cpp, .wat, or .ts")
        raise SystemExit(1)

    rc, err = _run_local(cmd)
    if rc != 0:
        print(f"❌ Compilation failed (exit code {rc})")
        if err:
            print(err)
        raise SystemExit(1)


def _validate(output: Path, cwd: Path, use_docker: bool) -> None:
    rel_out = f"/work/{_rel_path(output, cwd)}"
    if use_docker:
        ensure_image(MOVE_TOOLCHAIN_IMAGE)
        run_image(MOVE_TOOLCHAIN_IMAGE, ["wasm-validate", rel_out], workdir="/work", cwd=str(cwd))
        print(f"✅ {output.name} is valid")
    else:
        wv = _find_binary(["/opt/wabt/bin/wasm-validate", "wasm-validate"])
        if not wv:
            print("⚠️  wasm-validate not found — skipping validation")
            return
        rc, err = _run_local([wv, str(output)])
        print(f"✅ {output.name} is valid" if rc == 0 else f"❌ {output.name} is INVALID:\n{err}")


def _inspect(output: Path, cwd: Path, use_docker: bool) -> None:
    rel_out = f"/work/{_rel_path(output, cwd)}"
    if use_docker:
        ensure_image(MOVE_TOOLCHAIN_IMAGE)
        run_image(MOVE_TOOLCHAIN_IMAGE, ["wasm-objdump", "-x", rel_out], workdir="/work", cwd=str(cwd))
    else:
        wod = _find_binary(["/opt/wabt/bin/wasm-objdump", "wasm-objdump"])
        if not wod:
            print("⚠️  wasm-objdump not found")
            return
        rc, out = _run_local([wod, "-x", str(output)])
        if rc == 0:
            lines: list[str] = []
            capture = False
            for line in out.splitlines():
                if line.startswith("Import"):
                    capture = True
                if line.startswith("Custom"):
                    capture = False
                if capture:
                    lines.append(line)
            print(f"🔍 {output.name} imports/exports:\n" + "\n".join(lines))


def cmd_move_build(args: argparse.Namespace) -> None:
    if args.show_toolchains:
        print("🔧 Toolchains:")
        tcs = detect_all()
        for key, label in [("wasi", "WASI SDK"), ("wabt", "WABT"), ("asc", "AssemblyScript")]:
            bin_path = tcs.get(key)
            print(f"  {f'{label}:':<16s} {'✅ ' + bin_path if bin_path else '❌ not found'}")
        print(f"\n  Docker image: {MOVE_TOOLCHAIN_IMAGE}")
        return

    if not args.source:
        print("❌ No source file specified")
        return

    source = Path(args.source)
    if not source.exists():
        print(f"❌ Source file not found: {source}")
        return

    output = Path(args.output) if args.output else _default_build_output(source)
    cwd = Path.cwd()

    use_docker = (not args.local) and docker_available()
    if use_docker:
        print(f"  🔨 Building in Docker image: {MOVE_TOOLCHAIN_IMAGE}")
    else:
        if args.local:
            print("  🖥️  Building with local toolchains (--local)")
        else:
            print("  ⚠️  Docker not available — using local toolchains (fallback).")

    try:
        if use_docker:
            _compile_in_docker(source, output, cwd)
        else:
            _compile_local(source, output, cwd)
    except SystemExit:
        raise
    except DockerError as e:
        # Compiler diagnostics (if any) were already streamed to the terminal;
        # surface a clean failure instead of a traceback.
        print(f"❌ Build failed: {e}")
        raise SystemExit(1)
    except Exception as e:  # pragma: no cover — defensive
        print(f"❌ Build failed: {e}")
        raise SystemExit(1)

    size_kb = output.stat().st_size / 1024
    print(f"✅ Compiled {source.name} → {output}")
    print(f"   📦 Size: {size_kb:.1f} KB")

    if args.validate:
        _validate(output, cwd, use_docker)
    if args.inspect:
        _inspect(output, cwd, use_docker)
