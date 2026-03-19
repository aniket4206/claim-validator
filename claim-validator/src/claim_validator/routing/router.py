"""Payer router — resolves payer IDs to clearinghouse routes."""

from __future__ import annotations

from claim_validator.exceptions import PayerRoutingError
from claim_validator.routing.models import PayerRoute
from claim_validator.shared.code_tables.payer_routing import load_default_mapping


class PayerRouter:
    """Resolves payer IDs to clearinghouse routes.

    Stateless after construction.  The internal mapping dict is built once
    during ``__init__`` and never mutated, making the router thread-safe
    for concurrent ``route()`` / ``route_with_fallback()`` calls.

    Args:
        custom_mappings: Optional overrides that take precedence over the
            bundled default mapping.  Keys are payer IDs, values are lists
            of :class:`PayerRoute` sorted by priority.
    """

    def __init__(
        self,
        custom_mappings: dict[str, list[PayerRoute]] | None = None,
    ) -> None:
        defaults = load_default_mapping()
        if custom_mappings:
            # Normalize custom keys to uppercase and sort only overridden entries
            normalized: dict[str, list[PayerRoute]] = {
                k.upper().strip(): sorted(v, key=lambda r: r.priority)
                for k, v in custom_mappings.items()
            }
            self._mappings: dict[str, list[PayerRoute]] = {**defaults, **normalized}
        else:
            self._mappings = defaults

    def route(self, payer_id: str) -> PayerRoute:
        """Return the highest-priority route for *payer_id*.

        Raises:
            PayerRoutingError: If *payer_id* has no known routes.
        """
        routes = self._mappings.get(payer_id.upper().strip())
        if not routes:
            raise PayerRoutingError(
                f"No routes found for payer ID '{payer_id.strip()}'"
            )
        return routes[0]

    def route_with_fallback(self, payer_id: str) -> list[PayerRoute]:
        """Return all routes for *payer_id*, ordered by priority.

        Returns a defensive copy so callers cannot mutate internal state.

        Raises:
            PayerRoutingError: If *payer_id* has no known routes.
        """
        routes = self._mappings.get(payer_id.upper().strip())
        if not routes:
            raise PayerRoutingError(
                f"No routes found for payer ID '{payer_id.strip()}'"
            )
        return list(routes)
