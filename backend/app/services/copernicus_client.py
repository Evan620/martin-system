"""R8 Copernicus Data Space (CDSE) client.

Authenticates via OAuth2 client_credentials against the CDSE Keycloak realm
and runs Sentinel-Hub-compatible Process API requests. Tokens are cached
in-memory and refreshed proactively before expiry."""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class CopernicusAuthError(RuntimeError):
    """Raised when Copernicus credentials are rejected or absent."""


class CopernicusClient:
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        auth_url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> None:
        self._client_id = client_id or os.environ.get("COPERNICUS_CLIENT_ID")
        self._client_secret = client_secret or os.environ.get("COPERNICUS_CLIENT_SECRET")
        self._base_url = (base_url or os.environ.get("COPERNICUS_BASE_URL")
                          or "https://sh.dataspace.copernicus.eu").rstrip("/")
        self._auth_url = (auth_url or os.environ.get("COPERNICUS_AUTH_URL")
                          or "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token")
        self._timeout = int(timeout_seconds or os.environ.get("COPERNICUS_TIMEOUT_SECONDS", "60"))

        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0  # epoch seconds

    @classmethod
    def is_configured(cls) -> bool:
        """True iff client_id is set in env. Service uses this to dispatch."""
        return bool(os.environ.get("COPERNICUS_CLIENT_ID"))

    def _get_token(self) -> str:
        """Return a valid access token, refreshing if within 60s of expiry."""
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        if not self._client_id or not self._client_secret:
            raise CopernicusAuthError("COPERNICUS_CLIENT_ID/SECRET not set")

        try:
            resp = httpx.post(
                self._auth_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                timeout=self._timeout,
            )
        except httpx.HTTPError as e:
            raise CopernicusAuthError(f"auth request failed: {e}") from e

        if resp.status_code != 200:
            raise CopernicusAuthError(f"auth returned {resp.status_code}: {resp.text[:200]}")

        body = resp.json()
        self._token = body["access_token"]
        self._token_expires_at = time.time() + int(body.get("expires_in", 600))
        return self._token

    def _process_request(self, payload: Dict[str, Any]) -> bytes:
        """POST to the Process API. Returns raw response bytes."""
        token = self._get_token()
        resp = httpx.post(
            f"{self._base_url}/api/v1/process",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.content

    def compute_signals(self, lat: float, lon: float) -> Dict[str, Any]:
        """Run all four signal queries. Placeholder — implemented in Task 6."""
        raise NotImplementedError("Task 6 fills this in")
