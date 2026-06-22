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


def add_build_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("build", help="Compile a C/WAT/TS source file to .wasm")
    p.add_argument("source", nargs="?", help="Source file (.c, .wat, .ts)")
    p.add_argument(
        "-o", "--output", default=None,
        help="Output .wasm path (default: source path with .wasm extension)",
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

    if not args.source:
        print("❌ No source file specified")
        return

    source = Path(args.source)
    if not source.exists():
        print(f"❌ Source file not found: {source}")
        return

    # Ensure output directory exists
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    result = compile_file(str(source), args.output)
    print(result.message)

    if not result.success:
        if result.stderr:
            print(result.stderr, end="")
        return

    if result.output_path:
        wasm_path = Path(result.output_path)
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