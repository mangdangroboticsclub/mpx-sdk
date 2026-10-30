"""HTTP client for the AWA worker (web family runtime)."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from mpx_tool.config import DEFAULT_AWA_WORKER_URL


class AwaWorkerError(Exception):
    """Raised when the AWA worker is unreachable or returns an error."""


class AwaWorkerClient:
    """HTTP client for the AWA worker REST API (session lifecycle)."""

    def __init__(self, worker_url: str | None = None) -> None:
        self._base = (worker_url or DEFAULT_AWA_WORKER_URL).rstrip("/")

    def _url(self, path: str) -> str:
        return urljoin(self._base + "/", path.lstrip("/"))

    def _send(self, method: str, path: str, body: dict[str, Any] | None = None, timeout: int = 60) -> Any:
        url = self._url(path)
        data = json.dumps(body).encode("utf-8") if body else None
        req = Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except URLError as e:
            raise AwaWorkerError(f"Worker request failed ({method} {path}): {e}") from e
        except json.JSONDecodeError as e:
            raise AwaWorkerError(f"Invalid JSON from worker: {e}") from e

    # ── Session endpoints ────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        return self._send("GET", "/healthz", timeout=10)

    def start_session(self, skill_id: str, version: str, robot_uuid: str) -> dict[str, Any]:
        return self._send("POST", "/v1/awa/session/start", {
            "skill_id": skill_id,
            "version": version,
            "robot_uuid": robot_uuid,
        })

    def get_session(self, session_id: str) -> dict[str, Any]:
        return self._send("GET", f"/v1/awa/session/{session_id}", timeout=10)

    def action(self, session_id: str, action: str, params: dict[str, Any]) -> dict[str, Any]:
        return self._send("POST", f"/v1/awa/session/{session_id}/action", {
            "action": action,
            "params": params,
        })

    def end_session(self, session_id: str) -> dict[str, Any]:
        return self._send("POST", f"/v1/awa/session/{session_id}/end")
