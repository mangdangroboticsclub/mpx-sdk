"""Docker auto-pull / run helpers.

- ``ensure_image`` / ``pull`` — pull a pinned image from Docker Hub.
- ``run_image`` — one-shot ``docker run --rm`` (move toolchain builds).
- ``compose_up`` / ``compose_down`` — manage the web runtime stack
  (AWA worker + GCS emulator) via a vendored compose file.
"""

from __future__ import annotations

import os
import shutil
import subprocess

from mpx_tool.config import GCS_EMULATOR_IMAGE as _GCS_IMAGE
from mpx_tool.config import WEB_WORKER_IMAGE as _WORKER_IMAGE
from pathlib import Path

import importlib.resources

DOCKER_BIN = "docker"


class DockerError(Exception):
    """Raised when Docker is unavailable or an operation fails."""


def docker_available() -> bool:
    return shutil.which(DOCKER_BIN) is not None


def _run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    if not docker_available():
        raise DockerError("Docker not found on PATH. Install Docker Desktop / Engine.")
    result = subprocess.run(cmd, capture_output=capture, text=True)
    if check and result.returncode != 0:
        # When not capturing, stdout/stderr are None (output went straight to
        # the terminal) — don't crash trying to read them.
        err = result.stderr.strip() if result.stderr else ""
        out = result.stdout.strip() if result.stdout else ""
        detail = err or out or f"exit code {result.returncode}"
        raise DockerError(f"docker command failed ({' '.join(cmd[:2])}…): {detail}")
    return result


def image_present(image: str) -> bool:
    if not docker_available():
        return False
    result = _run([DOCKER_BIN, "image", "inspect", image], check=False, capture=True)
    return result.returncode == 0


def pull(image: str) -> None:
    """Pull an image from its registry (Docker Hub by default)."""
    print(f"  ⬇️  Pulling {image}...")
    subprocess.run([DOCKER_BIN, "pull", image], check=False)


def ensure_image(image: str) -> None:
    """Pull the image if it is not already present locally."""
    if not image_present(image):
        pull(image)


def run_image(image: str, args: list[str], workdir: str | None = None, cwd: str | None = None) -> None:
    """Run a one-shot container: ``docker run --rm [-w workdir] image args``."""
    cmd = [DOCKER_BIN, "run", "--rm"]
    if workdir:
        cmd += ["-w", workdir]
    if cwd:
        # Mount the current working directory into the container.
        cmd += ["-v", f"{cwd}:/work"]
    cmd += [image, *args]
    _run(cmd)


def _compose_file() -> Path:
    """Vendored web-runtime compose file shipped with the package."""
    ref = importlib.resources.files("mpx_tool.commands.resource.web") / "docker-compose.yml"
    with importlib.resources.as_file(ref) as path:
        return Path(path)


def _compose_env() -> dict[str, str]:
    """Image env overrides so compose uses the same pins as the CLI."""
    env = os.environ.copy()
    env.setdefault("MPX_WEB_WORKER_IMAGE", _WORKER_IMAGE)
    env.setdefault("MPX_GCS_EMULATOR_IMAGE", _GCS_IMAGE)
    return env


def compose_up(project_name: str = "mpx-web") -> None:
    """Start the web runtime stack (worker + GCS emulator)."""
    compose = _compose_file()
    print("  ▶️  Starting web runtime (AWA worker + GCS emulator)...")
    cmd = [DOCKER_BIN, "compose", "-p", project_name, "-f", str(compose), "up", "-d"]
    result = subprocess.run(cmd, env=_compose_env())
    if result.returncode != 0:
        raise DockerError("docker compose up failed")
    print("  ✅ Web runtime is up — worker http://localhost:9808, GCS http://localhost:4443")


def compose_down(project_name: str = "mpx-web") -> None:
    """Stop the web runtime stack."""
    compose = _compose_file()
    print("  ⏹  Stopping web runtime...")
    cmd = [DOCKER_BIN, "compose", "-p", project_name, "-f", str(compose), "down"]
    result = subprocess.run(cmd, env=_compose_env())
    if result.returncode != 0:
        raise DockerError("docker compose down failed")
    print("  ✅ Web runtime stopped.")
