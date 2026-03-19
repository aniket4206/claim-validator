"""Shared code table accessors and lookup functions — unified access for all domains.

Note: ``shared/data/pa_service_types.json`` (PA-specific service type subset) is
bundled but intentionally has no accessor here.  PA validators that need it can
load it directly via ``loader.load_json("pa_service_types.json")``, or an
accessor will be added when PA module refactoring lands (Epic 3).
"""

from __future__ import annotations

from claim_validator.shared.code_tables.aaa_reject_codes import (
    get_aaa_reject_codes_table,
    lookup_aaa_reject,
)
from claim_validator.shared.code_tables.hcpcs import get_hcpcs_table, lookup_hcpcs
from claim_validator.shared.code_tables.hcr_actions import (
    get_hcr_action_codes_table,
    lookup_hcr_action,
)
from claim_validator.shared.code_tables.icd10 import get_icd10_table, lookup_icd10
from claim_validator.shared.code_tables.payer_directory import (
    get_payer_directory_table,
    lookup_payer,
)
from claim_validator.shared.code_tables.payer_routing import (
    get_payer_routing_table,
    load_default_mapping,
)
from claim_validator.shared.code_tables.revenue_codes import (
    get_revenue_codes_table,
    lookup_revenue_code,
)
from claim_validator.shared.code_tables.pos import get_pos_table, lookup_pos
from claim_validator.shared.code_tables.service_types import (
    get_service_types_table,
    lookup_service_type,
)
from claim_validator.shared.code_tables.taxonomy import get_taxonomy_table, lookup_taxonomy
from claim_validator.shared.code_tables.timely_filing import (
    get_filing_deadline,
    get_timely_filing_table,
)

__all__ = [
    "get_aaa_reject_codes_table",
    "get_filing_deadline",
    "get_hcpcs_table",
    "get_hcr_action_codes_table",
    "get_icd10_table",
    "get_payer_directory_table",
    "get_payer_routing_table",
    "get_pos_table",
    "get_service_types_table",
    "get_taxonomy_table",
    "get_timely_filing_table",
    "lookup_aaa_reject",
    "lookup_hcpcs",
    "lookup_hcr_action",
    "lookup_icd10",
    "get_revenue_codes_table",
    "load_default_mapping",
    "lookup_payer",
    "lookup_revenue_code",
    "lookup_pos",
    "lookup_service_type",
    "lookup_taxonomy",
]
