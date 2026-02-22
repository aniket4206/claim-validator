"""Place of Service code lookup against bundled CMS table."""

from __future__ import annotations

from claim_validator.code_tables.loader import load_compressed_json


def lookup_pos(code: str) -> str | None:
    """Look up a Place of Service code. Returns description or None if not found."""
    table = load_compressed_json("pos_codes.json.gz")
    normalized = code.strip()
    return table.get(normalized)
