"""mpx web session — manage AWA sessions against the worker.

Usage:
  mpx web session start <skill_id> --robot <uuid>
  mpx web session list
  mpx web session get <session_id>
  mpx web session action <session_id> <action> [params_json]
  mpx web session end <session_id>
"""

from __future__ import annotations

import argparse
import json
import sys

from mpx_tool.sdk.awa_worker import AwaWorkerClient, AwaWorkerError
from mpx_tool.sdk.gateway import GatewayClient, GatewayError


def add_web_session_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("session", help="Manage AWA worker sessions")
    p_sub = p.add_subparsers(dest="session_command", required=True)

    p_start = p_sub.add_parser("start", help="Create a new session")
    p_start.add_argument("skill_id", help="Skill ID (e.g. username~slug)")
    p_start.add_argument("--robot", required=True, help="Robot UUID")

    p_sub.add_parser("list", help="List active sessions (worker health)")

    p_get = p_sub.add_parser("get", help="Get session status")
    p_get.add_argument("session_id", help="Session ID")

    p_action = p_sub.add_parser("action", help="Dispatch an action")
    p_action.add_argument("session_id", help="Session ID")
    p_action.add_argument("action", help="Action name")
    p_action.add_argument("params_json", nargs="?", default=None, help="Optional JSON params string")

    p_end = p_sub.add_parser("end", help="End a session")
    p_end.add_argument("session_id", help="Session ID")


def _gateway(args: argparse.Namespace) -> GatewayClient:
    return GatewayClient(gateway_url=getattr(args, "gateway_url", None))


def cmd_web_session(args: argparse.Namespace) -> None:
    worker = AwaWorkerClient(worker_url=getattr(args, "worker_url", None))
    command = args.session_command

    try:
        if command == "start":
            _cmd_start(args, worker)
        elif command == "list":
            _cmd_list(worker)
        elif command == "get":
            _cmd_get(args, worker)
        elif command == "action":
            _cmd_action(args, worker)
        elif command == "end":
            _cmd_end(args, worker)
    except AwaWorkerError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_start(args: argparse.Namespace, worker: AwaWorkerClient) -> None:
    skill_id = args.skill_id
    robot_uuid = args.robot
    gateway = _gateway(args)

    # Verify the skill exists on the gateway.
    try:
        skill = gateway.get_skill(skill_id)
    except GatewayError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    if not skill:
        print(f'❌ Skill "{skill_id}" not found on gateway', file=sys.stderr)
        sys.exit(1)
    version = f"v{skill.get('current_version', skill.get('version', '?'))}"

    # Verify the skill is assigned to the robot.
    try:
        robot_skills = gateway.get_robot_skills(robot_uuid)
    except GatewayError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    assigned = next((s for s in robot_skills if s.get("skill_id") == skill_id), None)
    if not assigned:
        ids = ", ".join(str(s.get("skill_id")) for s in robot_skills)
        print(f'❌ Skill "{skill_id}" is not assigned to robot "{robot_uuid}"', file=sys.stderr)
        print(f"Assigned skills: {ids or '(none)'}", file=sys.stderr)
        sys.exit(1)
    print(f'  ✓ Skill "{skill_id}" verified for robot {robot_uuid}')

    result = worker.start_session(skill_id, version, robot_uuid)
    print(json.dumps(result, indent=2))


def _cmd_list(worker: AwaWorkerClient) -> None:
    result = worker.health()
    print(f"Active sessions: {result.get('activeSessions')} / {result.get('maxSessions')}")
    print(f"Worker status:   {result.get('status')}")
    print(f"Chromium:        {result.get('chromiumStatus')}")


def _cmd_get(args: argparse.Namespace, worker: AwaWorkerClient) -> None:
    result = worker.get_session(args.session_id)
    print(json.dumps(result, indent=2))


def _cmd_action(args: argparse.Namespace, worker: AwaWorkerClient) -> None:
    params: dict = {}
    if args.params_json:
        try:
            params = json.loads(args.params_json)
        except json.JSONDecodeError:
            print("❌ params_json must be valid JSON", file=sys.stderr)
            sys.exit(1)

    result = worker.action(args.session_id, args.action, params)
    if result.get("status") == "success":
        print(json.dumps(result.get("data"), indent=2))
    else:
        print(f"Status: {result.get('status')}")
        if result.get("errorDetails"):
            print(f"Error:  {result.get('errorDetails')}")


def _cmd_end(args: argparse.Namespace, worker: AwaWorkerClient) -> None:
    result = worker.end_session(args.session_id)
    print(json.dumps(result, indent=2))
