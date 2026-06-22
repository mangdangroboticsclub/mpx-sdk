"""Toolchain detection and WASM compilation for MPX-Dog skills.

Portable — detects toolchains available on the current system.
Supports three compilation paths:

  1. C/C++  → WASI SDK  (``/opt/wasi-sdk/bin/clang``)
  2. WAT    → WABT       (``/opt/wabt/bin/wat2wasm``)
  3. TS     → AssemblyScript (``asc`` via npm)
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


# ── Data types ────────────────────────────────────────────────────

@dataclass
class Toolchain:
    """Describes a detected compiler toolchain."""

    name: str
    """Human-readable name (e.g. ``"WASI SDK"``)."""

    key: str
    """Short key for lookups (e.g. ``"wasi"``)."""

    extensions: list[str] = field(default_factory=list)
    """Source file extensions this toolchain handles (e.g. ``[".c", ".cc"]``)."""

    bin: str | None = None
    """Path to the detected binary, or ``None`` if not found."""

    version: str = ""
    """Version string from the toolchain."""

    compile_fn: Callable[[str, str | None], CompileResult] | None = None
    """Callback that compiles a source file to .wasm."""


@dataclass
class CompileResult:
    """Result of a single compilation attempt."""

    success: bool
    """Whether compilation succeeded."""

    message: str
    """Human-readable status message."""

    output_path: str | None = None
    """Path to the generated .wasm file, or ``None`` on failure."""

    stderr: str = ""
    """Raw stderr from the compiler (for debugging)."""


# ── Toolchain detection ───────────────────────────────────────────

def _run(cmd: list[str], timeout: int = 10) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return -1, "", "command not found"
    except subprocess.TimeoutExpired:
        return -1, "", "timed out"


def _detect_wasi() -> Toolchain:
    """Detect WASI SDK (C/C++ → WASM)."""
    tc = Toolchain(name="WASI SDK", key="wasi", extensions=[".c", ".cc", ".cpp"])
    candidates = [
        os.environ.get("WASI_CC"),
        shutil.which("clang"),
        "/opt/wasi-sdk/bin/clang",
    ]
    for cand in candidates:
        if cand and os.path.isfile(cand):
            rc, out, _ = _run([cand, "--version"])
            if rc == 0:
                tc.bin = cand
                # Extract "version X.Y.Z" from clang version string
                m = re.search(r"version\s+([\d.]+)", out)
                tc.version = m.group(1) if m else out.split("\n")[0]
                break
    return tc


def _detect_wabt() -> Toolchain:
    """Detect WABT tools (WAT → WASM)."""
    tc = Toolchain(name="WABT", key="wabt", extensions=[".wat"])
    candidates = [
        shutil.which("wat2wasm"),
        "/opt/wabt/bin/wat2wasm",
    ]
    for cand in candidates:
        if cand and os.path.isfile(cand):
            rc, out, _ = _run([cand, "--version"])
            if rc == 0:
                tc.bin = cand
                tc.version = out.strip()
                break
    return tc


def _detect_asc() -> Toolchain:
    """Detect AssemblyScript compiler (TS → WASM)."""
    tc = Toolchain(name="AssemblyScript", key="asc", extensions=[".ts"])
    cand = shutil.which("asc")
    if cand:
        rc, out, _ = _run([cand, "--version"])
        if rc == 0:
            tc.bin = cand
            tc.version = out.strip()
    return tc


def detect_all() -> dict[str, Toolchain]:
    """Detect all available toolchains.

    Returns a dict keyed by ``toolchain.key``.
    """
    toolchains: dict[str, Toolchain] = {}
    for detector in [_detect_wasi, _detect_wabt, _detect_asc]:
        tc = detector()
        toolchains[tc.key] = tc
    return toolchains


# ── Compilation ───────────────────────────────────────────────────

def _compile_c(source: str, output: str | None) -> CompileResult:
    """Compile a C/C++ file using WASI SDK."""
    tc = _detect_wasi()
    if not tc.bin:
        return CompileResult(False, "❌ WASI SDK not found — install clang for wasm32 target")

    src = Path(source)
    out = Path(output) if output else src.with_suffix(".wasm")

    cmd = [
        tc.bin,
        "--target=wasm32-wasip1",
        "-nostartfiles",
        "-Wl,--no-entry",
        "-Wl,--export=on_start",
        "-Wl,--import-undefined",
        "-o", str(out),
    ]

    # Auto-add -I flags for nearby include/ directories
    seen: set[Path] = set()
    for candidate in [
        src.parent / "include",
        src.parent.parent / "include",
        Path.cwd() / "include",
    ]:
        resolved = candidate.resolve()
        if resolved.is_dir() and resolved not in seen:
            cmd.extend(["-I", str(resolved)])
            seen.add(resolved)

    # Ensure output directory exists
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd.append(str(src))

    rc, stdout, stderr = _run(cmd, timeout=60)
    if rc == 0:
        return CompileResult(
            True,
            f"✅ Compiled {src.name} → {out.name}",
            str(out),
        )
    else:
        return CompileResult(
            False,
            f"❌ Compilation failed (exit code {rc})",
            stderr=stderr,
        )


def _compile_wat(source: str, output: str | None) -> CompileResult:
    """Compile a .wat file using WABT's wat2wasm."""
    tc = _detect_wabt()
    if not tc.bin:
        return CompileResult(False, "❌ WABT (wat2wasm) not found")

    src = Path(source)
    out = Path(output) if output else src.with_suffix(".wasm")

    cmd = [tc.bin, str(src), "-o", str(out)]
    rc, stdout, stderr = _run(cmd, timeout=30)
    if rc == 0:
        return CompileResult(
            True,
            f"✅ Compiled {src.name} → {out.name}",
            str(out),
        )
    else:
        return CompileResult(
            False,
            f"❌ wat2wasm failed (exit code {rc})",
            stderr=stderr,
        )


def _compile_ts(source: str, output: str | None) -> CompileResult:
    """Compile a TypeScript/AssemblyScript file using asc."""
    tc = _detect_asc()
    if not tc.bin:
        return CompileResult(False, "❌ AssemblyScript compiler (asc) not found")

    src = Path(source)
    out = Path(output) if output else src.with_suffix(".wasm")

    cmd = [
        tc.bin,
        str(src),
        "--importMemory",
        "--exportRuntime",
        "--outFile", str(out),
    ]
    rc, stdout, stderr = _run(cmd, timeout=60)
    if rc == 0:
        return CompileResult(
            True,
            f"✅ Compiled {src.name} → {out.name}",
            str(out),
        )
    else:
        return CompileResult(
            False,
            f"❌ asc failed (exit code {rc})",
            stderr=stderr,
        )


# Extension → compiler dispatch table
_COMPILERS: dict[str, Callable[[str, str | None], CompileResult]] = {
    ".c": _compile_c,
    ".cc": _compile_c,
    ".cpp": _compile_c,
    ".wat": _compile_wat,
    ".ts": _compile_ts,
}


def compile_file(source: str, output: str | None = None) -> CompileResult:
    """Compile a single source file to WASM.

    The file extension determines which toolchain is used:

    * ``.c``, ``.cc``, ``.cpp`` → WASI SDK
    * ``.wat`` → WABT (wat2wasm)
    * ``.ts`` → AssemblyScript (asc)

    Args:
        source: Path to the source file.
        output: Optional output path. Defaults to source with ``.wasm`` extension.

    Returns:
        A :class:`CompileResult` with the outcome.
    """
    ext = Path(source).suffix.lower()
    compiler = _COMPILERS.get(ext)
    if compiler is None:
        return CompileResult(
            False,
            f"❌ Unsupported extension '{ext}' — use .c, .cc, .cpp, .wat, or .ts",
        )
    return compiler(source, output)


# ── Validation & inspection ───────────────────────────────────────

def validate_wasm(wasm_path: str) -> CompileResult:
    """Run ``wasm-validate`` on a .wasm file.

    Returns a :class:`CompileResult` where ``success`` indicates validity.
    """
    wv = shutil.which("wasm-validate") or "/opt/wabt/bin/wasm-validate"
    if not os.path.isfile(wv):
        return CompileResult(False, "❌ wasm-validate not found")

    rc, _, stderr = _run([wv, wasm_path])
    name = Path(wasm_path).name
    if rc == 0:
        return CompileResult(True, f"✅ {name} is valid")
    else:
        return CompileResult(False, f"❌ {name} is INVALID:\n{stderr}")


def inspect_wasm(wasm_path: str) -> CompileResult:
    """Show imports/exports of a .wasm file via ``wasm-objdump``.

    Returns a :class:`CompileResult` with details in the message.
    """
    wod = shutil.which("wasm-objdump") or "/opt/wabt/bin/wasm-objdump"
    if not os.path.isfile(wod):
        return CompileResult(False, "❌ wasm-objdump not found")

    rc, out, _ = _run([wod, "-x", wasm_path])
    name = Path(wasm_path).name
    if rc == 0:
        # Extract just the Import/Export sections
        lines: list[str] = []
        capture = False
        for line in out.splitlines():
            if line.startswith("Import"):
                capture = True
            if line.startswith("Custom"):
                capture = False
            if capture:
                lines.append(line)
        return CompileResult(True, f"🔍 {name} imports/exports:\n" + "\n".join(lines))
    else:
        return CompileResult(False, f"❌ wasm-objdump failed for {name}")
