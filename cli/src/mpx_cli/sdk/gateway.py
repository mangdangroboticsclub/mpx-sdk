"""HTTP client for communicating with the MPX marketplace gateway.

Portable — uses only the Python standard library (urllib).
Works on any platform with Python 3.10+.

Mirrors the ``RobotClient`` pattern from ``connection.py`` but targets
the REST API of the gateway/marketplace server.
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

from mpx_cli.sdk.auth import read_token

# ── Defaults (overridable via environment variables) ───────────────
#
# THE FALLBACK IS THE REAL GATEWAY, NOT LOCALHOST, AND THAT WAY ROUND MATTERS.
#
# It used to fall back to http://localhost:8080. On the machine where this was
# written that was invisible: a .env in the package directory sets
# MPX_GATEWAY_URL to the real host, __init__.py loads it, and even `--help`
# printed the real address as "the default". But .env is not committed — that
# is the entire reason .env.sample exists — so on a fresh clone the variable
# is unset, the fallback applies, and `mpx-cli signup` dials a port on the
# user's own machine with nothing behind it. The error is
# [Errno 111] Connection refused, which reads like the marketplace is down
# rather than like a default nobody chose.
#
# A default should be what works for someone who has configured nothing.
# Running a gateway on localhost is the special case, so the special case is
# what sets the variable.
PRODUCTION_GATEWAY_URL = "http://35.220.215.160:8080"
DEFAULT_GATEWAY_URL = os.environ.get("MPX_GATEWAY_URL", PRODUCTION_GATEWAY_URL)


class GatewayError(Exception):
    """Raised when the gateway returns a non-OK response or is unreachable."""


class GatewayClient:
    """HTTP client for the MPX marketplace gateway REST API.

    All methods raise ``GatewayError`` on failure.
    """

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
        """Send an HTTP request and return the parsed JSON response."""
        url = self._url(path)
        body = json.dumps(data, separators=(",", ":")).encode("utf-8") if data else None
        req = Request(url, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", f"Bearer {token}")

        try:
            with urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                if raw:
                    return json.loads(raw)
                return {}
        except HTTPError as e:
            # MUST come before URLError: HTTPError subclasses it. Without this
            # branch an HTTP 422 — the gateway answering, in detail, that it
            # did not like the request — was caught as "connection failed" and
            # printed under "check your internet connection". The one thing it
            # definitely was not is a network problem: the server replied.
            raise GatewayError(self._http_error(e)) from e
        except URLError as e:
            raise GatewayError(self._unreachable(e)) from e
        except json.JSONDecodeError as e:
            raise GatewayError(f"Invalid JSON from gateway: {e}") from e

    def _http_error(self, e: HTTPError) -> str:
        """Turn a rejection into the reason for it.

        The gateway sends its complaint in the response body — FastAPI-style
        validation errors name the exact field and rule. Reading it costs
        nothing and is the difference between "422 Unprocessable Entity" and
        "password: must be at least 8 characters".
        """
        detail = ""
        try:
            payload = json.loads(e.read().decode("utf-8") or "{}")
        except Exception:
            payload = None

        if isinstance(payload, dict):
            raw = payload.get("detail", payload.get("message", payload.get("error")))
            if isinstance(raw, list):
                # FastAPI: [{"loc": ["body","password"], "msg": "...", ...}]
                parts = []
                for item in raw:
                    if not isinstance(item, dict):
                        parts.append(str(item))
                        continue
                    loc = ".".join(str(x) for x in item.get("loc", [])
                                   if x not in ("body", "query"))
                    msg = item.get("msg", "invalid")
                    parts.append(f"{loc}: {msg}" if loc else msg)
                detail = "; ".join(parts)
            elif raw:
                detail = str(raw)

        lines = [f"Gateway rejected the request: HTTP {e.code}"
                 + (f" — {detail}" if detail else "")]

        if e.code == 422 and not detail:
            lines += [
                "",
                "   422 means the gateway understood the request and refused "
                "the CONTENTS of it,",
                "   so this is not a network or address problem. Usually the "
                "username or password",
                "   does not meet its rules — try a longer password and a "
                "username with no spaces.",
            ]
        elif e.code == 409:
            lines += ["", "   That username is already taken."]
        elif e.code in (401, 403):
            lines += ["", "   Not authorised — `mpx-cli login` first, or your "
                          "session has expired."]
        return "\n".join(lines)

    def _unreachable(self, err: object) -> str:
        """Why the gateway did not answer — naming the address AND its source.

        The address the CLI dialled is worth printing, but on its own it does
        not say where that address came from, and the answer is usually the
        whole bug: MPX_GATEWAY_URL pointing at a local gateway that is not
        running. "Connection refused to localhost" is only confusing until you
        know nobody chose localhost on purpose.
        """
        lines = [f"Connection to gateway at {self._base} failed: {err}"]
        base = self._base
        if "localhost" in base or "127.0.0.1" in base:
            src = ("MPX_GATEWAY_URL" if os.environ.get("MPX_GATEWAY_URL")
                   else "a --gateway argument")
            lines += [
                "",
                f"   {base} is a gateway on YOUR OWN machine, and nothing is "
                "listening on that port.",
                f"   It came from {src}. Unless you are deliberately running "
                "the marketplace locally,",
                "   that is not the address you want — the real one is:",
                "",
                f"     {PRODUCTION_GATEWAY_URL}",
                "",
                "   Clear the override (check ./.env and cli/src/mpx_cli/.env, "
                "and your shell), or",
                f"   pass it explicitly:  mpx-cli --gateway {PRODUCTION_GATEWAY_URL} signup ...",
            ]
        else:
            lines += [
                "",
                "   Check your internet connection. If you are joined to the "
                "robot's own hotspot,",
                "   you are on a network with no route out — join your normal "
                "Wi-Fi for marketplace",
                "   commands, then switch back to deploy.",
            ]
        return "\n".join(lines)

    def _request_with_status(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        token: str | None = None,
    ) -> tuple[int, Any]:
        """Send an HTTP request and return ``(status_code, parsed_body)``."""
        url = self._url(path)
        body = json.dumps(data, separators=(",", ":")).encode("utf-8") if data else None
        req = Request(url, data=body, method=method)
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", f"Bearer {token}")

        try:
            with urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                parsed = json.loads(raw) if raw else {}
                return resp.status, parsed
        except URLError as e:
            # Try to extract HTTP status from the error
            if hasattr(e, "code") and e.code is not None:
                try:
                    raw_body = e.read().decode("utf-8") if hasattr(e, "read") else "{}"
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
        """Register a new developer account.

        POST /v1/auth/signup
        """
        return self._request("POST", "/v1/auth/signup", {
            "username": username,
            "password": password,
        })

    def login(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate and receive a JWT.

        POST /v1/auth/login  →  ``{"token": "..."}``
        """
        return self._request("POST", "/v1/auth/login", {
            "username": username,
            "password": password,
        })

    def refresh_token(self, token: str) -> dict[str, Any]:
        """Refresh an expiring JWT.

        POST /v1/auth/refresh
        """
        return self._request("POST", "/v1/auth/refresh", token=token)

    # ── Skill discovery endpoints ────────────────────────────────

    def list_skills(self) -> list[dict[str, Any]]:
        """List all marketplace skills.

        GET /v1/skills
        """
        result = self._request("GET", "/v1/skills")
        if isinstance(result, list):
            return result
        if "skills" in result:
            return list(result["skills"])
        return []

    def get_skill(self, skill_id: str) -> dict[str, Any]:
        """Get details for a single skill.

        GET /v1/skills/:id
        """
        return self._request("GET", f"/v1/skills/{skill_id}")

    def get_versions(self, skill_id: str) -> list[dict[str, Any]]:
        """List all published versions of a skill.

        GET /v1/skills/:id/versions
        """
        result = self._request("GET", f"/v1/skills/{skill_id}/versions")
        if isinstance(result, list):
            return result
        if "versions" in result:
            return list(result["versions"])
        return []

    def download_artifact(self, skill_id: str, version: str | None = None,
                          url: str | None = None) -> bytes:
        """Fetch a published skill's .wasm bytes.

        THE ENDPOINT IS NOT KNOWN FOR CERTAIN. The gateway is a separate
        service that is not in this repository, and nothing in the CLI ever
        downloaded an artifact before — `publish` uploads base64 and that is
        the only direction that existed. Rather than hardcode a guess and fail
        obscurely, this tries the plausible routes in order and, if they all
        miss, says exactly what it tried so the gateway can grow the right one.

        Order:
          1. an explicit --url, if the caller passed one
          2. an artifact URL carried in the skill's manifest
          3. GET /v1/skills/{id}/artifact  (the conventional shape)
          4. GET /v1/skills/{id}/download
        """
        attempts: list[str] = []

        if url:
            attempts.append(url)
        else:
            # The manifest is the gateway's own description of the skill, so if
            # it names a location that is authoritative and version-correct.
            try:
                manifest = self.get_manifest(skill_id, version)
                for key in ("artifact_url", "download_url", "wasm_url", "url"):
                    value = manifest.get(key)
                    if isinstance(value, str) and value.startswith("http"):
                        attempts.append(value)
                        break
            except GatewayError:
                pass  # no manifest is not fatal; fall through to conventions

            quoted = quote(skill_id, safe="")
            suffix = f"?version={quote(version)}" if version else ""
            attempts.append(f"{self._base}/v1/skills/{quoted}/artifact{suffix}")
            attempts.append(f"{self._base}/v1/skills/{quoted}/download{suffix}")

        errors: list[str] = []
        for candidate in attempts:
            try:
                req = Request(candidate, method="GET")
                token = read_token()
                if token:
                    req.add_header("Authorization", f"Bearer {token}")
                with urlopen(req, timeout=60) as resp:
                    data = resp.read()
                if data:
                    return data
                errors.append(f"{candidate}: empty response")
            except HTTPError as e:
                errors.append(f"{candidate}: HTTP {e.code}")
            except URLError as e:
                errors.append(f"{candidate}: {e.reason}")

        detail = "\n".join(f"     - {e}" for e in errors)
        raise GatewayError(
            "Could not download the skill artifact. Tried:\n"
            f"{detail}\n"
            "   If your gateway serves artifacts from a different path, pass it "
            "with --url, or add /v1/skills/{id}/artifact to the gateway."
        )

    def get_manifest(self, skill_id: str, version: str | None = None) -> dict[str, Any]:
        """Get the manifest/readme for a skill.

        GET /v1/skills/:id/manifest
        Optionally query ``?version=<version>``.
        """
        path = f"/v1/skills/{skill_id}/manifest"
        if version:
            path += f"?version={version}"
        return self._request("GET", path)

    def check_slug(self, slug: str, token: str) -> dict[str, Any]:
        """Check whether a slug is available.

        GET /v1/skills/check?slug=<slug>
        Requires authentication.
        """
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
    ) -> tuple[int, dict[str, Any]]:
        """Publish or update a skill version.

        POST /v1/publish

        Returns ``(status_code, response_body)`` so the caller can handle
        HTTP 409 (version conflict) and other statuses.

        Args:
            skill_id: Fully qualified skill ID (``{username}~{slug}``).
            title: Human-readable title.
            version: Semver string (e.g. ``"1.0.0"``).
            artifact_b64: Base64-encoded WASM binary.
            manifest: Full skill manifest dict.
            token: JWT for authentication.
        """
        body: dict[str, Any] = {
            "skill_id": skill_id,
            "title": title,
            "skill_type": "WASM",
            "source_language": manifest.get("source_language", "c"),
            "version": version,
            "artifact": artifact_b64,
            "manifest": manifest,
        }
        return self._request_with_status("POST", "/v1/publish", data=body, token=token)

    # ── Robot endpoints ──────────────────────────────────────────

    def get_robot(self, uuid: str) -> dict[str, Any]:
        """Get robot info.

        GET /v1/robots/:uuid
        """
        return self._request("GET", f"/v1/robots/{uuid}")

    def get_robot_skills(self, uuid: str) -> list[dict[str, Any]]:
        """List skills assigned to a robot.

        GET /v1/robots/:uuid/skills
        """
        result = self._request("GET", f"/v1/robots/{uuid}/skills")
        if isinstance(result, list):
            return result
        if "skills" in result:
            return list(result["skills"])
        return []
