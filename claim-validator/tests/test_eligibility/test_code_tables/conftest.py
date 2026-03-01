"""Shared fixtures for eligibility code table tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _reset_elig_table_caches() -> Iterator[None]:
    """Reset eligibility lazy-loaded table caches between tests."""
    from claim_validator.eligibility.code_tables import loader

    loader._tables.clear()
    loader._locks.clear()
    yield
