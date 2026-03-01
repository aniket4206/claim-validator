"""Shared fixtures for eligibility validator tests."""

from __future__ import annotations

from typing import Any

import pytest

from claim_validator.eligibility.models.request import EligibilityRequest


@pytest.fixture
def valid_request() -> EligibilityRequest:
    """Minimal valid eligibility request."""
    return EligibilityRequest(
        provider_npi="1234567893",
        payer_id="60054",
        subscriber_id="XYZ123456",
        subscriber_first_name="Jane",
        subscriber_last_name="Doe",
        subscriber_dob="1985-03-15",
    )


@pytest.fixture
def valid_request_dict() -> dict[str, Any]:
    """Minimal valid eligibility request as a plain dict."""
    return {
        "provider_npi": "1234567893",
        "payer_id": "60054",
        "subscriber_id": "XYZ123456",
        "subscriber_first_name": "Jane",
        "subscriber_last_name": "Doe",
        "subscriber_dob": "1985-03-15",
    }
