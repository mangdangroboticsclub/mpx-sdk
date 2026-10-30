"""HTTP client for the MPX-Dog robot (move family)."""

from __future__ import annotations

import json
import os
import sys
from typing import Any
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from mpx_tool.config import DEFAULT_ROBOT_HOST, DEFAULT_ROBOT_PORT


class RobotError(Exception):
    """Raised when the robot returns a non-OK response."""


class RobotClient:
    """HTTP client for the MPX-Dog robot's REST API."""

    def __init__(self, host: str = DEFAULT_ROBOT_HOST, port: int = DEFAULT_ROBOT_PORT) -> None:
        self.host = host
        self.port = port
        self._base = f"http://{host}:{port}"

    def _url(self, path: str) -> str:
        return urljoin(self._base, path)

    def _request(
        self,
        method: str,
        path: str,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        url = self._url(path)
        req = Request(url, data=data, method=method)
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        try:
            with urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8")
                if resp.status == 200 and body:
                    return json.loads(body)
                return {"ok": resp.status == 200}
        except URLError as e:
            raise RobotError(f"Connection to {self.host}:{self.port} failed: {e}") from e
        except json.JSONDecodeError as e:
            raise RobotError(f"Invalid JSON from robot: {e}") from e

    # ── Skills API ───────────────────────────────────────────────

    def list_skills(self) -> list[dict[str, Any]]:
        """List all .wasm skills installed on the robot."""
        result = self._request("GET", "/v1/skills/list")
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "skills" in result:
            return list(result["skills"])
        return []

    def upload_skill(self, wasm_path: str) -> dict[str, Any]:
        """Upload a .wasm file to the robot (raw binary body)."""
        filename = os.path.basename(wasm_path)
        if not filename.endswith(".wasm"):
            print("⚠️  Warning: file does not end with .wasm", file=sys.stderr)

        with open(wasm_path, "rb") as f:
            data = f.read()

        if len(data) == 0:
            raise RobotError("Empty file — nothing to upload")
        if len(data) > 256 * 1024:
            raise RobotError(f"File too large ({len(data)} bytes) — max is 256 KB")

        headers = {"Content-Type": "application/octet-stream"}
        return self._request("POST", f"/v1/skills/upload?name={filename}", data=data, headers=headers)

    def run_skill(self, skill_name: str) -> dict[str, Any]:
        """Execute a skill by filename on the robot."""
        payload = json.dumps({"skill": skill_name}, separators=(",", ":")).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        return self._request("POST", "/v1/skills/run", data=payload, headers=headers)

    # ── File system API ──────────────────────────────────────────

    def list_files(self) -> list[dict[str, Any]]:
        """List all files on the robot's LittleFS."""
        result = self._request("GET", "/v1/fs/list")
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "files" in result:
            return list(result["files"])
        return []

    def fs_info(self) -> dict[str, Any]:
        return self._request("GET", "/v1/fs/info")

    def delete_file(self, path: str) -> dict[str, Any]:
        """Delete a file from the robot's LittleFS."""
        payload = json.dumps({"path": path}, separators=(",", ":")).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        return self._request("POST", "/v1/fs/delete", data=payload, headers=headers)

    # ── Robot status ─────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        return self._request("GET", "/v1/robot/status")

    def __repr__(self) -> str:
        return f"RobotClient(host={self.host!r}, port={self.port})"
