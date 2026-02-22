"""Shared test fixtures for claim-validator."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def valid_claim_dict() -> dict[str, Any]:
    """Minimal valid claim dictionary for testing."""
    return {
        "billing_provider_npi": "1234567893",
        "subscriber_id": "XYZ123456",
        "diagnosis_codes": [
            {"code": "J06.9", "pointer": 1},
        ],
        "lines": [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
            },
        ],
    }
