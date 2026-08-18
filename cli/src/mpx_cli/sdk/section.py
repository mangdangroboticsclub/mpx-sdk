"""Carry a skill's manifest inside the .wasm itself.

The robot needs to know more about a skill than "here is some bytecode": which
gait name it provides, whether it should start at boot, what events should
trigger it. That metadata has to reach the firmware somehow, and every obvious
route is worse than this one.

  * A sidecar file uploaded next to the .wasm can be lost, skipped by an older
    CLI, or left behind after an uninstall.
  * A field in the upload request works for `mpx-cli` and not for a marketplace
    install, which is a different code path.
  * A record in /installed.json is written by the install path only, so a
    plain `mpx-cli deploy` would produce a skill the registry cannot see.

A WebAssembly custom section travels inside the artifact. Whatever moves the
module -- the CLI, the marketplace, a USB stick, someone emailing a .wasm to a
friend -- moves the metadata with it, and the two cannot drift apart because
they are the same file.

The section is named "mpx" and holds the manifest's declarative fields as JSON.
Custom sections are ignored by every WebAssembly runtime that does not know
them, so a module with one still runs anywhere.
"""

from __future__ import annotations

import json
from pathlib import Path

SECTION_NAME = b"mpx"

# Only the fields the firmware acts on. Deliberately not the whole manifest:
# a title and a readme are the marketplace's business, and every byte here is
# flash on a device that has 2.5 MB of it.
EMBEDDED_FIELDS = ("slug", "version", "abi", "provides_gait", "autorun",
                   "on", "behaviour", "params")


def _leb128(n: int) -> bytes:
    """Unsigned LEB128 — how WebAssembly writes every length."""
    out = bytearray()
    while True:
        byte = n & 0x7F
        n >>= 7
        out.append(byte | (0x80 if n else 0))
        if not n:
            return bytes(out)


def build_section(manifest: dict) -> bytes:
    """The raw bytes of an `mpx` custom section for this manifest."""
    payload = {k: manifest[k] for k in EMBEDDED_FIELDS if k in manifest}
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    contents = _leb128(len(SECTION_NAME)) + SECTION_NAME + body
    return b"\x00" + _leb128(len(contents)) + contents


def strip_section(wasm: bytes) -> bytes:
    """Remove any existing `mpx` section, so rebuilds do not accumulate them.

    Walks the section list properly rather than searching for bytes: a module's
    code segment can contain anything, including something that looks like a
    section header.
    """
    if len(wasm) < 8 or wasm[:4] != b"\x00asm":
        return wasm

    out = bytearray(wasm[:8])
    i = 8
    while i < len(wasm):
        start = i
        section_id = wasm[i]
        i += 1
        size, shift = 0, 0
        while i < len(wasm):
            byte = wasm[i]
            i += 1
            size |= (byte & 0x7F) << shift
            if not byte & 0x80:
                break
            shift += 7
        body_start, body_end = i, i + size
        if body_end > len(wasm):
            return wasm                      # truncated; leave it alone

        drop = False
        if section_id == 0:                  # custom section
            j, nshift, nlen = body_start, 0, 0
            while j < body_end:
                byte = wasm[j]
                j += 1
                nlen |= (byte & 0x7F) << nshift
                if not byte & 0x80:
                    break
                nshift += 7
            drop = wasm[j:j + nlen] == SECTION_NAME

        if not drop:
            out += wasm[start:body_end]
        i = body_end

    return bytes(out)


def read_section(wasm: bytes) -> dict | None:
    """The manifest embedded in a module, or None if it carries no `mpx`."""
    if len(wasm) < 8 or wasm[:4] != b"\x00asm":
        return None

    i = 8
    while i < len(wasm):
        section_id = wasm[i]
        i += 1
        size, shift = 0, 0
        while i < len(wasm):
            byte = wasm[i]
            i += 1
            size |= (byte & 0x7F) << shift
            if not byte & 0x80:
                break
            shift += 7
        body_start, body_end = i, i + size
        if body_end > len(wasm):
            return None

        if section_id == 0:
            j, nshift, nlen = body_start, 0, 0
            while j < body_end:
                byte = wasm[j]
                j += 1
                nlen |= (byte & 0x7F) << nshift
                if not byte & 0x80:
                    break
                nshift += 7
            if wasm[j:j + nlen] == SECTION_NAME:
                try:
                    return json.loads(wasm[j + nlen:body_end].decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return None
        i = body_end

    return None


def embed(wasm_path: Path, manifest: dict) -> int:
    """Rewrite `wasm_path` carrying this manifest. Returns the section size.

    Appending is legal: a custom section may appear anywhere in the section
    sequence, including after the code section, and a runtime that does not
    recognise the name skips it.
    """
    raw = wasm_path.read_bytes()
    section = build_section(manifest)
    wasm_path.write_bytes(strip_section(raw) + section)
    return len(section)
