"""Pipeline configuration — specifies phases, validators, and gating rules per domain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from claim_validator.shared.deidentifier.base import BaseDeidentifier
from claim_validator.validators.base import BaseValidator


@dataclass(frozen=True)
class PipelineConfig:
    """Immutable configuration for a multi-phase pipeline.

    Each domain creates one PipelineConfig with its specific validators,
    clearinghouse client, AI interpreter, and gating rules. The BasePipeline
    executes phases in order using this config.

    Attributes:
        domain: Domain identifier ("claim", "eligibility", "prior_auth").
        validators: Pre-constructed rule-based validators for phase 1.
        clearinghouse_client: Optional clearinghouse client for phase 2.
            Must have a ``submit(data)`` method (duck-typed).
        ai_interpreter: Optional AI interpreter/validator for phase 3.
            Must have a ``validate_deidentified(data)`` method (duck-typed).
        deidentifier: De-identifier for stripping PHI before AI phase.
            Required if ai_interpreter is configured.
        skip_ai_on_rule_failure: If True, skip AI when rule phase has ERRORs.
        skip_clearinghouse_on_rule_failure: If True, skip clearinghouse
            (and AI via cascade) when rule phase has ERRORs.
        code_prefix: Finding code prefix for this domain (e.g., "ELIG_", "PA_").
    """

    domain: str
    validators: tuple[BaseValidator, ...] = ()
    clearinghouse_client: Any | None = None
    ai_interpreter: Any | None = None
    deidentifier: BaseDeidentifier | None = None
    skip_ai_on_rule_failure: bool = True
    skip_clearinghouse_on_rule_failure: bool = True
    code_prefix: str = ""

    def __post_init__(self) -> None:
        """Validate config constraints."""
        if self.ai_interpreter is not None and self.deidentifier is None:
            msg = (
                "deidentifier is required when ai_interpreter is configured "
                "(PHI must be stripped before AI consumption per FR40)"
            )
            raise ValueError(msg)
