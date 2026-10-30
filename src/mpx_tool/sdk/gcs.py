"""HTTP client for GCS (emulator or real GCS) — web family storage."""

from __future__ import annotations

from typing import Any
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from mpx_tool.config import DEFAULT_GCS_BUCKET, DEFAULT_GCS_EMULATOR_URL


class GcsError(Exception):
    """Raised when a GCS operation fails."""


class GcsClient:
    """Minimal GCS JSON/upload API client for seeding and listing skills."""

    def __init__(
        self,
        base_url: str | None = None,
        bucket: str | None = None,
    ) -> None:
        self._base = (base_url or DEFAULT_GCS_EMULATOR_URL).rstrip("/")
        self.bucket = bucket or DEFAULT_GCS_BUCKET

    def _url(self, path: str) -> str:
        return f"{self._base}{path}"

    def _send(
        self,
        method: str,
        url: str,
        data: bytes | None = None,
        content_type: str | None = None,
        timeout: int = 30,
    ) -> tuple[int, Any]:
        req = Request(url, data=data, method=method)
        if content_type and data is not None:
            req.add_header("Content-Type", content_type)
        if data is not None:
            req.add_header("Content-Length", str(len(data)))
        try:
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                try:
                    return resp.status, (__import__("json").loads(raw) if raw else {})
                except Exception:
                    return resp.status, {"raw": raw}
        except URLError as e:
            raise GcsError(f"GCS request failed ({method} {url}): {e}") from e

    # ── Buckets ─────────────────────────────────────────────────

    def bucket_exists(self) -> bool:
        """Return True if the target bucket exists in the (emulator) store."""
        url = f"{self._base}/storage/v1/b/{self.bucket}"
        try:
            status, _ = self._send("GET", url)
        except GcsError:
            return False
        return status == 200

    def create_bucket(self) -> None:
        """Create the target bucket (fake-gcs-server JSON API)."""
        url = f"{self._base}/storage/v1/b"
        payload = __import__("json").dumps({"name": self.bucket}).encode("utf-8")
        status, _ = self._send("POST", url, data=payload, content_type="application/json")
        # fake-gcs-server returns 200 on create; 409 if it already exists.
        if status not in (200, 409):
            raise GcsError(f"Bucket {self.bucket!r} creation failed (HTTP {status})")

    def ensure_bucket(self) -> None:
        """Create the bucket if it does not yet exist (idempotent).

        fake-gcs-server starts with an empty data volume, so the skills
        bucket must be created on first use. Real GCS buckets already
        exist by the time this code would be pointed at them, so this is
        a no-op there.
        """
        if not self.bucket_exists():
            self.create_bucket()

    # ── Objects ──────────────────────────────────────────────────

    def upload(self, object_name: str, content: bytes, content_type: str) -> None:
        """Upload an object via the media-upload endpoint."""
        url = (
            f"{self._base}/upload/storage/v1/b/{self.bucket}/o"
            f"?uploadType=media&name={quote(object_name, safe='')}"
        )
        status, _ = self._send("POST", url, data=content, content_type=content_type)
        if not (200 <= status < 300):
            raise GcsError(f"Upload of {object_name!r} failed (HTTP {status})")

    def list_objects(self, prefix: str = "") -> list[dict[str, Any]]:
        """List objects under a prefix."""
        url = f"{self._base}/storage/v1/b/{self.bucket}/o?prefix={quote(prefix, safe='')}"
        status, body = self._send("GET", url)
        if status != 200:
            raise GcsError(f"List failed (HTTP {status})")
        items = body.get("items", []) if isinstance(body, dict) else []
        return [i for i in items if isinstance(i, dict)]

    def get_object(self, object_name: str) -> bytes:
        """Fetch an object's raw content via ?alt=media."""
        url = (
            f"{self._base}/storage/v1/b/{self.bucket}/o"
            f"/{quote(object_name, safe='')}?alt=media"
        )
        req = Request(url, method="GET")
        try:
            with urlopen(req, timeout=30) as resp:
                return resp.read()
        except URLError as e:
            raise GcsError(f"GET {object_name!r} failed: {e}") from e

    def delete_object(self, object_name: str) -> None:
        """Delete one object (component-wise URL encoding)."""
        encoded = "/".join(quote(part, safe="") for part in object_name.split("/"))
        url = f"{self._base}/storage/v1/b/{self.bucket}/o/{encoded}"
        status, _ = self._send("DELETE", url)
        if not (200 <= status < 300):
            raise GcsError(f"Delete of {object_name!r} failed (HTTP {status})")
