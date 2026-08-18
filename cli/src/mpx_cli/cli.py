"""mpx-cli entry point — argument parsing and command dispatch."""

from __future__ import annotations

import argparse
import sys

from mpx_cli.commands.init import add_init_parser, cmd_init
from mpx_cli.commands.build import add_build_parser, cmd_build
from mpx_cli.commands.upload import add_upload_parser, cmd_upload
from mpx_cli.commands.run import add_run_parser, cmd_run
from mpx_cli.commands.list_skills import add_list_parser, cmd_list
from mpx_cli.commands.delete import add_delete_parser, cmd_delete
from mpx_cli.commands.auth import add_auth_parser, cmd_signup, cmd_login, cmd_logout
from mpx_cli.commands.search import add_search_parser, cmd_search
from mpx_cli.commands.info import add_info_parser, cmd_info
from mpx_cli.commands.versions import add_versions_parser, cmd_versions
from mpx_cli.commands.publish import add_publish_parser, cmd_publish
from mpx_cli.commands.robot import add_robot_parser, cmd_robot
from mpx_cli.commands.deploy import add_deploy_parser, cmd_deploy
from mpx_cli.commands.logs import add_logs_parser, cmd_logs
from mpx_cli.commands.install import add_install_parser, cmd_install
from mpx_cli.commands.gaits import add_gaits_parser, cmd_gaits
from mpx_cli.commands.doctor import add_doctor_parser, cmd_doctor
from mpx_cli.commands.trace import add_trace_parser, cmd_trace
from mpx_cli.commands.movements import (add_movements_parser, cmd_movements,
                                        cmd_stop, cmd_safe_mode)
from mpx_cli.commands.sync import add_sync_parser, cmd_sync
from mpx_cli.sdk.connection import DEFAULT_HOST, DEFAULT_PORT
from mpx_cli.sdk.gateway import DEFAULT_GATEWAY_URL


def robot_opts() -> argparse.ArgumentParser:
    """Shared --ip/--port for every command that talks to the robot.

    The defaults are ``argparse.SUPPRESS``, and that is load-bearing. A
    subparser writes its defaults into a fresh namespace which argparse then
    copies over the parent's, so a subparser option with any concrete default
    silently overwrites a value given before the subcommand. SUPPRESS means an
    absent flag is never set at all, so ``mpx-cli --ip X upload f.wasm`` and
    ``mpx-cli upload f.wasm --ip X`` both survive, and when neither is given
    the global default (which reads MPX_HOST) is what remains.
    """
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument(
        "--ip", "-i",
        default=argparse.SUPPRESS,
        help=f"Robot IP address (default: {DEFAULT_HOST}, env: MPX_HOST)",
    )
    p.add_argument(
        "--port", "-p",
        type=int,
        default=argparse.SUPPRESS,
        help=f"Robot HTTP port (default: {DEFAULT_PORT}, env: MPX_PORT)",
    )
    return p


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mpx-cli",
        description="MPX-Dog Skill Development Kit — build & deploy WASM skills",
    )
    parser.add_argument(
        "--ip", "-i",
        default=DEFAULT_HOST,
        help=f"Robot IP address (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=DEFAULT_PORT,
        help=f"Robot HTTP port (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--gateway",
        default=DEFAULT_GATEWAY_URL,
        help=f"Marketplace gateway URL (default: {DEFAULT_GATEWAY_URL}, env: MPX_GATEWAY_URL)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"mpx-cli {__import__('mpx_cli').__version__}",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # Local robot commands (offline, no gateway needed)
    add_init_parser(sub)
    add_build_parser(sub)
    add_upload_parser(sub)
    add_run_parser(sub)
    add_deploy_parser(sub)
    add_list_parser(sub)
    add_delete_parser(sub)
    add_logs_parser(sub)
    add_install_parser(sub)
    add_gaits_parser(sub)
    add_doctor_parser(sub)
    add_trace_parser(sub)
    add_movements_parser(sub)
    add_sync_parser(sub)

    # Marketplace commands (require gateway)
    add_auth_parser(sub)
    add_publish_parser(sub)
    add_search_parser(sub)
    add_info_parser(sub)
    add_versions_parser(sub)
    add_robot_parser(sub)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Inject gateway URL for cloud commands that need it
    if hasattr(args, "gateway") and args.gateway:
        args.gateway_url = args.gateway

    commands = {
        "init": cmd_init,
        "build": cmd_build,
        "upload": cmd_upload,
        "run": cmd_run,
        "deploy": cmd_deploy,
        "list": cmd_list,
        # `list` registers aliases=["ls"]; argparse dispatches the alias as the
        # command name, so it needs its own entry or `mpx-cli ls` raises KeyError.
        "ls": cmd_list,
        "delete": cmd_delete,
        "logs": cmd_logs,
        "install": cmd_install,
        "gaits": cmd_gaits,
        "doctor": cmd_doctor,
        "trace": cmd_trace,
        "movements": cmd_movements,
        "stop": cmd_stop,
        "safe-mode": cmd_safe_mode,
        "sync": cmd_sync,
        "signup": cmd_signup,
        "login": cmd_login,
        "logout": cmd_logout,
        "publish": cmd_publish,
        "search": cmd_search,
        "info": cmd_info,
        "versions": cmd_versions,
        "robot": cmd_robot,
    }

    try:
        # Commands return False to signal a handled failure (a connection
        # refused, a missing file) that has already been reported to the user.
        # Without this they printed an error and still exited 0, so shell
        # chains and CI treated a failed upload as success.
        if commands[args.command](args) is False:
            sys.exit(1)
    except SystemExit:
        raise
    except Exception as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()