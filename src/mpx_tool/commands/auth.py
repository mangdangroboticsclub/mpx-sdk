"""Shared auth commands: login / signup / logout."""

from __future__ import annotations

import argparse
import getpass
import re
import sys

from mpx_tool.sdk.auth import (
    clear_token,
    get_username_from_token,
    read_token,
    write_token,
)
from mpx_tool.sdk.gateway import GatewayClient, GatewayError

_USERNAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]+$")


def add_auth_parsers(sub: argparse._SubParsersAction) -> None:
    p_login = sub.add_parser("login", help="Authenticate and store a session token")
    p_login.add_argument("username", help="Account username")
    p_login.add_argument(
        "--password", "-p",
        help="Password (prompted securely if omitted)",
    )

    p_signup = sub.add_parser("signup", help="Register a new marketplace account")
    p_signup.add_argument("username", help="Desired username")
    p_signup.add_argument(
        "--password", "-p",
        help="Password (prompted securely if omitted)",
    )

    p_logout = sub.add_parser("logout", help="Clear the stored session token")
    p_logout.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation",
    )


def _gateway(args: argparse.Namespace) -> GatewayClient:
    return GatewayClient(gateway_url=getattr(args, "gateway_url", None))


def cmd_signup(args: argparse.Namespace) -> None:
    username = args.username
    if len(username) < 3:
        print("❌ Username must be at least 3 characters.", file=sys.stderr)
        sys.exit(1)
    if not _USERNAME_RE.match(username):
        print(
            "❌ Username must start with a letter and contain only letters, "
            "numbers, underscores, and hyphens.",
            file=sys.stderr,
        )
        sys.exit(1)

    password = args.password or getpass.getpass("Password: ")
    if not args.password:
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("❌ Passwords do not match.", file=sys.stderr)
            sys.exit(1)
    if len(password) < 8:
        print("❌ Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    client = _gateway(args)
    print(f"📝 Registering account '{username}'...")
    try:
        client.signup(username, password)
        print(f"✅ Account created for '{username}'")
    except GatewayError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    # Auto-login after successful signup
    try:
        result = client.login(username, password)
    except GatewayError as e:
        print(f"❌ Auto-login failed: {e}", file=sys.stderr)
        sys.exit(1)

    token = result.get("token")
    if not token:
        print("❌ Auto-login failed: no token in response", file=sys.stderr)
        sys.exit(1)
    write_token(token)
    print(f"   Logged in as '{username}'")


def cmd_login(args: argparse.Namespace) -> None:
    existing = read_token()
    if existing:
        existing_user = get_username_from_token(existing)
        if existing_user:
            print(f"🔑 Already logged in as '{existing_user}'")
            resp = input("Log in again? [y/N] ")
            if resp.lower() not in ("y", "yes"):
                print("Cancelled.")
                return

    password = args.password or getpass.getpass("Password: ")
    client = _gateway(args)
    print(f"🔑 Authenticating as '{args.username}'...")

    try:
        result = client.login(args.username, password)
    except GatewayError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    token = result.get("token")
    if not token:
        print("❌ Login failed: no token in response", file=sys.stderr)
        sys.exit(1)

    write_token(token)
    print(f"✅ Logged in as '{args.username}'")
    print("   Token stored in ~/.mpx-token")


def cmd_logout(args: argparse.Namespace) -> None:
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
