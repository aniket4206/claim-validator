"""Factory for creating clearinghouse client instances."""

from __future__ import annotations

from typing import Any

from claim_validator.clearinghouse.base import BaseClearinghouseClient
from claim_validator.exceptions import ConfigurationError


def get_clearinghouse_client(
    provider: str,
    **config: Any,
) -> BaseClearinghouseClient:
    """Create a clearinghouse client for the given provider.

    Uses lazy imports to avoid loading provider modules until needed.

    Args:
        provider: Provider identifier (``"stedi"``, ``"claimmd"``, or
            ``"waystar"``).
        **config: Provider-specific configuration (api_key, secret, etc.).

    Returns:
        A configured clearinghouse client instance.

    Raises:
        ConfigurationError: If the provider is not recognized.
    """
    provider_lower = provider.lower()

    if provider_lower == "stedi":
        from claim_validator.clearinghouse.providers.stedi import StediClient

        return StediClient(**config)

    if provider_lower == "claimmd":
        from claim_validator.clearinghouse.providers.claimmd import (
            ClaimMDClient,
        )

        return ClaimMDClient(**config)

    if provider_lower == "waystar":
        from claim_validator.clearinghouse.providers.waystar import (
            WaystarClient,
        )

        return WaystarClient(**config)

    if provider_lower == "availity":
        from claim_validator.clearinghouse.providers.availity import (
            AvailityClient,
        )

        return AvailityClient(**config)

    if provider_lower == "change":
        from claim_validator.clearinghouse.providers.change_healthcare import (
            ChangeHealthcareClient,
        )

        return ChangeHealthcareClient(**config)

    msg = (
        f"Unknown clearinghouse provider: {provider!r}. "
        f"Supported providers: stedi, claimmd, waystar, change, availity"
    )
    raise ConfigurationError(msg)
