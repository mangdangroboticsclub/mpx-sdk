"""mpx-cli logs — read the robot's own log over Wi-Fi.

Everything the firmware knows about a failing skill already goes to ESP_LOGx:
the gait name that did not match, the servo id that was out of range, the WAMR
trap message and the line WAMR prints when a skill was built against an older
ABI. All of it went to a UART, which is invisible to anyone developing over
Wi-Fi — so from the developer's side a broken skill and a working one looked
identical.

The robot keeps the last few hundred lines in a small RAM ring
(``main/util/log_ring.cc``) and serves them from ``GET /v1/logs``. Each response
carries a ``next`` sequence number; passing it back as ``since`` reads
incrementally, so following the log never repeats a line and never skips one.

Polling rather than a WebSocket is deliberate: httpd runs with
``max_open_sockets = 5`` and LRU purging, so a permanently-held log socket
would be a fifth of the budget and could get itself — or the chat socket —
evicted.
"""

from __future__ import annotations

import argparse
import time

from mpx_cli.sdk.connection import RobotClient, RobotError

# Slow enough not to bother an ESP32 that is also running a gait loop, fast
# enough to feel live while you watch a skill run.
_FOLLOW_INTERVAL_S = 0.7


def add_logs_parser(sub: argparse._SubParsersAction) -> None:
    from mpx_cli.cli import robot_opts

    p = sub.add_parser(
        "logs",
        parents=[robot_opts()],
        help="Show the robot's log (use -f to follow)",
    )
    p.add_argument(
        "-f", "--follow", action="store_true",
        help="Keep polling and print new lines as they appear (Ctrl-C to stop)",
    )
    p.add_argument(
        "-n", "--lines", type=int, default=200,
        help="How many past lines to show first (default: 200)",
    )


def _print(lines: list[str]) -> None:
    for line in lines:
        print(line)


def cmd_logs(args: argparse.Namespace) -> bool:
    client = RobotClient(host=args.ip, port=args.port)

    try:
        first = client.logs(since=0, max_lines=max(1, args.lines))
    except RobotError as e:
        print(f"❌ {e}")
        # The endpoint is new, so an old firmware answers 404. Say so, rather
        # than letting it look like the robot is unreachable.
        print("   If the robot is reachable but this fails, its firmware may "
              "predate /v1/logs — reflash it.")
        return False

    _print(first.get("lines", []))
    since = int(first.get("next", 0))

    if not args.follow:
        return True

    print(f"— following {client.host}:{client.port} (Ctrl-C to stop) —")
    try:
        while True:
            time.sleep(_FOLLOW_INTERVAL_S)
            try:
                batch = client.logs(since=since, max_lines=200)
            except RobotError:
                # A robot that reboots mid-follow, or a dropped connection, is
                # normal during development. Keep trying rather than exiting;
                # the sequence number resets on reboot and the next successful
                # poll resyncs from the oldest line held.
                continue
            _print(batch.get("lines", []))
            since = int(batch.get("next", since))
    except KeyboardInterrupt:
        print()
        return True
