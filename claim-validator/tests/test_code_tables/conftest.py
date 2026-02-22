"""Shared fixtures for code table tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _reset_table_caches() -> Iterator[None]:
    """Reset lazy-loaded table caches between tests."""
    from claim_validator.code_tables import loader, timely_filing

    loader._tables.clear()
    loader._locks.clear()
    timely_filing._timely_filing = None
    yield
