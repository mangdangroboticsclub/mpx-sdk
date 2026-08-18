"""mpx-cli deploy — build, upload and run in one command.

This is the loop you actually run all day. Before this command it was three
invocations with the skill name spelled three different ways and the robot IP
repeated twice::

    mpx-cli build  src/my_skill.c --validate
    mpx-cli upload build/my_skill.wasm --ip 192.168.2.1
    mpx-cli run    my_skill.wasm --ip 192.168.2.1

Now it is::

    mpx-cli deploy

Each step delegates to the existing command function rather than duplicating
its logic, so behaviour stays identical to running them by hand — including the
manifest-based path inference, which is what makes the arguments unnecessary.

Failures stop the chain. That matters more than it sounds: ``build`` used to
return successfully after a failed compile, so a ``build && upload`` shell
chain would happily push the *previous* binary and look like it worked.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from mpx_cli.commands.build import cmd_build
from mpx_cli.commands.run import add_run_options, cmd_run
from mpx_cli.commands.upload import cmd_upload
from mpx_cli.sdk.project import project_for_source


def add_deploy_parser(sub: argparse._SubParsersAction) -> None:
    from mpx_cli.cli import robot_opts

    p = sub.add_parser(
        "deploy",
        parents=[robot_opts()],
        help="Build, upload and run in one step (the usual dev loop)",
    )
    p.add_argument(
        "source", nargs="?",
        help="Source file (default: src/<slug>.<ext> from manifest.json)",
    )
    p.add_argument(
        "-o", "--output", default=None,
        help="Output .wasm path (default: build/<slug>.wasm)",
    )
    p.add_argument(
        "--no-run", action="store_true",
        help="Upload but do not execute the skill",
    )
    p.add_argument(
        "--validate", action="store_true",
        help="Run wasm-validate on the built module",
    )
    # deploy must report a failed run exactly as `run` does, or the one-command
    # loop reintroduces the blind spot `run` just lost.
    add_run_options(p)


def cmd_deploy(args: argparse.Namespace) -> bool:
    # Anchored on the argument, not the current directory: `mpx-cli deploy
    # four-ways` from one level up must upload and run the skill it just built,
    # not one inferred from wherever the shell happens to be.
    project = project_for_source(args.source)

    # ── 1. Build ────────────────────────────────────────────────
    # cmd_build raises on a missing source or a failed compile, and cli.py
    # turns that into exit code 1 — so an exception here correctly aborts the
    # deploy instead of uploading whatever happened to be in build/.
    build_args = argparse.Namespace(
        source=args.source,
        output=args.output,
        validate=args.validate,
        inspect=False,
        show_toolchains=False,
    )
    cmd_build(build_args)

    # ── 2. Upload ───────────────────────────────────────────────
    # Prefer the exact artifact we just built. Falling back to None lets
    # cmd_upload do its own manifest lookup, which keeps one code path for
    # inference rather than two that can disagree.
    wasm = args.output
    if wasm is None and project is not None:
        wasm = str(project.wasm)

    print()
    upload_args = argparse.Namespace(wasm=wasm, ip=args.ip, port=args.port)
    if cmd_upload(upload_args) is False:
        # Do not go on to run: the robot is still holding the previous build,
        # so running now would execute stale code and look like it worked.
        return False

    if args.no_run:
        return True

    # ── 3. Run ──────────────────────────────────────────────────
    # The robot stores a skill under the basename of what was uploaded, so run
    # that exact name. Deriving it from the manifest instead would run the
    # wrong file whenever -o was used, or whenever the build came from a
    # directory argument rather than the current directory.
    print()
    remote = Path(wasm).name if wasm else None
    run_args = argparse.Namespace(
        skill=remote, ip=args.ip, port=args.port,
        no_wait=getattr(args, "no_wait", False),
        timeout=getattr(args, "timeout", 70),
    )
    return cmd_run(run_args)
