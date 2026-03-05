"""Place of Service code table — shared accessor and lookup."""

from __future__ import annotations

from claim_validator.shared.code_tables.loader import load_compressed_json


def get_pos_table() -> dict[str, str]:
    """Return the full Place of Service code table (cached after first load)."""
    return load_compressed_json("pos_codes.json.gz")


def lookup_pos(code: str) -> str | None:
    """Look up a Place of Service code. Returns description or None if not found."""
    return get_pos_table().get(code.strip())
