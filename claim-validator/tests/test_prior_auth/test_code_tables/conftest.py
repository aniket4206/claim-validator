"""Shared fixtures for PA code table tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _reset_pa_table_caches() -> Iterator[None]:
    """Reset PA lazy-loaded table caches between tests."""
    from claim_validator.prior_auth.code_tables import loader

    loader._tables.clear()
    loader._locks.clear()
    yield
