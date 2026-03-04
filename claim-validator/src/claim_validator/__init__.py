"""claim-validator: Healthcare claim validation library."""

from __future__ import annotations

try:
    from claim_validator._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0"

from claim_validator._api import validate
from claim_validator.clearinghouse import (
    BaseClearinghouseClient,
    ClearinghouseError,
    get_clearinghouse_client,
)
from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import ClaimType, Severity
from claim_validator.deidentifier import ClaimDeidentifier
from claim_validator.eligibility import (
    AAAError,
    BenefitInfo,
    CoverageInfo,
    CoverageStatus,
    DeidentifiedAAAError,
    DeidentifiedCoverageInfo,
    DeidentifiedEligibilityResponse,
    EligibilityDeidentifier,
    EligibilityPipeline,
    EligibilityRequest,
    EligibilityResponse,
    EligibilityResult,
    check_eligibility,
)
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
from claim_validator.models.workflow import PreClaimResult
from claim_validator.orchestrator import pre_claim_check
from claim_validator.prior_auth import (
    CertificationActionCode,
    CertificationTypeCode,
    DeidentifiedPriorAuthError,
    DeidentifiedPriorAuthResponse,
    DeidentifiedServiceLineDecision,
    PADeterminationResult,
    PatientInfo,
    PriorAuthDeidentifier,
    PriorAuthError,
    PriorAuthInterpreterAI,
    PriorAuthPipeline,
    PriorAuthRequest,
    PriorAuthResponse,
    PriorAuthResult,
    RequestCategoryCode,
    ServiceLine,
    ServiceLineDecision,
    SubscriberInfo,
    determine_pa_required,
    parse_278_response,
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
    "AAAError",
    "BaseAIValidator",
    "BaseClearinghouseClient",
    "BaseLLMClient",
    "BaseValidator",
    "BenefitInfo",
    "CertificationActionCode",
    "CertificationTypeCode",
    "ClaimData",
    "ClaimDeidentifier",
    "ClaimLineData",
    "ClaimType",
    "ClaimValidatorError",
    "ClaimValidatorSettings",
    "ClearinghouseError",
    "check_eligibility",
    "CodeTableError",
    "ConfigurationError",
    "CoverageInfo",
    "CoverageStatus",
    "DeidentifiedAAAError",
    "DeidentifiedClaim",
    "DeidentifiedCoverageInfo",
    "DeidentifiedEligibilityResponse",
    "DeidentifiedLineData",
    "DeidentifiedPriorAuthError",
    "DeidentifiedPriorAuthResponse",
    "DeidentifiedServiceLineDecision",
    "EligibilityDeidentifier",
    "determine_pa_required",
    "DiagnosisCode",
    "EligibilityPipeline",
    "EligibilityRequest",
    "EligibilityResponse",
    "EligibilityResult",
    "Finding",
    "get_clearinghouse_client",
    "get_llm_client",
    "LLMError",
    "Message",
    "PADeterminationResult",
    "parse_278_response",
    "PatientInfo",
    "PipelineResult",
    "pre_claim_check",
    "PreClaimResult",
    "PriorAuthDeidentifier",
    "PriorAuthInterpreterAI",
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
