"""Abstract base class for clearinghouse clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from claim_validator.clearinghouse.models import (
    ClaimStatusResponse,
    ClearinghouseEligibilityResponse,
    SubmissionResult,
)


class BaseClearinghouseClient(ABC):
    """Abstract clearinghouse client — all providers implement this.

    Provides the contract for submitting claims, verifying eligibility,
    and checking claim status through healthcare clearinghouses.

    Subclasses must implement ``submit_claim``, ``check_eligibility``,
    ``check_claim_status``, and the ``provider_name`` property.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "",
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout
        self._client = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(timeout, connect=10.0),
        )

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the clearinghouse provider identifier."""
        ...

    @abstractmethod
    def submit_claim(self, claim_data: dict[str, Any]) -> SubmissionResult:
        """Submit a claim to the clearinghouse.

        Args:
            claim_data: Claim fields as a dictionary.

        Returns:
            Submission acknowledgment result.
        """
        ...

    @abstractmethod
    def check_eligibility(
        self, request: dict[str, Any]
    ) -> ClearinghouseEligibilityResponse:
        """Verify patient eligibility (270/271 transaction).

        Args:
            request: Eligibility request fields as a dictionary.

        Returns:
            Eligibility verification response.
        """
        ...

    @abstractmethod
    def check_claim_status(self, claim_ref: str) -> ClaimStatusResponse:
        """Check claim adjudication status (276/277 transaction).

        Args:
            claim_ref: Clearinghouse claim reference identifier.

        Returns:
            Claim status response.
        """
        ...

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> BaseClearinghouseClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
