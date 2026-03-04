"""Tests for HMACAuth clearinghouse authentication."""

from __future__ import annotations

from unittest.mock import patch

import httpx

from claim_validator.clearinghouse.auth import HMACAuth


class TestHMACAuth:
    """Verify HMAC-SHA256 signing behaviour."""

    def test_sets_authorization_header(self) -> None:
        auth = HMACAuth(api_key="my-key", secret="my-secret")
        request = httpx.Request("POST", "https://api.example.com/test", content=b'{}')
        flow = auth.auth_flow(request)
        signed = next(flow)
        assert signed.headers["Authorization"].startswith("HMAC my-key:")

    def test_sets_timestamp_header(self) -> None:
        auth = HMACAuth(api_key="my-key", secret="my-secret")
        request = httpx.Request("POST", "https://api.example.com/test", content=b'{}')
        with patch("claim_validator.clearinghouse.auth.time") as mock_time:
            mock_time.time.return_value = 1709500000
            flow = auth.auth_flow(request)
            signed = next(flow)
            assert signed.headers["X-Timestamp"] == "1709500000"

    def test_deterministic_signature(self) -> None:
        """Same inputs produce same signature."""
        auth = HMACAuth(api_key="test-key", secret="test-secret")
        body = b'{"test": true}'

        signatures = []
        for _ in range(2):
            request = httpx.Request(
                "POST", "https://api.example.com/v1/claims", content=body
            )
            with patch("claim_validator.clearinghouse.auth.time") as mock_time:
                mock_time.time.return_value = 1709500000
                flow = auth.auth_flow(request)
                signed = next(flow)
                signatures.append(signed.headers["Authorization"])

        assert signatures[0] == signatures[1]

    def test_different_body_different_signature(self) -> None:
        auth = HMACAuth(api_key="key", secret="secret")

        with patch("claim_validator.clearinghouse.auth.time") as mock_time:
            mock_time.time.return_value = 1709500000

            req1 = httpx.Request("POST", "https://api.example.com/test", content=b'{"a":1}')
            signed1 = next(auth.auth_flow(req1))
            sig1 = signed1.headers["Authorization"]

            req2 = httpx.Request("POST", "https://api.example.com/test", content=b'{"b":2}')
            signed2 = next(auth.auth_flow(req2))
            sig2 = signed2.headers["Authorization"]

        assert sig1 != sig2

    def test_different_secret_different_signature(self) -> None:
        body = b'{"test": true}'

        with patch("claim_validator.clearinghouse.auth.time") as mock_time:
            mock_time.time.return_value = 1709500000

            auth1 = HMACAuth(api_key="key", secret="secret-a")
            req1 = httpx.Request("POST", "https://api.example.com/test", content=body)
            signed1 = next(auth1.auth_flow(req1))
            sig1 = signed1.headers["Authorization"]

            auth2 = HMACAuth(api_key="key", secret="secret-b")
            req2 = httpx.Request("POST", "https://api.example.com/test", content=body)
            signed2 = next(auth2.auth_flow(req2))
            sig2 = signed2.headers["Authorization"]

        assert sig1 != sig2

    def test_authorization_format(self) -> None:
        auth = HMACAuth(api_key="my-key", secret="my-secret")
        request = httpx.Request("POST", "https://api.example.com/test", content=b'{}')
        flow = auth.auth_flow(request)
        signed = next(flow)
        auth_header = signed.headers["Authorization"]
        assert auth_header.startswith("HMAC my-key:")
        # Extract signature part
        sig = auth_header.split(":")[1]
        # SHA-256 hex digest is 64 characters
        assert len(sig) == 64

    def test_empty_body_request(self) -> None:
        """GET requests with no body should still produce a valid signature."""
        auth = HMACAuth(api_key="key", secret="secret")
        request = httpx.Request("GET", "https://api.example.com/status")
        flow = auth.auth_flow(request)
        signed = next(flow)
        assert signed.headers["Authorization"].startswith("HMAC key:")
        sig = signed.headers["Authorization"].split(":")[1]
        assert len(sig) == 64

    def test_requires_request_body(self) -> None:
        assert HMACAuth.requires_request_body is True


class TestHMACAuthImport:
    """Verify HMACAuth importable from clearinghouse package."""

    def test_import_from_clearinghouse(self) -> None:
        from claim_validator.clearinghouse import HMACAuth

        assert HMACAuth is not None
