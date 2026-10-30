"""mpx CLI — argument parsing and command dispatch.

Command surface (design doc §5):

  mpx login | signup | logout          # shared marketplace auth
  mpx publish [dir]                    # shared publish (auto-detects family)
  mpx search | info | versions         # shared marketplace browse

  mpx move init|build|upload|run|list|delete   # robot (WASM) skills
  mpx web  init|seed|list|delete|readme|session|up|down  # web (AWA) skills

  mpx update-manifest [dir]            # shared manifest metadata editor
                                       # (also: mpx move|web update-manifest)
"""

from __future__ import annotations

import sys

import argparse

from mpx_tool import __version__
from mpx_tool.commands.auth import add_auth_parsers, cmd_login, cmd_logout, cmd_signup
from mpx_tool.commands.info import add_info_parser, cmd_info
from mpx_tool.commands.manifest_cmd import add_update_manifest_parser, cmd_update_manifest
from mpx_tool.commands.publish import add_publish_parser, cmd_publish
from mpx_tool.commands.search import add_search_parser, cmd_search
from mpx_tool.commands.versions import add_versions_parser, cmd_versions
from mpx_tool.commands.move.build import add_move_build_parser, cmd_move_build
from mpx_tool.commands.move.delete import add_move_delete_parser, cmd_move_delete
from mpx_tool.commands.move.init import add_move_init_parser, cmd_move_init
from mpx_tool.commands.move.list_ import add_move_list_parser, cmd_move_list
from mpx_tool.commands.move.run import add_move_run_parser, cmd_move_run
from mpx_tool.commands.move.upload import add_move_upload_parser, cmd_move_upload
from mpx_tool.commands.web.delete import add_web_delete_parser, cmd_web_delete
from mpx_tool.commands.web.init import add_web_init_parser, cmd_web_init
from mpx_tool.commands.web.list_ import add_web_list_parser, cmd_web_list
from mpx_tool.commands.web.readme import add_web_readme_parser, cmd_web_readme
from mpx_tool.commands.web.runtime import add_web_runtime_parsers, cmd_web_down, cmd_web_up
from mpx_tool.commands.web.seed import add_web_seed_parser, cmd_web_seed
from mpx_tool.commands.web.session import add_web_session_parser, cmd_web_session

_SHARED = {
    "login": cmd_login,
    "signup": cmd_signup,
    "logout": cmd_logout,
    "publish": cmd_publish,
    "search": cmd_search,
    "info": cmd_info,
    "versions": cmd_versions,
    "update-manifest": cmd_update_manifest,
}

_MOVE = {
    "init": cmd_move_init,
    "build": cmd_move_build,
    "upload": cmd_move_upload,
    "run": cmd_move_run,
    "list": cmd_move_list,
    "ls": cmd_move_list,  # argparse alias — parser stores the literal name typed
    "delete": cmd_move_delete,
    "update-manifest": cmd_update_manifest,
}

_WEB = {
    "init": cmd_web_init,
    "seed": cmd_web_seed,
    "list": cmd_web_list,
    "delete": cmd_web_delete,
    "readme": cmd_web_readme,
    "update-manifest": cmd_update_manifest,
    "session": cmd_web_session,
    "up": cmd_web_up,
    "down": cmd_web_down,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mpx",
        description="MPX developer CLI — robot (WASM) and web (AWA) skills",
    )
    parser.add_argument(
        "--gateway",
        default=None,
        help="Marketplace gateway URL (env: MPX_GATEWAY_URL)",
    )
    parser.add_argument(
        "--worker-url",
        default=None,
        help="AWA worker URL (env: AWA_WORKER_URL)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"mpx {__version__}",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── Shared (marketplace / auth) ──────────────────────────────
    add_auth_parsers(sub)
    add_publish_parser(sub)
    add_search_parser(sub)
    add_info_parser(sub)
    add_versions_parser(sub)
    add_update_manifest_parser(sub)

    # ── move family (robot / WASM) ───────────────────────────────
    p_move = sub.add_parser("move", help="Robot (WASM) skill commands")
    move_sub = p_move.add_subparsers(dest="move_command", required=True)
    add_move_init_parser(move_sub)
    add_move_build_parser(move_sub)
    add_move_upload_parser(move_sub)
    add_move_run_parser(move_sub)
    add_move_list_parser(move_sub)
    add_move_delete_parser(move_sub)
    add_update_manifest_parser(move_sub)

    # ── web family (merchant web / AWA) ──────────────────────────
    p_web = sub.add_parser("web", help="Web (AWA) skill commands")
    web_sub = p_web.add_subparsers(dest="web_command", required=True)
    add_web_init_parser(web_sub)
    add_web_seed_parser(web_sub)
    add_web_list_parser(web_sub)
    add_web_delete_parser(web_sub)
    add_web_readme_parser(web_sub)
    add_update_manifest_parser(web_sub)
    add_web_session_parser(web_sub)
    add_web_runtime_parsers(web_sub)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Inject gateway/worker URLs so commands can read them uniformly.
    args.gateway_url = args.gateway
    args.worker_url = args.worker_url

    try:
        if args.command in _SHARED:
            _handle(parser, args, _SHARED, args.command, "command")
        elif args.command == "move":
            _handle(parser, args, _MOVE, args.move_command, "move command")
        elif args.command == "web":
            _handle(parser, args, _WEB, args.web_command, "web command")
        else:  # pragma: no cover
            parser.error(f"unknown command: {args.command}")
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)


def _handle(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    handlers: dict[str, object],
    name: str,
    what: str,
) -> None:
    """Invoke a command handler, failing gracefully on an unknown name.

    argparse accepts aliases (e.g. ``move ls`` for ``move list``), and the
    parser stores the literal name that was typed — so ``args.move_command``
    can hold a spelling that isn't (yet) a canonical key. Rather than a raw
    ``KeyError`` traceback, fall back to argparse's own usage/exit-2 message.
    """
    handler = handlers.get(name)
    if handler is None:
        parser.error(f"unknown {what}: {name}")
    handler(args)


# ── Transitional legacy entry points (design doc §5.4) ──────────

_LEGACY_NOTICE = "⚠️  '{prog}' is deprecated — use 'mpx' instead."

_MOVE_CMDS = {"init", "build", "upload", "run", "list", "ls", "delete"}
_WEB_CMDS = {"init", "seed", "session", "readme", "list", "delete", "up", "down"}
_SHARED_CMDS = {"login", "signup", "logout", "publish", "search", "info", "versions", "update-manifest"}


def _legacy_main(prog: str, family: str, argv: list[str] | None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    print(_LEGACY_NOTICE.format(prog=prog), file=sys.stderr)

    if not args or args[0] in ("--help", "-h", "--version", "-v"):
        main(args)
        return

    cmd = args[0]
    if family == "move" and cmd in _MOVE_CMDS:
        main(["move", cmd, *args[1:]])
    elif family == "web" and cmd in _WEB_CMDS:
        main(["web", cmd, *args[1:]])
    elif cmd in _SHARED_CMDS:
        main(args)
    else:
        print(f"Error: unknown {prog} command '{cmd}'.", file=sys.stderr)
        sys.exit(2)


def main_legacy_cli(argv: list[str] | None = None) -> None:
    _legacy_main("mpx-cli", "move", argv)


def main_legacy_awa(argv: list[str] | None = None) -> None:
    _legacy_main("mpx-awa", "web", argv)
