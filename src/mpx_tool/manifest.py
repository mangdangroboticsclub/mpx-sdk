"""Skill manifest helpers shared by ``init``, ``publish`` and ``update-manifest``.

One manifest contract serves both skill families:

  * ``skill_type: WASM`` → robot (``mpx move …``) skills
  * ``skill_type: AWA`` / ``CAPABILITY`` → web (``mpx web …``) skills

The manifest is the source of truth for what ``mpx publish`` ships, so the
scaffolders embed the field table below in the project's own docs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

MANIFEST_NAME = "manifest.json"
WASM_TYPES = {"WASM"}
_WEB_ONLY_FIELDS = ("domain", "actions", "capabilities", "urls", "timeout", "memoryLimitMB")
_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


# ── Semver ───────────────────────────────────────────────────────

def parse_semver(v: str) -> tuple[int, int, int] | None:
    """Return ``(major, minor, patch)`` or ``None`` when ``v`` is not semver."""
    m = _SEMVER_RE.match(str(v).strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


# ── Read / write ─────────────────────────────────────────────────

def read_manifest(skill_dir: Path) -> tuple[Path, dict]:
    """Load ``<skill_dir>/manifest.json``, raising ``ValueError`` on failure."""
    path = skill_dir / MANIFEST_NAME
    if not path.exists():
        raise ValueError(f"No {MANIFEST_NAME} found in {skill_dir}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid {MANIFEST_NAME}: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"Invalid {MANIFEST_NAME}: expected a JSON object")
    return path, data


def write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def is_wasm(manifest: dict) -> bool:
    return str(manifest.get("skill_type", "AWA")).upper() in WASM_TYPES


def family_label(manifest: dict) -> str:
    return "move" if is_wasm(manifest) else "web"


# ── Docs embedded into scaffolded projects ───────────────────────

_FIELD_ROWS = (
    ("`slug`", "Skill id is `username~slug`; immutable once published."),
    ("`title`", "Listing name in the marketplace."),
    ("`version`", "Must be `X.Y.Z`. `mpx publish` offers a bump when the version already exists and rewrites this file."),
    ("`readme`", "One-paragraph summary surfaced in the marketplace listing."),
    ("`skill_type`", "{skill_type} — selects how `mpx publish` validates and ships this skill."),
    ("`source_language`", "{language}"),
)

_WEB_FIELD_ROWS = (
    ("`domain`", "Site this skill drives (AWA routing)."),
    ("`actions`", "Per-action params / returns / examples — the agent dispatches from these."),
    ("`capabilities`", "Action names advertised to the agent."),
    ("`urls`", "Known URL templates (documentation / reference)."),
    ("`timeout` / `memoryLimitMB`", "Runtime caps enforced by the sandbox."),
)

# Per-family wording: each scaffolded GUIDE only ever describes its own family.
_MOVE_DOC = {
    "skill_type": "`WASM`",
    "language": "Source language of the skill: `c`, `wat` or `ts`.",
    "command": "mpx move update-manifest .",
    "example_readme": "Faster gait start",
}
_WEB_DOC = {
    "skill_type": "`AWA`",
    "language": "`javascript` — fixed for web skills.",
    "command": "mpx web update-manifest .",
    "example_readme": "Now supports checkout",
}

_DOC_SECTION = """## Updating this GUIDE and the manifest metadata

`{manifest}` is the source of truth: `mpx publish` reads it, so anything stale
there is what users and agents see. Keep this file and the manifest in sync.

| Field | Effect |
| --- | --- |
{rows}

### Checklist when you change the skill

{checklist}

### Editing metadata

One command edits every field:

```bash
{command}
```

It prompts for each editable field with the current value as the default — press
Enter to keep it. For scripted updates, pass flags instead of prompting:

```bash
{command} --version 1.2.0 --readme "{example_readme}"
```

Editing by hand is fine too — just re-run `mpx publish .` afterwards so the
marketplace metadata matches this file.
"""

_CHECKLIST = {
    "move": (
        "Bump `version` in `{manifest}` (or let `mpx publish` bump it on conflict).",
        "Update the `readme` one-liner if the skill's purpose changed.",
        "Keep the Quick Start and Host Functions sections above in sync with the code.",
        "Update `source_language` if you switch languages (`c` / `wat` / `ts`) and keep `include/` matched.",
        "Update this doc's own prose — it is what a human reads first.",
        "`mpx publish .` to ship.",
    ),
    "web": (
        "Bump `version` in `{manifest}` (or let `mpx publish` bump it on conflict).",
        "Update the `readme` one-liner if the skill's purpose changed.",
        "Keep the handler docs above and the `actions` descriptions in `{manifest}` in sync.",
        "Update `actions` / `capabilities` / `urls` whenever behavior or reachable pages change — the agent dispatches from them.",
        "Update this doc's own prose — it is what a human reads first.",
        "`mpx publish .` to ship.",
    ),
}


def metadata_section(skill_type: str, manifest_name: str = MANIFEST_NAME) -> str:
    """Markdown block documenting manifest fields, for a scaffolded project."""
    wasm = str(skill_type).upper() in WASM_TYPES
    family = "move" if wasm else "web"
    doc = _MOVE_DOC if wasm else _WEB_DOC
    field_rows = _FIELD_ROWS if wasm else (_FIELD_ROWS + _WEB_FIELD_ROWS)
    rows = [
        "| {} | {} |".format(field, effect.format(**doc))
        for field, effect in field_rows
    ]
    body = _DOC_SECTION.format(
        manifest=manifest_name,
        rows="\n".join(rows),
        checklist="\n".join(
            f"{i}. {line.format(manifest=manifest_name)}"
            for i, line in enumerate(_CHECKLIST[family], start=1)
        ),
        command=doc["command"],
        example_readme=doc["example_readme"],
    )
    return body
