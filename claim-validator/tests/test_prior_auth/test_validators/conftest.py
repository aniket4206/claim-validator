"""Shared fixtures for PA validator tests."""

from __future__ import annotations

from datetime import date

import pytest

from claim_validator.prior_auth.models.request import (
    PriorAuthRequest,
    ServiceLine,
    SubscriberInfo,
)


@pytest.fixture
def valid_request() -> PriorAuthRequest:
    """Minimal valid PriorAuthRequest for validator tests."""
    return PriorAuthRequest(
        requester_npi="1234567893",
        subscriber=SubscriberInfo(
            member_id="MEM001",
            first_name="Jane",
            last_name="Doe",
            dob=date(1985, 3, 15),
        ),
        diagnosis_codes=["J06.9"],
        service_lines=[
            ServiceLine(cpt_code="99213"),
        ],
    )
