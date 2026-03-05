"""Authentication handlers for clearinghouse providers."""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import time
from collections.abc import Generator

import httpx


class HMACAuth(httpx.Auth):
    """HMAC-SHA256 request signing for Waystar API.

    Signs each request by computing an HMAC-SHA256 digest over a
    canonical string of ``method\\npath\\ntimestamp\\nbody_hash`` and
    attaching it in the ``Authorization`` and ``X-Timestamp`` headers.

    Note:
        The canonical string uses the URL path only (no query parameters).
        If query parameters need to be covered by the signature, update
        ``request.url.path`` to ``request.url.raw_path`` in ``auth_flow``.
    """

    requires_request_body = True

    def __init__(self, api_key: str, secret: str) -> None:
        self._api_key = api_key
        self._secret = secret

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        """Sign the request with HMAC-SHA256."""
        timestamp = str(int(time.time()))
        body_hash = hashlib.sha256(request.content).hexdigest()
        canonical = (
            f"{request.method}\n{request.url.path}\n{timestamp}\n{body_hash}"
        )
        signature = hmac_mod.new(
            self._secret.encode(),
            canonical.encode(),
            hashlib.sha256,
        ).hexdigest()
        request.headers["Authorization"] = (
            f"HMAC {self._api_key}:{signature}"
        )
        request.headers["X-Timestamp"] = timestamp
        yield request
