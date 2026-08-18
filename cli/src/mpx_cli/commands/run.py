"""mpx-cli run — execute a skill on the robot, and report how it actually went."""

from __future__ import annotations

import argparse
import time

from mpx_cli.sdk.connection import RobotClient, RobotError
from mpx_cli.sdk.project import describe_missing, find_project

# Fast enough that a two-second skill still feels responsive, slow enough not
# to add load to an ESP32 that is also running a gait loop at the same time.
_POLL_INTERVAL_S = 0.4


def add_run_options(p: argparse.ArgumentParser) -> None:
    """Shared by `run` and `deploy` so the two behave identically."""
    p.add_argument(
        "--no-wait", action="store_true",
        help="Return as soon as the skill starts, without waiting for its result",
    )
    p.add_argument(
        "--timeout", type=int, default=70,
        help="Seconds to wait for a result (default: 70; the robot stops any "
             "skill at 60)",
    )
    p.add_argument(
        "--param", action="append", metavar="NAME=VALUE", default=[],
        help="Set a skill parameter for this run. Repeatable. The skill reads "
             "it with mpx_paramf()/mpx_parami(); anything it does not supply "
             "falls back to the skill's own default, so this is always "
             "optional. Declare parameters in manifest.json and the robot's "
             "web UI renders a control for each one.",
    )


def add_run_parser(sub: argparse._SubParsersAction) -> None:
    from mpx_cli.cli import robot_opts

    p = sub.add_parser(
        "run",
        parents=[robot_opts()],
        help="Execute a skill on the robot",
    )
    p.add_argument(
        "skill", nargs="?",
        help="Skill filename (default: <slug>.wasm from manifest.json)",
    )
    add_run_options(p)



def params_string(pairs: list[str] | None) -> str:
    """Turn --param NAME=VALUE flags into the wire format the robot parses.

    Flat "name=value;name=value" rather than JSON, because the firmware's run
    handler reads its body with strstr and putting a JSON parser on an ESP32
    to carry two floats is the wrong trade.
    """
    if not pairs:
        return ""
    out = []
    for pair in pairs:
        if "=" not in pair:
            print(f"warning: ignoring --param '{pair}' (expected NAME=VALUE)")
            continue
        name, _, value = pair.partition("=")
        name, value = name.strip(), value.strip()
        if not name:
            print(f"warning: ignoring --param '{pair}' (empty name)")
            continue
        out.append(f"{name}={value}")
    return ";".join(out)


def _resolve_skill(args: argparse.Namespace) -> str | None:
    """The robot stores skills by bare filename, not by path."""
    if args.skill:
        return args.skill

    project = find_project()
    if project is None:
        print(f"❌ {describe_missing('skill name')}")
        return None

    return project.remote_name


def wait_for_result(client: RobotClient, skill: str, timeout_s: int) -> bool:
    """Poll /v1/skills/status until the run ends, then report what happened.

    POST /v1/skills/run answers the instant the skill's task is spawned, so its
    reply is always ``started`` — it cannot be anything else, because a skill
    may run for 60 s and blocking the HTTP handler that long exhausts the
    robot's socket pool. Treating that reply as success meant a skill which
    trapped on its first instruction, or was never a valid module at all, still
    printed a green tick and exited 0. ``deploy`` inherited the same blind
    spot, so no shell chain or CI job could tell a working skill from a broken
    one.
    """
    deadline = time.monotonic() + timeout_s
    spinner = "|/-\\"
    tick = 0

    while time.monotonic() < deadline:
        time.sleep(_POLL_INTERVAL_S)

        try:
            status = client.skill_status()
        except RobotError:
            # A skill can momentarily saturate the robot, or reboot it. Keep
            # polling until the deadline rather than calling that a failure.
            continue

        if status.get("running"):
            elapsed = status.get("elapsed_ms", 0) / 1000.0
            print(f"\r   {spinner[tick % 4]} running… {elapsed:.1f}s", end="", flush=True)
            tick += 1
            continue

        last = status.get("last") or {}
        # Ignore a result left over from an earlier run of a different skill —
        # otherwise a stale success would be reported as this run's success.
        if last.get("name") and last.get("name") != skill:
            continue

        print("\r" + " " * 44 + "\r", end="")
        message = last.get("message", "finished")
        seconds = last.get("duration_ms", 0) / 1000.0

        if last.get("ok"):
            print(f"✅ {skill} — {message} ({seconds:.1f}s)")
            return True

        print(f"❌ {skill} — {message} ({seconds:.1f}s)")
        print("   'mpx-cli logs' shows what the robot logged.")
        return False

    print("\r" + " " * 44 + "\r", end="")
    print(f"⚠️  {skill} did not report a result within {timeout_s}s — it may "
          f"still be running.")
    print("   'mpx-cli logs -f' will show what it is doing.")
    return False


def cmd_run(args: argparse.Namespace) -> bool:
    skill = _resolve_skill(args)
    if skill is None:
        return False

    client = RobotClient(host=args.ip, port=args.port)

    print(f"▶️  Running '{skill}' on {client.host}:{client.port}...")

    try:
        result = client.run_skill(skill, params_string(getattr(args, "param", [])))
    except RobotError as e:
        print(f"❌ {e}")
        return False

    # The firmware answers 409 when a skill is already running — only one WASM
    # instance exists. That is a failure, not a start.
    output = str(result.get("output", ""))
    if "already running" in output:
        print(f"❌ {output}")
        return False

    if getattr(args, "no_wait", False):
        print("✅ started (not waiting for a result)")
        return True

    return wait_for_result(client, skill, getattr(args, "timeout", 70))
