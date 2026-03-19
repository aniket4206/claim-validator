"""Clearinghouse client pool — manages multiple provider clients with fallback routing."""

from __future__ import annotations

import logging
import threading
from typing import Any

from claim_validator.clearinghouse.base import BaseClearinghouseClient
from claim_validator.clearinghouse.factory import get_clearinghouse_client
from claim_validator.clearinghouse.models import (
    ClearinghouseEligibilityResponse,
    SubmissionResult,
)
from claim_validator.exceptions import ConfigurationError
from claim_validator.routing.router import PayerRouter

logger = logging.getLogger(__name__)


def _is_circuit_open_error(exc: BaseException) -> bool:
    """Check if an exception is a CircuitOpenError (without importing resilience)."""
    return type(exc).__name__ == "CircuitOpenError"


class ClearinghouseClientPool:
    """Manages multiple clearinghouse clients with lazy instantiation.

    Clients are created on first ``get_client()`` call and cached for reuse.
    The pool routes claims and eligibility requests to the correct
    clearinghouse using a :class:`PayerRouter`.  When the primary clearinghouse
    has an open circuit breaker, falls back to alternate providers.

    Args:
        configs: Provider name -> config kwargs dict.
        router: Optional pre-configured router.
    """

    def __init__(
        self,
        configs: dict[str, dict[str, Any]],
        router: PayerRouter | None = None,
    ) -> None:
        self._configs: dict[str, dict[str, Any]] = {
            k.lower(): v for k, v in configs.items()
        }
        self._router = router or PayerRouter()
        self._clients: dict[str, BaseClearinghouseClient] = {}
        self._lock = threading.Lock()

    def get_client(self, provider_name: str) -> BaseClearinghouseClient:
        """Return the client for *provider_name*, creating it on first access.

        Raises:
            ConfigurationError: If *provider_name* is not in the pool's configs.
        """
        key = provider_name.lower()

        if key in self._clients:
            return self._clients[key]

        if key not in self._configs:
            raise ConfigurationError(
                f"Clearinghouse provider '{provider_name}' is not configured in the pool"
            )

        with self._lock:
            if key in self._clients:
                return self._clients[key]

            client = get_clearinghouse_client(key, **self._configs[key])
            self._clients[key] = client
            return client

    def submit_claim(
        self,
        claim_data: dict[str, Any],
        payer_id: str,
    ) -> SubmissionResult:
        """Route *claim_data* to the correct clearinghouse and submit.

        Falls back to alternate clearinghouses if the primary has an open
        circuit breaker.
        """
        return self._with_fallback(
            payer_id,
            lambda client: client.submit_claim(claim_data),
        )

    def check_eligibility(
        self,
        request: dict[str, Any],
        payer_id: str,
    ) -> ClearinghouseEligibilityResponse:
        """Route *request* to the correct clearinghouse for eligibility.

        Falls back to alternate clearinghouses if the primary has an open
        circuit breaker.
        """
        return self._with_fallback(
            payer_id,
            lambda client: client.check_eligibility(request),
        )

    def check_claim_status(
        self,
        claim_ref: str,
        payer_id: str,
    ) -> Any:
        """Check claim status — always uses primary route (no fallback).

        Status queries must go to the original clearinghouse where the
        claim was submitted.
        """
        route = self._router.route(payer_id)
        client = self.get_client(route.clearinghouse)
        return client.check_claim_status(claim_ref)

    def _with_fallback(
        self,
        payer_id: str,
        action: Any,
    ) -> Any:
        """Try the primary route, then fallbacks on CircuitOpenError."""
        routes = self._router.route_with_fallback(payer_id)
        attempted: list[str] = []

        for route in routes:
            if route.clearinghouse.lower() not in self._configs:
                continue  # Skip unconfigured providers
            try:
                client = self.get_client(route.clearinghouse)
                return action(client)
            except Exception as exc:
                if _is_circuit_open_error(exc):
                    attempted.append(route.clearinghouse)
                    logger.warning(
                        "Circuit open for %s, trying fallback", route.clearinghouse
                    )
                    continue
                raise  # Non-circuit errors propagate immediately

        # All configured routes had open circuits
        if attempted:
            raise ConfigurationError(
                f"All clearinghouses unavailable for payer '{payer_id}': "
                f"circuit open on {attempted}"
            )

        # No configured routes at all — use primary route for error
        route = routes[0]
        client = self.get_client(route.clearinghouse)
        return action(client)

    def close(self) -> None:
        """Close all instantiated clients."""
        with self._lock:
            for client in self._clients.values():
                client.close()
            self._clients.clear()

    def __enter__(self) -> ClearinghouseClientPool:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
