"""claim-validator: Healthcare claim validation library."""

from __future__ import annotations

try:
    from claim_validator._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0"

from claim_validator._api import validate
from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import ClaimType, Severity
from claim_validator.deidentifier import ClaimDeidentifier
from claim_validator.exceptions import (
    ClaimValidatorError,
    CodeTableError,
    ConfigurationError,
    LLMError,
    ValidationError,
)
from claim_validator.llm import BaseLLMClient, Message, get_llm_client
from claim_validator.models import (
    ClaimData,
    ClaimLineData,
    DeidentifiedClaim,
    DeidentifiedLineData,
    DiagnosisCode,
    Finding,
    PipelineResult,
    ValidatorOutput,
)
from claim_validator.prior_auth import (
    CertificationActionCode,
    CertificationTypeCode,
    DeidentifiedPriorAuthResponse,
    PADeterminationResult,
    PatientInfo,
    PriorAuthError,
    PriorAuthPipeline,
    PriorAuthRequest,
    PriorAuthResponse,
    PriorAuthResult,
    RequestCategoryCode,
    ServiceLine,
    ServiceLineDecision,
    SubscriberInfo,
    determine_pa_required,
    submit_prior_auth,
)
from claim_validator.validators import (
    BaseAIValidator,
    BaseValidator,
    ValidationPipeline,
    ValidatorRegistry,
)

__all__ = [
    "__version__",
    "BaseAIValidator",
    "BaseLLMClient",
    "BaseValidator",
    "CertificationActionCode",
    "CertificationTypeCode",
    "ClaimData",
    "ClaimDeidentifier",
    "ClaimLineData",
    "ClaimType",
    "ClaimValidatorError",
    "ClaimValidatorSettings",
    "CodeTableError",
    "ConfigurationError",
    "DeidentifiedClaim",
    "DeidentifiedLineData",
    "DeidentifiedPriorAuthResponse",
    "determine_pa_required",
    "DiagnosisCode",
    "Finding",
    "get_llm_client",
    "LLMError",
    "Message",
    "PADeterminationResult",
    "PatientInfo",
    "PipelineResult",
    "PriorAuthError",
    "PriorAuthPipeline",
    "PriorAuthRequest",
    "PriorAuthResponse",
    "PriorAuthResult",
    "RequestCategoryCode",
    "ServiceLine",
    "ServiceLineDecision",
    "Severity",
    "submit_prior_auth",
    "SubscriberInfo",
    "validate",
    "ValidationError",
    "ValidationPipeline",
    "ValidatorOutput",
    "ValidatorRegistry",
]
