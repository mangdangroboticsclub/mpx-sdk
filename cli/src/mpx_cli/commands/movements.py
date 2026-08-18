"""mpx-cli movements / stop / safe-mode — the robot's movement list and run state.

`movements` is the answer to "what can this robot do", and the point is that
the answer is no longer a constant. A skill that declares `provides_gait` in
its manifest appears here beside the firmware's own gaits, so adding a named
movement stopped being a firmware operation.
"""

from __future__ import annotations

import argparse

from mpx_cli.sdk.connection import RobotClient


def add_movements_parser(sub: argparse._SubParsersAction) -> None:
    from mpx_cli.cli import robot_opts
    p = sub.add_parser("movements", parents=[robot_opts()],
                       help="Every movement this robot can perform, built-in and skill-provided")
    p.add_argument("--skills-only", action="store_true",
                   help="Only the ones skills provide")

    s = sub.add_parser("stop", parents=[robot_opts()],
                       help="Ask the running skill to stop (the only way to end a behaviour)")
    s.set_defaults(_stop=True)

    m = sub.add_parser("safe-mode", parents=[robot_opts()],
                       help="Show or clear autorun safe mode")
    m.add_argument("--clear", action="store_true",
                   help="Re-enable autorun after it was disabled")


def cmd_movements(args: argparse.Namespace) -> None:
    client = RobotClient(args.ip, args.port)
    data = client.movements()
    rows = data.get("movements", [])
    if args.skills_only:
        rows = [r for r in rows if r.get("source") == "skill"]

    builtin = [r for r in rows if r.get("source") != "skill"]
    skill = [r for r in rows if r.get("source") == "skill"]

    if builtin:
        print(f"Built in ({len(builtin)})\n")
        for i in range(0, len(builtin), 6):
            print("  " + "  ".join(f"{r['name']:<13}" for r in builtin[i:i + 6]).rstrip())
        print()

    if skill:
        print(f"From skills ({len(skill)})\n")
        for r in skill:
            kind = "behaviour" if r.get("behaviour") else "one-shot"
            print(f"  {r['name']:<16} {r.get('skill',''):<18} {kind}")
        print()
    elif not args.skills_only:
        print("From skills (0)\n")
        print("  None yet. Add \"provides_gait\": \"<name>\" to a skill's manifest.json,")
        print("  mpx-cli deploy it, and it appears here — and on the phone.\n")

    print(f"Run one:  mpx-cli movement <name>       (or from the robot's web UI)")


def cmd_stop(args: argparse.Namespace) -> None:
    client = RobotClient(args.ip, args.port)
    r = client.stop_skill()
    if r.get("was_running"):
        print("Asked the running skill to stop. on_stop() still runs, so it can park.")
    else:
        print("Nothing was running.")


def cmd_safe_mode(args: argparse.Namespace) -> None:
    client = RobotClient(args.ip, args.port)
    if args.clear:
        client.clear_safe_mode()
        print("Safe mode cleared — autorun will run again on the next boot.")
        return

    reg = client.registry()
    if reg.get("safe_mode"):
        print("SAFE MODE IS ON.\n")
        print("  An autorun skill failed to keep the robot up three boots in a row,")
        print("  so the firmware stopped starting it. The robot is running normally.\n")
        print("  Uninstall the skill, or:  mpx-cli safe-mode --clear")
    else:
        print("Safe mode is off; autorun is enabled.")
        auto = [s for s in reg.get("skills", []) if s.get("autorun")]
        print(f"  autorun skill: {auto[0]['slug']}" if auto else "  no skill is marked autorun.")
