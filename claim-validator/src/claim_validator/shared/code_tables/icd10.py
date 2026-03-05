"""ICD-10-CM code table — shared accessor and lookup."""

from __future__ import annotations

from claim_validator.shared.code_tables.loader import load_compressed_json


def get_icd10_table() -> dict[str, str]:
    """Return the full ICD-10-CM code table (cached after first load)."""
    return load_compressed_json("icd10_cm.json.gz")


def lookup_icd10(code: str) -> str | None:
    """Look up an ICD-10-CM code. Returns description or None if not found.

    Handles codes with or without the dot separator (e.g. ``"J06.9"`` or ``"J069"``).
    """
    table = get_icd10_table()
    normalized = code.upper().strip()
    result = table.get(normalized)
    if result is not None:
        return result
    # Try without dot (input has dot, table might not)
    dotless = normalized.replace(".", "")
    result = table.get(dotless)
    if result is not None:
        return result
    # Try with dot inserted at position 3 (input has no dot, table uses dots)
    if "." not in normalized and len(normalized) > 3:
        dotted = normalized[:3] + "." + normalized[3:]
        result = table.get(dotted)
    return result
