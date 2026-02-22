#!/usr/bin/env python3
"""End-to-end demo: every validation layer with local Ollama.

Usage:
    # 1. Start Ollama with a model:
    #    ollama pull mistral
    #    ollama serve
    #
    # 2. Run this script:
    #    uv run python demo_e2e.py
    #
    # 3. Without Ollama (rule-based only):
    #    uv run python demo_e2e.py --no-ai

"""

from __future__ import annotations

import argparse
import sys
import textwrap

from claim_validator import (
    ClaimData,
    ClaimDeidentifier,
    ClaimValidatorSettings,
    Severity,
    ValidationPipeline,
    validate,
)

# ── Default AI validators (dotted paths) ────────────────────────
AI_VALIDATORS = [
    "claim_validator.validators.ai.code_validation.CodeValidationAI",
    "claim_validator.validators.ai.coverage_check.CoverageCheckAI",
    "claim_validator.validators.ai.prior_auth.PriorAuthAI",
]

# ── Ollama defaults ─────────────────────────────────────────────
DEFAULT_OLLAMA_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "tinyllama"


# ================================================================
# Claim Scenarios
# ================================================================

def clean_claim() -> dict:
    """A perfectly valid claim — should pass rule-based with zero errors."""
    return {
        "billing_provider_npi": "1234567893",
        "subscriber_id": "XYZ987654",
        "subscriber_first_name": "Alice",
        "subscriber_last_name": "Smith",
        "subscriber_dob": "1975-03-10",
        "subscriber_gender": "F",
        "patient_first_name": "Alice",
        "patient_last_name": "Smith",
        "patient_dob": "1975-03-10",
        "patient_gender": "F",
        "patient_relationship": "self",
        "payer_id": "BCBS001",
        "payer_name": "Blue Cross Blue Shield",
        "place_of_service": "11",
        "total_charge": 150.00,
        "filing_date": "2026-02-01",
        "diagnosis_codes": [
            {"code": "J06.9", "pointer": 1},
        ],
        "lines": [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
                "service_date_to": "2026-01-15",
                "place_of_service": "11",
            },
        ],
    }


def broken_claim() -> dict:
    """A claim with multiple rule-based errors.

    - Invalid NPI (fails Luhn)
    - Missing subscriber ID
    - Negative charge amount
    - Bad diagnosis pointer
    - Duplicate lines
    """
    return {
        "billing_provider_npi": "1234567890",  # BAD Luhn
        # subscriber_id intentionally missing
        "patient_first_name": "Bob",
        "patient_last_name": "Jones",
        "patient_dob": "1990-06-15",
        "patient_gender": "M",
        "payer_id": "UHC01",
        "total_charge": 100.00,
        "filing_date": "2026-02-10",
        "diagnosis_codes": [
            {"code": "J06.9", "pointer": 1},
        ],
        "lines": [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1, 5],  # pointer 5 doesn't exist
                "charge_amount": -50.00,  # negative
                "service_date_from": "2026-01-20",
            },
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-20",
            },
        ],
    }


def ai_interesting_claim() -> dict:
    """A claim that is rule-valid but clinically interesting for AI.

    - Male patient with vaginitis diagnosis (N76.0 — implausible)
    - High-cost MRI (likely needs prior auth)
    Uses only codes that exist in the bundled ICD-10 table.
    """
    return {
        "billing_provider_npi": "1234567893",
        "subscriber_id": "MEM555111",
        "subscriber_first_name": "Charlie",
        "subscriber_last_name": "Brown",
        "subscriber_dob": "1965-08-22",
        "subscriber_gender": "M",
        "patient_first_name": "Charlie",
        "patient_last_name": "Brown",
        "patient_dob": "1965-08-22",
        "patient_gender": "M",
        "patient_relationship": "self",
        "payer_id": "AETNA01",
        "payer_name": "Aetna",
        "place_of_service": "11",
        "total_charge": 1600.00,
        "filing_date": "2026-02-15",
        "diagnosis_codes": [
            {"code": "M54.5", "pointer": 1},  # low back pain
            {"code": "N76.0", "pointer": 2},  # acute vaginitis — male!
        ],
        "lines": [
            {
                "procedure_code": "72148",  # MRI lumbar spine
                "diagnosis_pointers": [1],
                "charge_amount": 800.00,
                "service_date_from": "2026-02-01",
                "place_of_service": "11",
            },
            {
                "procedure_code": "99214",  # office visit
                "diagnosis_pointers": [2],
                "charge_amount": 800.00,
                "service_date_from": "2026-02-01",
                "place_of_service": "11",
            },
        ],
    }


# ================================================================
# Display helpers
# ================================================================

DIVIDER = "=" * 72


def print_header(title: str) -> None:
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)


def print_findings(result) -> None:  # noqa: ANN001
    """Pretty-print pipeline results."""
    status = "PASSED" if result.passed else "FAILED"
    print(f"\n  Result: {status}")
    print(f"  Time:   {result.execution_time:.3f}s")
    print(f"  Phases: {len(result.phase_results)}")
    print(
        f"  Findings: {len(result.findings)} "
        f"({len(result.errors)} errors, "
        f"{len(result.warnings)} warnings)"
    )

    for phase in result.phase_results:
        print(f"\n  --- Phase: {phase.phase} "
              f"({phase.execution_time:.3f}s) ---")
        for output in phase.validator_outputs:
            if output.findings:
                for f in output.findings:
                    sev = "ERR" if f.severity == Severity.ERROR else "WRN"
                    print(
                        f"  [{sev}] {f.code}"
                    )
                    print(
                        f"        {f.message}"
                    )
                    if f.field_name:
                        line_str = (
                            f" line={f.line_number}"
                            if f.line_number
                            else ""
                        )
                        print(
                            f"        field={f.field_name}"
                            f"{line_str}"
                        )
                    if f.suggestion:
                        wrapped = textwrap.fill(
                            f.suggestion, width=60,
                            initial_indent="        -> ",
                            subsequent_indent="           ",
                        )
                        print(wrapped)
                    if f.context:
                        err = f.context.get("error", "")
                        if err:
                            print(
                                f"        ctx: {err[:120]}"
                            )
            else:
                print(
                    f"  [OK]  {output.validator_name}: "
                    f"no findings"
                )

    print()


# ================================================================
# Demo scenarios
# ================================================================

def demo_rule_based_clean() -> None:
    """Scenario 1: Valid claim — all rule-based validators pass."""
    print_header("Scenario 1: Clean Claim (rule-based only)")
    result = validate(clean_claim())
    print_findings(result)


def demo_rule_based_broken() -> None:
    """Scenario 2: Broken claim — multiple rule-based errors."""
    print_header("Scenario 2: Broken Claim (rule-based errors)")
    result = validate(broken_claim())
    print_findings(result)


def demo_deidentification() -> None:
    """Scenario 3: Show de-identification stripping PHI."""
    print_header("Scenario 3: De-identification Demo")
    claim = ClaimData(**ai_interesting_claim())
    deidentified = ClaimDeidentifier.deidentify(claim)

    print("\n  Original (PHI present):")
    print(f"    patient_first_name = {claim.patient_first_name}")
    print(f"    patient_last_name  = {claim.patient_last_name}")
    print(f"    patient_dob        = {claim.patient_dob}")
    print(f"    subscriber_id      = {claim.subscriber_id}")

    print("\n  De-identified (PHI stripped):")
    print(f"    patient_age        = {deidentified.patient_age}")
    print(f"    patient_gender     = {deidentified.patient_gender}")
    print(f"    payer_id           = {deidentified.payer_id}")
    print(f"    billing_npi        = {deidentified.billing_provider_npi}")
    print(f"    diagnosis_codes    = {deidentified.diagnosis_codes}")
    for i, line in enumerate(deidentified.lines, 1):
        print(
            f"    line {i}: {line.procedure_code} "
            f"${line.charge_amount:.2f}"
        )

    # Confirm PHI is gone
    assert not hasattr(deidentified, "patient_first_name")
    assert not hasattr(deidentified, "subscriber_id")
    print("\n  [OK] No PHI fields present on DeidentifiedClaim")
    print()


def demo_ai_phase(
    model: str,
    base_url: str,
) -> None:
    """Scenario 4: Full pipeline — rule-based + AI with Ollama."""
    print_header(
        f"Scenario 4: Full Pipeline with AI "
        f"(model={model})"
    )

    settings = ClaimValidatorSettings(
        ai_validators=AI_VALIDATORS,
        skip_ai_on_rule_failure=True,
        ai_config={
            "provider": "openai_compatible",
            "api_key": "ollama",
            "model": model,
            "base_url": base_url,
        },
    )

    pipeline = ValidationPipeline.from_settings(settings)

    # 4a: Clean claim — AI should run (no rule errors)
    print("\n  4a: Clean claim -> AI validators run")
    result_clean = pipeline.run(
        ClaimData(**clean_claim()),
    )
    print_findings(result_clean)

    # 4b: Clinically interesting claim — AI should flag issues
    print("  4b: Clinically suspicious claim -> AI flags")
    result_suspicious = pipeline.run(
        ClaimData(**ai_interesting_claim()),
    )
    print_findings(result_suspicious)

    # 4c: Broken claim — AI should be SKIPPED (rule errors)
    print("  4c: Broken claim -> AI skipped (rule errors)")
    result_broken = pipeline.run(
        ClaimData(**broken_claim()),
    )
    print_findings(result_broken)
    ai_phases = [
        p for p in result_broken.phase_results
        if p.phase == "ai"
    ]
    if not ai_phases:
        print("  [OK] AI phase was correctly skipped\n")


def demo_ai_force_on_failure(
    model: str,
    base_url: str,
) -> None:
    """Scenario 5: Force AI even when rules fail."""
    print_header(
        "Scenario 5: AI runs despite rule-based errors "
        "(skip_ai_on_rule_failure=False)"
    )

    settings = ClaimValidatorSettings(
        ai_validators=AI_VALIDATORS,
        skip_ai_on_rule_failure=False,
        ai_config={
            "provider": "openai_compatible",
            "api_key": "ollama",
            "model": model,
            "base_url": base_url,
        },
    )

    pipeline = ValidationPipeline.from_settings(settings)
    result = pipeline.run(ClaimData(**broken_claim()))
    print_findings(result)

    ai_phases = [
        p for p in result.phase_results
        if p.phase == "ai"
    ]
    if ai_phases:
        print("  [OK] AI phase ran despite rule errors\n")


# ================================================================
# Main
# ================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="End-to-end claim-validator demo",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Skip AI scenarios (no Ollama needed)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_OLLAMA_URL,
        help=f"Ollama API URL (default: {DEFAULT_OLLAMA_URL})",
    )
    args = parser.parse_args()

    print("\n" + DIVIDER)
    print("  claim-validator End-to-End Demo")
    print(DIVIDER)

    # Always run rule-based demos
    demo_rule_based_clean()
    demo_rule_based_broken()
    demo_deidentification()

    if args.no_ai:
        print("\n  Skipping AI scenarios (--no-ai)\n")
        return

    # AI demos require Ollama
    print(
        f"\n  Connecting to Ollama at {args.base_url}"
        f" with model '{args.model}'..."
    )
    try:
        demo_ai_phase(args.model, args.base_url)
        demo_ai_force_on_failure(args.model, args.base_url)
    except Exception as exc:
        print(f"\n  AI demo failed: {exc}")
        print(
            "  Make sure Ollama is running: "
            "ollama serve"
        )
        print(
            f"  And the model is pulled: "
            f"ollama pull {args.model}"
        )
        sys.exit(1)

    print(DIVIDER)
    print("  All scenarios complete!")
    print(DIVIDER + "\n")


if __name__ == "__main__":
    main()
