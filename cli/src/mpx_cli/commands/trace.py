"""mpx-cli trace — watch the numbers a running skill emits.

print() answers "did I get here". It does not answer "what is my knee error
doing", and a control loop you cannot see is one you end up debugging by
building firmware and watching a serial monitor. mpx_trace() plus this command
is the alternative.

Polls /v1/trace the way `logs` polls /v1/logs: sequence-numbered, so nothing is
missed and nothing is shown twice, and a reader that falls behind resumes from
the oldest sample still held rather than failing.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict

from mpx_cli.sdk.connection import RobotClient

BARS = " ▁▂▃▄▅▆▇█"


def add_trace_parser(sub: argparse._SubParsersAction) -> None:
    from mpx_cli.cli import robot_opts
    p = sub.add_parser("trace", parents=[robot_opts()],
                       help="Plot the named numbers a running skill emits")
    p.add_argument("--signal", "-s", action="append", default=None,
                   help="Only this signal; repeatable. Default: all of them.")
    p.add_argument("--csv", action="store_true",
                   help="Write CSV to stdout instead of drawing (for a real plot)")
    p.add_argument("--once", action="store_true",
                   help="Print what is buffered and exit, instead of following")
    p.add_argument("--interval", type=float, default=0.25,
                   help="Seconds between polls (default: 0.25)")


def _sparkline(values: list[float], width: int = 42) -> tuple[str, float, float]:
    if not values:
        return "", 0.0, 0.0
    window = values[-width:]
    lo, hi = min(window), max(window)
    span = hi - lo
    if span < 1e-9:
        return BARS[4] * len(window), lo, hi
    out = "".join(BARS[min(8, max(0, int((v - lo) / span * 8)))] for v in window)
    return out, lo, hi


def cmd_trace(args: argparse.Namespace) -> None:
    client = RobotClient(args.ip, args.port)
    wanted = set(args.signal) if args.signal else None

    since = 0
    series: dict[str, list[float]] = defaultdict(list)
    latest: dict[str, float] = {}
    total = 0
    drawn = 0

    if args.csv:
        print("t_ms,signal,value")

    if not args.csv and not args.once:
        print("Watching /v1/trace — run a skill that calls mpx_trace(). Ctrl-C to stop.\n")

    try:
        while True:
            try:
                payload = client.trace(since=since, max_samples=400)
            except Exception as exc:
                print(f"! {type(exc).__name__}: {exc}", file=sys.stderr)
                if args.once:
                    raise SystemExit(1)
                time.sleep(1.0)
                continue

            samples = payload.get("samples", [])
            since = payload.get("next", since)

            for s in samples:
                name = s.get("n", "?")
                if wanted and name not in wanted:
                    continue
                value = s.get("v")
                if value is None:          # the firmware sends null for NaN
                    continue
                total += 1
                latest[name] = value
                series[name].append(value)
                if len(series[name]) > 400:
                    del series[name][:-400]
                if args.csv:
                    print(f"{s.get('t', 0)},{name},{value}")

            if args.csv:
                sys.stdout.flush()
            elif series:
                # Redraw in place: one line per signal, newest on the right.
                if drawn:
                    sys.stdout.write(f"\x1b[{drawn}A")
                drawn = 0
                for name in sorted(series):
                    spark, lo, hi = _sparkline(series[name])
                    sys.stdout.write(
                        f"\x1b[2K  {name:<15} {latest[name]:>9.3f}  "
                        f"{spark}  [{lo:.2f} .. {hi:.2f}]\n")
                    drawn += 1
                sys.stdout.flush()

            if args.once:
                break
            time.sleep(args.interval)

    except KeyboardInterrupt:
        pass

    if not args.csv:
        if total:
            print(f"\n{total} sample(s), {len(series)} signal(s).")
        else:
            print("\nNo samples. The robot only has them while a skill that calls "
                  "mpx_trace() is running —\ntry: mpx-cli deploy examples/06-together")
