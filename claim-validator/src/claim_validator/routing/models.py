"""Payer routing data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PayerRoute:
    """A single payer-to-clearinghouse route entry.

    Attributes:
        clearinghouse: Provider identifier (e.g. ``"stedi"``, ``"claimmd"``).
        payer_id_at_clearinghouse: The payer ID used with that clearinghouse.
        priority: Route priority (1 = primary, 2 = first fallback, etc.).
        supports: Transaction types this route handles
            (e.g. ``frozenset({"837P", "270/271"})``).
    """

    clearinghouse: str
    payer_id_at_clearinghouse: str
    priority: int
    supports: frozenset[str]
