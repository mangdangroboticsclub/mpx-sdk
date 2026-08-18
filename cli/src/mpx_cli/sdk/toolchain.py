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

    tried: list[str] = field(default_factory=list)
    """One line per candidate location, saying what was found there.

    A missing toolchain used to report only that it was missing, which tells
    you nothing about *where* to install it or which of several possible
    installs the CLI is unhappy with. Recording the search means the error can
    show its work, and "the binary is there but will not run" stops looking
    identical to "the binary is not there".
    """


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

TIMED_OUT = -2
"""_run()'s exit code for "the command did not answer in time".

Distinct from -1 (not found) on purpose. Collapsing the two is what made a
slow disk indistinguishable from an uninstalled compiler.
"""


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
        return TIMED_OUT, "", "timed out"


def _probe(tc: Toolchain, label: str, cand: str | None,
           version_re: str | None = None) -> bool:
    """Is @p cand a usable toolchain binary? Record what was found either way.

    EXISTENCE DECIDES, THE VERSION IS DECORATION — and getting that backwards
    is a real bug this had. Detection ran `<binary> --version` with a 10 s
    timeout and treated any non-zero result as "not installed". Running
    `--version` on WASI SDK's clang means faulting a ~100 MB binary in from an
    overlay filesystem; on a cold container over Docker Desktop that can take
    longer than ten seconds. So `mpx-cli deploy` reported MISSING WASI SDK,
    and the identical command a moment later — same container, nothing
    rebuilt, page cache now warm — compiled fine.

    A compiler that is present and executable is present. The version probe
    gets a longer budget, runs only to fill in a label, and can never veto the
    thing it is describing.
    """
    if not cand:
        tc.tried.append(f"{label}: not set")
        return False
    if not os.path.isfile(cand):
        tc.tried.append(f"{label}: no such file ({cand})")
        return False
    if not os.access(cand, os.X_OK):
        tc.tried.append(f"{label}: found at {cand} but not executable")
        return False

    # 60 s, because the first read of a large binary on a cold container is
    # slow and being slow is not being absent.
    rc, out, err = _run([cand, "--version"], timeout=60)
    if rc == TIMED_OUT:
        tc.bin = cand
        tc.version = "unknown (version check timed out)"
        tc.tried.append(f"{label}: {cand} (usable; version probe timed out)")
        return True
    if rc != 0:
        # Present but genuinely broken — truncated download, half-extracted
        # archive, missing shared library. "Reinstall", not "install".
        detail = (err or out).strip().splitlines()
        tc.tried.append(f"{label}: found at {cand} but --version failed"
                        + (f" ({detail[0]})" if detail else ""))
        return False

    tc.bin = cand
    if version_re:
        m = re.search(version_re, out)
        tc.version = m.group(1) if m else out.strip().split("\n")[0]
    else:
        tc.version = out.strip().split("\n")[0]
    tc.tried.append(f"{label}: {cand} ({tc.version})")
    return True


def _detect_wasi() -> Toolchain:
    """Detect WASI SDK (C/C++ → WASM), and remember where it looked."""
    tc = Toolchain(name="WASI SDK", key="wasi", extensions=[".c", ".cc", ".cpp"])
    candidates = [
        ("$WASI_CC",             os.environ.get("WASI_CC")),
        ("clang on PATH",        shutil.which("clang")),
        ("/opt/wasi-sdk/bin/clang", "/opt/wasi-sdk/bin/clang"),
    ]
    for label, cand in candidates:
        if _probe(tc, label, cand, r"version\s+([\d.]+)"):
            break
    return tc


def _detect_wabt() -> Toolchain:
    """Detect WABT tools (WAT → WASM)."""
    tc = Toolchain(name="WABT", key="wabt", extensions=[".wat"])
    candidates = [
        ("wat2wasm on PATH",       shutil.which("wat2wasm")),
        ("/opt/wabt/bin/wat2wasm", "/opt/wabt/bin/wat2wasm"),
    ]
    for label, cand in candidates:
        if _probe(tc, label, cand):
            break
    return tc


def _detect_asc() -> Toolchain:
    """Detect AssemblyScript compiler (TS → WASM)."""
    tc = Toolchain(name="AssemblyScript", key="asc", extensions=[".ts"])
    # asc is a node shim, so the first run pays node's startup as well.
    _probe(tc, "asc on PATH", shutil.which("asc"))
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


def sdk_include_dir() -> Path | None:
    """Where the one copy of the SDK headers lives.

    Looked up in this order, first hit wins:

      1. $MPX_SDK_INCLUDE                  — an explicit override
      2. <repo>/sdk/include                — walking up from the source tree
      3. <package>/../../sdk/include       — an editable install inside the repo

    Returns None if none of them exist, in which case the compiler will report
    a missing mpx.h, which is a clearer error than anything we could invent.
    """
    env = os.environ.get("MPX_SDK_INCLUDE")
    if env and Path(env).is_dir():
        return Path(env).resolve()

    here = Path(__file__).resolve()
    for base in [Path.cwd(), *Path.cwd().parents, *here.parents]:
        candidate = base / "sdk" / "include"
        if (candidate / "mpx.h").is_file():
            return candidate.resolve()
    return None


def _compile_c(source: str, output: str | None) -> CompileResult:
    """Compile a C/C++ file using WASI SDK."""
    tc = _detect_wasi()
    if not tc.bin:
        # Show the search, not just the verdict. "install clang for wasm32
        # target" is advice you cannot act on when clang is supposed to be in
        # the dev container already — the useful question is which of the
        # three places the CLI looks came up empty, and whether the binary is
        # absent or merely broken.
        lines = ["❌ WASI SDK not found — cannot compile C to WebAssembly.",
                 "   Looked in:"]
        lines += [f"     · {t}" for t in tc.tried]
        lines += [
            "",
            "   In the dev container it lives at /opt/wasi-sdk (installed by",
            "   .devcontainer/Dockerfile and put on PATH there). If it is",
            "   missing, the container is not the one the Dockerfile builds —",
            "   rebuild it: VS Code → Dev Containers: Rebuild Container.",
            "   Outside a container, install WASI SDK and either put its bin/",
            "   on PATH or set WASI_CC=/path/to/wasi-sdk/bin/clang.",
        ]
        return CompileResult(False, "\n".join(lines))

    src = Path(source)
    out = Path(output) if output else src.with_suffix(".wasm")

    cmd = [
        tc.bin,
        "--target=wasm32-wasip1",
        "-nostartfiles",
        "-Wl,--no-entry",
        "-Wl,--export=on_start",
        # on_stop is optional, so it must not be a link error when absent.
        "-Wl,--export-if-defined=on_stop",
        "-Wl,--import-undefined",
        "-Wall",
        "-o", str(out),
    ]

    # Include paths.
    #
    # There is exactly ONE copy of the SDK headers, in sdk/include, and every
    # build points at it. Projects used to vendor their own copy, which is how
    # this repo ended up with four divergent mpx_host.h files — two of them
    # stale, one still describing ABI v1 and guaranteed to trap on its first
    # host call. A snapshot of an ABI is a snapshot of a moving target; the
    # right number of copies is one.
    #
    # A project-local include/ still comes first, so you can shadow a header
    # deliberately while you are working on one.
    seen: set[Path] = set()
    for candidate in [
        src.parent / "include",
        src.parent.parent / "include",
        Path.cwd() / "include",
        sdk_include_dir(),
    ]:
        if candidate is None:
            continue
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
        "--use", "abort=",
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
