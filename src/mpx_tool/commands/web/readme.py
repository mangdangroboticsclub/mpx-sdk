"""mpx web readme — display a skill's manifest/readme from the gateway."""

from __future__ import annotations

import argparse
import json
import sys
import textwrap

from mpx_tool.sdk.gateway import GatewayClient, GatewayError


def add_web_readme_parser(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("readme", help="Show a skill's manifest/readme from the gateway")
    p.add_argument("skill_id", help="Skill ID (e.g. username~slug)")
    p.add_argument("--json", action="store_true", help="Output raw manifest JSON")
    p.add_argument("--version", default=None, help="Fetch a specific version")


def _wrap(text: str, width: int = 72) -> list[str]:
    return textwrap.wrap(text, width) or [""]


def _render(manifest: dict) -> str:
    lines: list[str] = []
    name = manifest.get("title") or manifest.get("name") or manifest.get("skill_name") or "Unknown Skill"
    lines.append(f"✨ {name}\n")

    if manifest.get("domain"):
        lines.append(f"  Domain:    {manifest['domain']}")
    if manifest.get("slug"):
        lines.append(f"  Slug:      {manifest['slug']}")
    type_str = " · ".join(filter(None, [manifest.get("skill_type"), manifest.get("source_language")]))
    if type_str:
        lines.append(f"  Type:      {type_str}")
    if manifest.get("version"):
        lines.append(f"  Version:   {manifest['version']}")
    if manifest.get("author"):
        lines.append(f"  Author:    {manifest['author']}")
    lines.append("")

    readme_text = manifest.get("readme") or manifest.get("description") or manifest.get("summary") or ""
    if readme_text:
        lines.append("  📖 Readme")
        for line in _wrap(str(readme_text)):
            lines.append(f"  {line}")
        lines.append("")

    caps = manifest.get("capabilities") or manifest.get("endpoints") or []
    if isinstance(caps, list) and caps:
        lines.append(f"  🛠️ Capabilities ({len(caps)})")
        lines.append(f"  {', '.join(str(c) for c in caps)}")
        lines.append("")

    actions = manifest.get("actions") or {}
    if isinstance(actions, dict) and actions:
        lines.append("  ⚡ Actions")
        max_name_len = max((len(str(k)) for k in actions), default=10)
        for key, act in actions.items():
            desc = act if isinstance(act, str) else (act or {}).get("description", "")
            lines.append(f"  {str(key):<{max_name_len + 2}} {desc}")
        lines.append("")

    urls = manifest.get("urls") or {}
    if isinstance(urls, dict) and urls:
        lines.append("  🔗 URLs")
        max_key_len = max((len(str(k)) for k in urls), default=8)
        for key, val in urls.items():
            lines.append(f"  {str(key):<{max_key_len + 2}} {val}")
        lines.append("")

    return "\n".join(lines)


def cmd_web_readme(args: argparse.Namespace) -> None:
    if not args.skill_id:
        print("Error: missing skill_id.\nUsage: mpx web readme <skill_id>", file=sys.stderr)
        sys.exit(1)

    client = GatewayClient(gateway_url=getattr(args, "gateway_url", None))

    try:
        manifest = client.get_manifest(args.skill_id, version=args.version)
    except GatewayError as e:
        print(f"  ✗ {e}", file=sys.stderr)
        sys.exit(1)

    if not manifest:
        print(f'  ✗ Skill "{args.skill_id}" not found', file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        print(_render(manifest))
