"""mpx-cli build — compile source files to WASM."""

from __future__ import annotations

import argparse
from pathlib import Path
from mpx_cli.sdk.toolchain import (
    compile_file,
    detect_all,
    inspect_wasm,
    validate_wasm,
)
from mpx_cli.sdk.section import embed
from mpx_cli.sdk.project import MANIFEST_NAME, describe_missing, find_project
from mpx_cli.sdk.toolchain import sdk_include_dir
import json


def check_abi(project) -> None:
    """Warn when a project was written against a different ABI than this SDK.

    A module built against the wrong ABI loads fine and then traps on its first
    host call, with no message that points anywhere near the cause. It was the
    single most confusing failure in this system, and it is cheap to catch here
    instead: the project records the ABI it was scaffolded against, and the SDK
    knows the one it describes.

    A warning, not an error — you may well be deliberately targeting an older
    robot, and refusing to build would be worse than saying so.
    """
    if project is None:
        return
    declared = project.manifest.get("abi")
    if declared is None:
        return

    inc = sdk_include_dir()
    if not inc:
        return
    abi_json = inc.parent.parent / "abi" / "host_functions.json"
    if not abi_json.is_file():
        return
    try:
        current = int(json.loads(abi_json.read_text(encoding="utf-8"))["abi_version"])
    except Exception:
        return

    if int(declared) != current:
        print(f"warning: manifest.json says abi {declared}, this SDK is abi {current}")
        print( "         The robot will load the module and then trap on its first")
        print( "         host call. Update the manifest once you have flashed")
        print(f"         matching firmware:  \"abi\": {current}")


def add_build_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("build", help="Compile a C/WAT/TS source file to .wasm")
    p.add_argument(
        "source", nargs="?",
        help="Source file (default: src/<slug>.<ext> from manifest.json)",
    )
    p.add_argument(
        "-o", "--output", default=None,
        help="Output .wasm path (default: build/<name>.wasm)",
    )
    p.add_argument(
        "--validate", action="store_true",
        help="Run wasm-validate on the output",
    )
    p.add_argument(
        "--inspect", action="store_true",
        help="Show imports/exports via wasm-objdump",
    )
    p.add_argument(
        "--show-toolchains", action="store_true",
        help="List detected toolchains and exit",
    )


def _resolve_source(args: argparse.Namespace) -> tuple[Path, "object | None"]:
    """Explicit path wins; otherwise derive it from the project manifest.

    A DIRECTORY is accepted too, and means "that project". `mpx-cli deploy
    four-ways` is the obvious thing to type from one level up, and it used to
    fail with "Unsupported extension ''" — an error about a file extension,
    when the real answer is that a directory is a perfectly reasonable thing
    to point at.

    RETURNS THE PROJECT AS WELL AS THE SOURCE, and that is the whole point of
    the tuple. This resolved the project in three branches and returned only
    the path; cmd_build then read a bare `project` name that existed in none of
    its own scopes, so every successful compile ended in
    `NameError: name 'project' is not defined` at the manifest-embedding step.
    The build had already worked — only the label failed. Hand the caller the
    project it needs rather than making it look the same thing up twice.
    """
    if args.source:
        given = Path(args.source)

        if given.is_dir():
            # Deliberately not find_project(given): that walks *up*, so
            # pointing at a directory which is merely inside a project would
            # silently build the parent's skill instead of saying "there is
            # nothing here".
            project = (
                find_project(given)
                if (given / MANIFEST_NAME).is_file()
                else None
            )
            if project is None:
                raise RuntimeError(
                    f"'{given}' has no {MANIFEST_NAME}, so there is no skill "
                    f"here to build.\n"
                    f"   Pass a source file instead, or run 'mpx-cli init' to "
                    f"create a project."
                )
            source = project.source
            if source is None:
                raise RuntimeError(
                    f"'{given}' declares slug '{project.slug}' but has no "
                    f"matching source under {project.root / 'src'}.\n"
                    f"   Expected one of: {project.slug}.c / .cc / .cpp / .wat / .ts"
                )
            print(f"📦 {project.slug} (from {project.root / MANIFEST_NAME})")
            return source, project

        # A bare source path still belongs to a project — `src/foo.c` sits
        # inside one — and that project's manifest is what gets embedded. Walk
        # up from the file rather than from the shell's cwd, so building a
        # skill from outside its directory embeds ITS manifest and not a
        # neighbour's.
        return given, find_project(given.parent)

    project = find_project()

    check_abi(project)
    if project is None:
        raise RuntimeError(describe_missing("source file"))

    source = project.source
    if source is None:
        raise RuntimeError(
            f"No source file matching slug '{project.slug}' under "
            f"{project.root / 'src'}.\n"
            f"   Expected one of: {project.slug}.c / .cc / .cpp / .wat / .ts"
        )

    print(f"📦 {project.slug} (from {project.root / 'manifest.json'})")
    return source, project


def _default_build_output(source: Path) -> Path:
    """Default output path: ``build/<stem>.wasm`` alongside the source."""
    return source.parent.parent / "build" / f"{source.stem}.wasm"


def cmd_build(args: argparse.Namespace) -> None:
    if args.show_toolchains:
        print("🔧 Available toolchains:")
        for key, tc in detect_all().items():
            if tc.bin:
                status = f"✅ {tc.bin} ({tc.version})"
            else:
                status = "❌ not found"
            print(f"  {tc.name:<20s} {status}")
        return

    source, project = _resolve_source(args)

    if not source.exists():
        # Raise rather than print-and-return: cli.py turns an exception into
        # exit code 1, and a silent success here is what lets
        # `make build && make upload` push a stale binary.
        raise RuntimeError(f"Source file not found: {source}")

    # Default output: build/<name>.wasm (a sibling of src/)
    output_path = args.output or str(_default_build_output(source))
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    result = compile_file(str(source), output_path)
    print(result.message)

    if not result.success:
        if result.stderr:
            print(result.stderr, end="")
        raise RuntimeError("Build failed")

    if result.output_path:
        wasm_path = Path(result.output_path)

        # Carry the manifest's declarative fields inside the module, so the
        # robot learns what this skill provides — a gait name, an autorun
        # flag, event triggers — from the artifact itself. See sdk/section.py
        # for why it lives in the .wasm rather than beside it.
        if project is not None:
            try:
                n = embed(wasm_path, project.manifest)
                extras = [k for k in ("provides_gait", "autorun", "on")
                          if project.manifest.get(k)]
                if extras:
                    print(f"   🏷  embedded manifest ({n} B): {', '.join(extras)}")
            except OSError as exc:
                # A build that produced a working module should not fail
                # because the metadata could not be attached; the skill still
                # runs, it just will not register itself.
                print(f"   ⚠️  could not embed the manifest: {exc}")
        size_kb = wasm_path.stat().st_size / 1024
        print(f"   📦 Size: {size_kb:.1f} KB")

    if args.validate and result.output_path:
        print()
        vr = validate_wasm(result.output_path)
        print(vr.message)

    if args.inspect and result.output_path:
        print()
        ir = inspect_wasm(result.output_path)
        print(ir.message)