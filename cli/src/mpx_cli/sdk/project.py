"""Project resolution — find the skill project you are standing in.

Every scaffolded skill already carries a ``manifest.json`` at its root
(written by ``commands/init.py``), and it already holds the one identifier
everything else is derived from: the slug. Until now only ``publish`` read it,
so the same name had to be retyped in four different spellings across a loop
developers run dozens of times a day::

    mpx-cli build  src/my_skill.c
    mpx-cli upload build/my_skill.wasm
    mpx-cli run    my_skill.wasm

This module lets the other commands derive those paths instead. It introduces
no new file format and needs no migration — it reads the manifest that is
already there.

The resolution order for every command is:

    explicit CLI argument  ->  project manifest  ->  a clear error

so passing a path always wins and nothing that worked before changes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

MANIFEST_NAME = "manifest.json"

# Extensions the toolchain can compile, in the order we probe for them.
# Matches the dispatch table in ``sdk/toolchain.py``.
SOURCE_EXTENSIONS = (".c", ".cc", ".cpp", ".wat", ".ts")


@dataclass(frozen=True)
class Project:
    """A skill project: the directory holding ``manifest.json``."""

    root: Path
    slug: str
    manifest: dict

    @property
    def source(self) -> Path | None:
        """``src/<slug>.<ext>`` for the first extension that exists on disk.

        Returns None when no source file matches the slug — e.g. the file was
        renamed without updating the manifest. Callers should fall back to
        asking for an explicit path rather than guessing further.
        """
        src_dir = self.root / "src"
        for ext in SOURCE_EXTENSIONS:
            candidate = src_dir / f"{self.slug}{ext}"
            if candidate.exists():
                return candidate
        return None

    @property
    def wasm(self) -> Path:
        """``build/<slug>.wasm`` — where ``build`` puts its output."""
        return self.root / "build" / f"{self.slug}.wasm"

    @property
    def remote_name(self) -> str:
        """The bare filename the robot stores a skill under.

        ``run`` and ``delete`` take this form, not a path — the file lives on
        the robot's filesystem, not yours.
        """
        return f"{self.slug}.wasm"


def find_project(start: Path | None = None) -> Project | None:
    """Walk up from ``start`` (default: cwd) looking for ``manifest.json``.

    Returns None rather than raising when there is no project, or when the
    manifest is unreadable or has no ``slug`` — the caller decides whether a
    missing project is an error, because for ``build`` it is not (you may
    legitimately pass a bare source path from anywhere).
    """
    here = (start or Path.cwd()).resolve()

    for directory in (here, *here.parents):
        manifest_path = directory / MANIFEST_NAME
        if not manifest_path.is_file():
            continue

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            # A malformed manifest higher up should not mask a good one, but
            # in practice projects do not nest — stop and let the caller fall
            # back to explicit arguments.
            return None

        if not isinstance(manifest, dict):
            return None

        slug = manifest.get("slug")
        if not slug or not isinstance(slug, str):
            return None

        return Project(root=directory, slug=slug, manifest=manifest)

    return None


def project_for_source(source: str | None) -> Project | None:
    """The project a command should act on, given its optional source argument.

    ``find_project()`` alone answers "which project am I standing in", which is
    the wrong question the moment an argument is passed. ``mpx-cli deploy
    four-ways`` run from ``examples/`` would build *four-ways* and then upload
    and run whatever the *current* directory's manifest named — or nothing at
    all, since ``examples/`` has no manifest. Anchoring on the argument keeps
    all three steps talking about the same skill.

    With no argument this is exactly ``find_project()``, so the bare
    ``mpx-cli deploy`` loop is unchanged.
    """
    if not source:
        return find_project()

    given = Path(source)
    return find_project(given if given.is_dir() else given.parent)


def describe_missing(what: str) -> str:
    """The error text shown when a path could not be inferred.

    Names both escape routes, because "not found" on its own leaves the user
    guessing which of the two they got wrong.
    """
    return (
        f"No {what} given and no {MANIFEST_NAME} found in this directory or "
        f"any parent.\n"
        f"   Either pass the path explicitly, or run this from inside a skill "
        f"project (one created by 'mpx-cli init')."
    )
