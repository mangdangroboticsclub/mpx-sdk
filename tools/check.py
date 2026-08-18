#!/usr/bin/env python3
"""Everything CI should run. `python tools/check.py`

Five things, in the order they are cheapest to fix:

  1. generated files are in sync with the firmware and the CLI
  2. every relative link in the docs points at something that exists
  3. the prose agrees with the repo: ABI version, symbol count, example names
  4. every example has the three files it needs
  5. every example compiles for wasm32, and every import it uses is in the ABI

(5) is skipped with a note when no wasm-capable clang is on PATH, so this is
still useful on a machine without the toolchain.

(3) exists because a link check only proves a target exists, not that the
sentence around it is true. The README said "ABI v3" and "64 host functions"
for an entire release of v4-and-70, and pointed at examples 01..08 when six
existed. Every one of those was a first-hour failure for somebody, and not
one of them was catchable by reading carefully.

The link check exists because the previous docs cited `examples/walk-with-gains`
as the worked example while that example sat in a folder named `_to_delete/`.
Nothing catches that except checking.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAILURES: list[str] = []


def section(title: str) -> None:
    print(f"\n== {title}")


def fail(msg: str) -> None:
    FAILURES.append(msg)
    print(f"   FAIL  {msg}")


def ok(msg: str) -> None:
    print(f"   ok    {msg}")


# ── 1. generated files ──────────────────────────────────────────────────────
section("generated files")
for script in ("gen_abi.py", "gen_gaits.py", "gen_geometry.py",
               "gen_params.py", "gen_coverage.py", "gen_docs.py"):
    r = subprocess.run([sys.executable, str(ROOT / "tools" / script), "--check"],
                       capture_output=True, text=True, cwd=ROOT)
    (ok if r.returncode == 0 else fail)(
        f"{script} --check" + ("" if r.returncode == 0 else f"\n{r.stdout}{r.stderr}"))

# ── 2. links ────────────────────────────────────────────────────────────────
section("documentation links")
LINK = re.compile(r"\[[^\]]*\]\(([^)#]+?)(?:#[^)]*)?\)")
checked = broken = 0
for md in sorted(ROOT.rglob("*.md")):
    if "_to_delete" in md.parts or "node_modules" in md.parts:
        continue
    for target in LINK.findall(md.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        checked += 1
        if not (md.parent / target).resolve().exists():
            broken += 1
            fail(f"{md.relative_to(ROOT)} -> {target}")
if not broken:
    ok(f"{checked} relative links, all resolve")

# The one number every example must agree with. Read, never typed: this
# check existed and still said 3 the day the firmware moved to 4.
SDK_ABI = json.loads((ROOT / "abi" / "host_functions.json")
                     .read_text(encoding="utf-8"))["abi_version"]

# Every maker-facing page must be reachable from docs/README.md in one hop.
# The previous docs grew to 28 files because nothing noticed when a page
# stopped being linked; four unread pages are worse than one read one.
index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
orphans = [p.name for p in sorted((ROOT / "docs").glob("*.md"))
           if p.name != "README.md" and p.name not in index]
(ok if not orphans else fail)(
    "every docs page is linked from the index"
    + ("" if not orphans else f" — orphaned: {', '.join(orphans)}"))

# ── 3. prose that can go stale ──────────────────────────────────────────────
section("prose agrees with the repo")

_abi = json.loads((ROOT / "abi" / "host_functions.json").read_text(encoding="utf-8"))
readme = (ROOT / "README.md").read_text(encoding="utf-8")

# The two numbers a maker acts on before anything else: which firmware to
# flash, and therefore whether their first skill will run at all.
m = re.search(r"ABI v(\d+)", readme)
if not m:
    fail("README.md does not state an ABI version")
elif int(m.group(1)) != _abi["abi_version"]:
    fail(f"README.md says ABI v{m.group(1)}, abi/host_functions.json says "
         f"v{_abi['abi_version']}")
else:
    ok(f"README ABI version — v{_abi['abi_version']}")

m = re.search(r"(\d+) host functions", readme)
if not m:
    fail("README.md does not state a host-function count")
elif int(m.group(1)) != _abi["symbol_count"]:
    fail(f"README.md says {m.group(1)} host functions, the ABI has "
         f"{_abi['symbol_count']}")
else:
    ok(f"README host-function count — {_abi['symbol_count']}")

# Every examples/NN-name written down anywhere, in any file type, must be a
# directory that exists. Renaming an example is exactly when this rots.
EXAMPLE_REF = re.compile(r"examples/(\d\d-[a-z0-9-]+)")
missing: dict[str, set[str]] = {}
scanned = 0
for f in sorted(ROOT.rglob("*")):
    if not f.is_file() or f.suffix not in {".md", ".c", ".h", ".py", ".json", ".ts", ".wat"}:
        continue
    if any(part in {".git", "_to_delete", "node_modules", "build"} for part in f.parts):
        continue
    scanned += 1
    for name in set(EXAMPLE_REF.findall(f.read_text(encoding="utf-8", errors="ignore"))):
        if not (ROOT / "examples" / name).is_dir():
            missing.setdefault(name, set()).add(str(f.relative_to(ROOT)))
if missing:
    for name, where in sorted(missing.items()):
        fail(f"examples/{name} does not exist — cited in {', '.join(sorted(where))}")
else:
    ok(f"every examples/NN-* reference resolves ({scanned} files scanned)")

# The headers are documentation too, and their doc links are invisible to the
# markdown link check above. mpx.h pointed at docs/guide/how-motion-works.md
# for a whole restructure after that page stopped existing.
DOC_REF = re.compile(r"docs/[A-Za-z0-9_./-]+\.md")
header_bad = []
for h in sorted((ROOT / "sdk" / "include").rglob("*.h")):
    for target in set(DOC_REF.findall(h.read_text(encoding="utf-8", errors="ignore"))):
        if not (ROOT / target).exists():
            header_bad.append(f"{h.relative_to(ROOT)} -> {target}")
(ok if not header_bad else fail)(
    "doc paths cited inside sdk/include are real"
    + ("" if not header_bad else " — " + "; ".join(header_bad)))

# ── 4. example structure ────────────────────────────────────────────────────
section("example structure")
for d in sorted((ROOT / "examples").iterdir()):
    if not d.is_dir():
        continue
    manifest = d / "manifest.json"
    if not manifest.is_file():
        fail(f"{d.name}: no manifest.json")
        continue
    m = json.loads(manifest.read_text(encoding="utf-8"))
    problems = []
    if not (d / "README.md").is_file():
        problems.append("no README.md")
    if not any((d / "src" / f"{m['slug']}{e}").is_file() for e in (".c", ".cc", ".ts", ".wat")):
        problems.append(f"no src/{m['slug']}.*")
    if m.get("abi") != SDK_ABI:
        problems.append(f"abi is {m.get('abi')}, expected {SDK_ABI}")
    (ok if not problems else fail)(f"{d.name}" + ("" if not problems else ": " + ", ".join(problems)))

# ── 5. compile ──────────────────────────────────────────────────────────────
section("compile every example for wasm32")
def _wasm_clang() -> "str | None":
    """The first clang that can actually emit wasm32.

    Finding *a* clang is not the same as finding one that can build a skill.
    An ESP-IDF or Xtensa toolchain puts a clang on PATH with no wasm32 target
    in it, and this check then failed all six examples with
    "No available targets are compatible with triple wasm32" -- which looks
    like the SDK is broken when it is the toolchain that is wrong. Probe
    instead of assuming, and prefer the WASI SDK where it is installed.
    """
    seen = []
    candidates = [
        os.environ.get("WASI_CC"),
        "/opt/wasi-sdk/bin/clang",
        r"C:\wasi-sdk\bin\clang.exe",
        shutil.which("clang"),
    ]
    for cand in candidates:
        if not cand or cand in seen:
            continue
        seen.append(cand)
        if not (os.path.isfile(cand) or shutil.which(cand)):
            continue
        probe = subprocess.run(
            [cand, "--target=wasm32", "-nostdlib", "-c", "-x", "c",
             "-o", os.devnull, "-"],
            input="int main(void){return 0;}", capture_output=True, text=True)
        if probe.returncode == 0:
            return cand
    return None


clang = _wasm_clang()
if not clang:
    found = shutil.which("clang")
    print("   SKIPPED — no clang that can target wasm32. This is the check that\n"
          "            catches a header change breaking every example; CI runs\n"
          "            it, you are not.")
    if found:
        print(f"            (`{found}` exists but has no wasm32 target — that is\n"
              "             usually an ESP-IDF or Xtensa clang.)")
    print("            Install the WASI SDK, or set WASI_CC to a clang that can:\n"
          "              https://github.com/WebAssembly/wasi-sdk/releases\n"
          "            On Debian/Ubuntu: apt install clang lld")
else:
    abi = json.loads((ROOT / "abi" / "host_functions.json").read_text(encoding="utf-8"))
    allowed = {s["name"] for s in abi["symbols"]}
    inc = ROOT / "sdk" / "include"
    outdir = ROOT / "build" / "_check"
    outdir.mkdir(parents=True, exist_ok=True)

    for src in sorted((ROOT / "examples").glob("*/src/*.c")):
        out = outdir / (src.stem + ".wasm")
        r = subprocess.run(
            [clang, "--target=wasm32", "-nostdlib", "-O2",
             "-Wall", "-Wextra", "-Wconversion", "-Wno-sign-conversion",
             "-Wl,--no-entry", "-Wl,--export=on_start",
             "-Wl,--export-if-defined=on_stop", "-Wl,--export-if-defined=on_tick", "-Wl,--import-undefined",
             "-I", str(inc), "-o", str(out), str(src)],
            capture_output=True, text=True)
        if r.returncode != 0 or r.stderr.strip():
            fail(f"{src.parent.parent.name}\n{r.stderr[:1200]}")
            continue
        data = out.read_bytes()
        unknown = {n.decode() for n in
                   re.findall(rb"\x03env.([a-z_][a-z_0-9]{2,31})", data)} - allowed
        if unknown:
            fail(f"{src.parent.parent.name}: imports not in the ABI: {sorted(unknown)}")
        else:
            ok(f"{src.parent.parent.name:<16} {len(data):>6} bytes")

# ── verdict ─────────────────────────────────────────────────────────────────
print()
if FAILURES:
    print(f"{len(FAILURES)} problem(s)")
    sys.exit(1)
print("all checks passed")
