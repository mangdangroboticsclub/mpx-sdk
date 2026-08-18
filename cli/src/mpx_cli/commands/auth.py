"""mpx-cli auth — signup, login, and logout commands."""

from __future__ import annotations

import argparse
import getpass
import sys

from mpx_cli.sdk.gateway import GatewayClient, GatewayError
from mpx_cli.sdk.auth import (
    read_token,
    write_token,
    clear_token,
    get_username_from_token,
)


def add_auth_parser(sub: argparse._SubParsersAction) -> None:
    """Add ``signup``, ``login``, and ``logout`` subcommands."""

    # ── signup ───────────────────────────────────────────────────
    p_signup = sub.add_parser("signup", help="Register a new marketplace account")
    p_signup.add_argument("username", help="Desired username")
    p_signup.add_argument(
        "--password", "-p",
        help="Password (prompted securely if omitted)",
    )

    # ── login ────────────────────────────────────────────────────
    p_login = sub.add_parser("login", help="Authenticate and store a session token")
    p_login.add_argument("username", help="Account username")
    p_login.add_argument(
        "--password", "-p",
        help="Password (prompted securely if omitted)",
    )

    # ── logout ───────────────────────────────────────────────────
    p_logout = sub.add_parser("logout", help="Clear stored session token")
    p_logout.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation",
    )


def cmd_signup(args: argparse.Namespace) -> None:
    """Handle ``mpx-cli signup <username>``."""
    password = args.password
    if not password:
        password = getpass.getpass("Password: ")

    client = GatewayClient(gateway_url=getattr(args, "gateway_url", None))
    print(f"📝 Registering account '{args.username}'...")

    try:
        result = client.signup(args.username, password)
        print(f"✅ Account created for '{args.username}'")
        if "message" in result:
            print(f"   {result['message']}")
    except GatewayError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


def cmd_login(args: argparse.Namespace) -> None:
    """Handle ``mpx-cli login <username>``."""
    # Check if already logged in
    existing = read_token()
    if existing:
        existing_user = get_username_from_token(existing)
        if existing_user:
            print(f"🔑 Already logged in as '{existing_user}'")
            resp = input("Log in again? [y/N] ")
            if resp.lower() not in ("y", "yes"):
                print("Cancelled.")
                return

    password = args.password
    if not password:
        password = getpass.getpass("Password: ")

    client = GatewayClient(gateway_url=getattr(args, "gateway_url", None))
    print(f"🔑 Authenticating as '{args.username}'...")

    try:
        result = client.login(args.username, password)
        token = result.get("token")
        if not token:
            print("❌ Login failed: no token in response", file=sys.stderr)
            sys.exit(1)

        write_token(token)
        print(f"✅ Logged in as '{args.username}'")
        print(f"   Token stored in ~/.mpx-cli-token")
    except GatewayError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


def cmd_logout(args: argparse.Namespace) -> None:
    """Handle ``mpx-cli logout``."""
    token = read_token()
    if not token:
        print("ℹ️  Not logged in.")
        return

    username = get_username_from_token(token) or "unknown"
    if not args.yes:
        resp = input(f"Log out '{username}'? [y/N] ")
        if resp.lower() not in ("y", "yes"):
            print("Cancelled.")
            return

    clear_token()
    print(f"✅ Logged out '{username}'")
