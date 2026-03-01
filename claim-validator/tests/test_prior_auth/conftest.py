"""Shared test fixtures for prior authorization module."""

from __future__ import annotations

from datetime import date

import pytest

from claim_validator.prior_auth.models.request import SubscriberInfo


@pytest.fixture
def subscriber() -> SubscriberInfo:
    """Minimal valid subscriber for PA request tests."""
    return SubscriberInfo(
        member_id="MEM001",
        first_name="Jane",
        last_name="Doe",
        dob=date(1985, 3, 15),
    )
