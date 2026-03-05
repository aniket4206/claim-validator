"""Payer directory code table — shared accessor and lookup."""

from __future__ import annotations

from typing import Any, cast

from claim_validator.shared.code_tables.loader import load_json


def get_payer_directory_table() -> dict[str, Any]:
    """Return the full payer directory table (cached after first load)."""
    return cast(dict[str, Any], load_json("payer_directory.json"))


def lookup_payer(payer_id: str) -> dict[str, str] | None:
    """Look up a payer by ID. Returns payer info dict or None if not found.

    The returned dict contains: ``name``, ``type``.
    """
    return get_payer_directory_table().get(payer_id.upper().strip())
