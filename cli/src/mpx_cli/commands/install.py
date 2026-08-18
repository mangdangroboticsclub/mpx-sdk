"""mpx-cli install — put a marketplace skill on the robot.

This is the half of the marketplace that did not exist. `publish` pushed a
skill UP; nothing in the CLI could bring one back DOWN. `GatewayClient` had no
download method at all, and `upload` only ever read a local file — so the only
skills the CLI could put on a robot were ones you had compiled yourself
moments earlier.

The browser had a substitute, and it is the reason this command exists rather
than a nicer version of that one: purchased WASM bytes travelled *inside a
generated Lua program*, POSTed to /v1/lua/enqueue, written to
/lua/_deploy_N.lua, then interpreted so a file_write() binding could decode
them onto flash. Each write popped a permission modal with a 60 s timeout, the
enqueue endpoint answered "ok" before the Lua had run so nothing could report
failure, and a 256 KB skill needed ~340 KB of base64 in one contiguous ESP32
allocation — which is more than the heap reliably has.

Here the bytes go straight from the gateway to POST /v1/skills/upload, the
path that already carries every `mpx-cli deploy`. No Lua, no base64 inflation,
no permission prompt, and the robot records what it installed.
"""

from __future__ import annotations

import argparse

from mpx_cli.sdk.connection import RobotClient, RobotError
from mpx_cli.sdk.gateway import GatewayClient, GatewayError

# Matches the firmware's own cap (http_server.cc) and publish's check.
MAX_SKILL_BYTES = 256 * 1024


def add_install_parser(sub: argparse._SubParsersAction) -> None:
    from mpx_cli.cli import robot_opts

    p = sub.add_parser(
        "install",
        parents=[robot_opts()],
        help="Download a marketplace skill and put it on the robot",
    )
    p.add_argument("skill_id", help="Marketplace skill id (see 'mpx-cli search')")
    p.add_argument("--version", default=None, help="Specific version (default: latest)")
    p.add_argument("--url", default=None,
                   help="Download from this URL instead of asking the gateway")
    p.add_argument("--name", default=None,
                   help="Filename on the robot (default: derived from the skill id)")
    p.add_argument("--run", action="store_true", help="Run it once installed")


def _remote_name(skill_id: str, explicit: str | None) -> str:
    """A safe bare filename. The firmware rejects anything else.

    Marketplace ids look like `username~slug`, and neither `~` nor `/` survives
    the robot's filename validator — so derive a plain name from the slug part
    rather than letting the upload fail after the download.
    """
    if explicit:
        return explicit if explicit.endswith((".wasm", ".mpxe")) else explicit + ".wasm"

    slug = skill_id.split("~")[-1]
    safe = "".join(c if (c.isalnum() or c in "_-") else "_" for c in slug)
    return (safe or "skill") + ".wasm"


def cmd_install(args: argparse.Namespace) -> bool:
    gateway = GatewayClient(getattr(args, "gateway_url", None))
    client = RobotClient(host=args.ip, port=args.port)

    # ── 1. Metadata, for the provenance record and a readable message ──────
    title, version = args.skill_id, args.version or ""
    try:
        info = gateway.get_skill(args.skill_id)
        title = info.get("title") or title
        version = version or str(info.get("current_version") or "")
    except GatewayError:
        # Not fatal — a gateway that cannot describe a skill may still serve it.
        pass

    print(f"📦 {title}" + (f" v{version}" if version else ""))

    # ── 2. Download ───────────────────────────────────────────────────────
    print(f"⬇️  Downloading from the marketplace...")
    try:
        data = gateway.download_artifact(args.skill_id, args.version, args.url)
    except GatewayError as e:
        print(f"❌ {e}")
        return False

    # ── 3. Check it before it reaches the robot ───────────────────────────
    # The robot would reject a bad module too, but only after a 256 KB upload
    # over Wi-Fi and with a much vaguer error.
    if not data.startswith(b"\x00asm"):
        print(f"❌ That is not a WebAssembly module — it does not start with the "
              f"\\0asm magic bytes ({len(data)} bytes received).")
        print("   The gateway may have returned an error page or an HTML redirect.")
        return False
    if len(data) > MAX_SKILL_BYTES:
        print(f"❌ Too large: {len(data)} bytes, and the robot's limit is "
              f"{MAX_SKILL_BYTES}.")
        return False

    remote = _remote_name(args.skill_id, args.name)
    print(f"   {len(data)} bytes → {remote}")

    # ── 4. Upload, recording where it came from ───────────────────────────
    print(f"📤 Uploading to {client.host}:{client.port}...")
    try:
        result = client.upload_skill_bytes(
            data, remote,
            skill_id=args.skill_id, version=version, title=title,
        )
    except RobotError as e:
        print(f"❌ {e}")
        return False

    if not result.get("ok"):
        print(f"❌ Upload rejected: {result}")
        return False

    print(f"✅ Installed '{remote}'")
    print(f"   The robot now records this as {args.skill_id}, so any device "
          f"can see it and uninstall it.")

    if not args.run:
        print(f"   Run it with: mpx-cli run {remote}")
        return True

    from mpx_cli.commands.run import wait_for_result
    print()
    try:
        client.run_skill(remote)
    except RobotError as e:
        print(f"❌ {e}")
        return False
    return wait_for_result(client, remote, 70)
