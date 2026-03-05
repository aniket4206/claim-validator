"""Timely filing deadline table — shared accessor and lookup."""

from __future__ import annotations

from typing import cast

from claim_validator.shared.code_tables.loader import load_json


def get_timely_filing_table() -> dict[str, int]:
    """Return the full timely filing table (cached after first load)."""
    return cast(dict[str, int], load_json("timely_filing.json"))


def get_filing_deadline(payer_id: str) -> int | None:
    """Get timely filing deadline in days for a payer.

    Returns the deadline in days, or the ``_default`` value if the payer
    is unknown. Returns None only if no default exists.
    """
    table = get_timely_filing_table()
    normalized = payer_id.upper().strip()
    deadline = table.get(normalized)
    if deadline is None:
        deadline = table.get("_default")
    return deadline
