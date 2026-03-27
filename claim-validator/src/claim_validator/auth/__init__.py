"""Authentication module — routes, schemas, and utilities."""

from claim_validator.auth.routes import router as auth_router
from claim_validator.auth.utils import get_token_from_request, verify_token

__all__ = ["auth_router", "get_token_from_request", "verify_token"]
