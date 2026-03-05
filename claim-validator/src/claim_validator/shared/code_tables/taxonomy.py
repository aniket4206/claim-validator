"""Provider taxonomy code table — shared accessor and lookup."""

from __future__ import annotations

from claim_validator.shared.code_tables.loader import load_compressed_json


def get_taxonomy_table() -> dict[str, str]:
    """Return the full provider taxonomy code table (cached after first load)."""
    return load_compressed_json("taxonomy.json.gz")


def lookup_taxonomy(code: str) -> str | None:
    """Look up a provider taxonomy code. Returns description or None if not found."""
    return get_taxonomy_table().get(code.upper().strip())
