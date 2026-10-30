"""HTTP client for the MPX marketplace gateway.

Portable — Python stdlib only (urllib). Mirrors the upstream
``mpx-cli`` gateway client but with a generalized ``publish`` that
accepts ``skill_type``/``source_language`` so one code path serves
both the WASM ("move") and AWA ("web") skill families.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from mpx_tool.config import DEFAULT_GATEWAY_URL


class GatewayError(Exception):
    """Raised when the gateway returns a non-OK response or is unreachable."""


class GatewayClient:
    """HTTP client for the MPX marketplace gateway REST API."""

    def __init__(self, gateway_url: str | None = None) -> None:
        self._base = (gateway_url or DEFAULT_GATEWAY_URL).rstrip("/")

    # ── Low-level helpers ────────────────────────────────────────

    def _url(self, path: str) -> str:
        return urljoin(self._base + "/", path.lstrip("/"))

    def _request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        token: str | None = None,
    ) -> Any:
        url = self._url(path)
        body = json.dumps(data, separators=(",", ":")).encode("utf-8") if data else None
        req = Request(url, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", f"Bearer {token}")

        try:
            with urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except URLError as e:
            raise GatewayError(f"Connection to gateway at {self._base} failed: {e}") from e
        except json.JSONDecodeError as e:
            raise GatewayError(f"Invalid JSON from gateway: {e}") from e

    def _request_with_status(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        token: str | None = None,
    ) -> tuple[int, Any]:
        """Send a request and return ``(status_code, parsed_body)``."""
        url = self._url(path)
        body = json.dumps(data, separators=(",", ":")).encode("utf-8") if data else None
        req = Request(url, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", f"Bearer {token}")

        try:
            with urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return resp.status, (json.loads(raw) if raw else {})
        except URLError as e:
            if getattr(e, "code", None) is not None:
                try:
                    raw_body = e.read().decode("utf-8")
                    parsed = json.loads(raw_body) if raw_body else {}
                    return e.code, parsed
                except Exception:
                    return e.code, {"error": str(e)}
            raise GatewayError(
                f"Connection to gateway at {self._base} failed: {e}"
            ) from e
        except json.JSONDecodeError as e:
            raise GatewayError(f"Invalid JSON from gateway: {e}") from e

    # ── Auth endpoints ───────────────────────────────────────────

    def signup(self, username: str, password: str) -> dict[str, Any]:
        """POST /v1/auth/signup"""
        return self._request("POST", "/v1/auth/signup", {
            "username": username,
            "password": password,
        })

    def login(self, username: str, password: str) -> dict[str, Any]:
        """POST /v1/auth/login  →  {"token": "..."}"""
        return self._request("POST", "/v1/auth/login", {
            "username": username,
            "password": password,
        })

    def refresh_token(self, token: str) -> dict[str, Any]:
        """POST /v1/auth/refresh"""
        return self._request("POST", "/v1/auth/refresh", token=token)

    # ── Skill discovery endpoints ────────────────────────────────

    def list_skills(self) -> list[dict[str, Any]]:
        """GET /v1/skills"""
        result = self._request("GET", "/v1/skills")
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "skills" in result:
            return list(result["skills"])
        return []

    def get_skill(self, skill_id: str) -> dict[str, Any]:
        """GET /v1/skills/:id"""
        return self._request("GET", f"/v1/skills/{skill_id}")

    def get_versions(self, skill_id: str) -> list[dict[str, Any]]:
        """GET /v1/skills/:id/versions"""
        result = self._request("GET", f"/v1/skills/{skill_id}/versions")
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "versions" in result:
            return list(result["versions"])
        return []

    def get_manifest(self, skill_id: str, version: str | None = None) -> dict[str, Any]:
        """GET /v1/skills/:id/manifest[?version=]"""
        path = f"/v1/skills/{skill_id}/manifest"
        if version:
            path += f"?version={version}"
        return self._request("GET", path)

    def check_slug(self, slug: str, token: str) -> dict[str, Any]:
        """GET /v1/skills/check?slug=<slug> (authenticated)."""
        return self._request("GET", f"/v1/skills/check?slug={slug}", token=token)

    # ── Publish endpoint ─────────────────────────────────────────

    def publish(
        self,
        skill_id: str,
        title: str,
        version: str,
        artifact_b64: str,
        manifest: dict[str, Any],
        token: str,
        skill_type: str,
        source_language: str,
    ) -> tuple[int, dict[str, Any]]:
        """POST /v1/publish — one code path for WASM and AWA skills.

        Returns ``(status_code, response_body)``; the caller handles
        HTTP 409 (version conflict) and other statuses.
        """
        body: dict[str, Any] = {
            "skill_id": skill_id,
            "title": title,
            "skill_type": skill_type,
            "source_language": source_language,
            "version": version,
            "artifact": artifact_b64,
            "manifest": manifest,
        }
        return self._request_with_status("POST", "/v1/publish", data=body, token=token)

    # ── Robot endpoints ──────────────────────────────────────────

    def get_robot(self, uuid: str) -> dict[str, Any]:
        """GET /v1/robots/:uuid"""
        return self._request("GET", f"/v1/robots/{uuid}")

    def get_robot_skills(self, uuid: str) -> list[dict[str, Any]]:
        """GET /v1/robots/:uuid/skills"""
        result = self._request("GET", f"/v1/robots/{uuid}/skills")
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "skills" in result:
            return list(result["skills"])
        return []
