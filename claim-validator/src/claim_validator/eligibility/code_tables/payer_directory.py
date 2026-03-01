"""Payer directory lookup for eligibility verification."""

from __future__ import annotations

from typing import Any

from claim_validator.eligibility.code_tables.loader import load_elig_json


def get_payer_directory(payer_id: str) -> dict[str, str] | None:
    """Look up a payer by ID. Returns payer info dict or None if not found.

    The returned dict contains: name, type.
    """
    table: dict[str, Any] = load_elig_json("payer_directory.json")
    normalized = payer_id.upper().strip()
    return table.get(normalized)
