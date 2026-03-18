"""Live integration test for Groq AI provider and ClaimMD clearinghouse.

Requires real API keys in .env:
  CLAIM_VALIDATOR_AI_PROVIDER=groq
  CLAIM_VALIDATOR_AI_API_KEY=gsk_...
  CLAIM_VALIDATOR_AI_MODEL=...
  CLAIMMD_API_KEY=...
"""

from __future__ import annotations

import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_groq_provider() -> bool:
    """Test 1: Groq LLM provider — send a simple medical coding question."""
    section("TEST 1: Groq LLM Provider")

    provider = os.getenv("CLAIM_VALIDATOR_AI_PROVIDER", "groq")
    api_key = os.getenv("CLAIM_VALIDATOR_AI_API_KEY", "")
    model = os.getenv("CLAIM_VALIDATOR_AI_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        print("SKIP: No CLAIM_VALIDATOR_AI_API_KEY set")
        return False

    print(f"Provider: {provider}")
    print(f"Model:    {model}")
    print(f"API Key:  {api_key[:10]}...")

    from claim_validator.llm.factory import get_llm_client
    from claim_validator.llm.base import Message

    try:
        start = time.perf_counter()
        client = get_llm_client(
            provider,
            api_key=api_key,
            model=model,
            base_url="https://api.groq.com/openai/v1",
        )
        print(f"Client created: {client.provider_name}")

        messages = [
            Message(
                role="system",
                content="You are a medical coding expert. Be very concise.",
            ),
            Message(
                role="user",
                content="Is ICD-10 code J06.9 valid? What does it mean? One sentence.",
            ),
        ]

        response = client.send_messages(messages)
        elapsed = time.perf_counter() - start

        print(f"Response ({elapsed:.2f}s): {response[:200]}")
        print(f"\nPASS: Groq provider works")
        return True
    except Exception as e:
        print(f"\nFAIL: {type(e).__name__}: {e}")
        return False


def test_groq_rejection_summary() -> bool:
    """Test 2: Groq generates a rejection summary from findings."""
    section("TEST 2: Groq Rejection Summary")

    provider = os.getenv("CLAIM_VALIDATOR_AI_PROVIDER", "groq")
    api_key = os.getenv("CLAIM_VALIDATOR_AI_API_KEY", "")
    model = os.getenv("CLAIM_VALIDATOR_AI_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        print("SKIP: No API key")
        return False

    from claim_validator.llm.factory import get_llm_client
    from claim_validator.llm.base import Message

    try:
        start = time.perf_counter()
        client = get_llm_client(
            provider,
            api_key=api_key,
            model=model,
            base_url="https://api.groq.com/openai/v1",
        )

        findings_text = """
- [ERROR] INVALID_NPI: Billing provider NPI '123456789' failed Luhn check-digit validation
- [ERROR] MISSING_REQUIRED_FIELD: subscriber_dob is required but missing
- [WARNING] APPROACHING_DEADLINE: Payer filing deadline is in 15 days
        """.strip()

        messages = [
            Message(
                role="system",
                content=(
                    "You are a healthcare billing expert. Summarize why "
                    "this claim validation failed in plain language for "
                    "billing staff. Include specific suggestions to fix "
                    "each issue. Be concise."
                ),
            ),
            Message(
                role="user",
                content=f"Claim validation findings:\n{findings_text}",
            ),
        ]

        response = client.send_messages(messages)
        elapsed = time.perf_counter() - start

        print(f"Summary ({elapsed:.2f}s):\n{response[:500]}")
        print(f"\nPASS: Rejection summary generation works")
        return True
    except Exception as e:
        print(f"\nFAIL: {type(e).__name__}: {e}")
        return False


def test_claimmd_eligibility() -> bool:
    """Test 3: ClaimMD eligibility check (270/271)."""
    section("TEST 3: ClaimMD Eligibility Check")

    api_key = os.getenv("CLAIMMD_API_KEY", "")
    base_url = os.getenv("CLAIMMD_URL", "https://svc.claim.md")

    if not api_key:
        print("SKIP: No CLAIMMD_API_KEY set")
        return False

    print(f"URL:     {base_url}")
    print(f"API Key: {api_key[:10]}...")

    from claim_validator.clearinghouse.providers.claimmd import ClaimMDClient

    try:
        start = time.perf_counter()
        client = ClaimMDClient(account_key=api_key, base_url=base_url)

        result = client.check_eligibility({
            "payer_id": "00520",
            "npi": "1245319599",
            "subscriber_id": "TEST123",
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1980-01-15",
            "service_date": "2026-03-18",
        })

        elapsed = time.perf_counter() - start

        print(f"Status:      {result.status}")
        print(f"Eligible:    {result.eligible}")
        print(f"Reference:   {result.reference_id}")
        print(f"Errors:      {result.errors}")
        print(f"Time:        {elapsed:.2f}s")
        print(f"Raw keys:    {list(result.raw_response.keys())[:10]}")

        client.close()
        print(f"\nPASS: ClaimMD eligibility works")
        return True
    except Exception as e:
        print(f"\nFAIL: {type(e).__name__}: {e}")
        return False


def test_claimmd_prior_auth() -> bool:
    """Test 4: ClaimMD prior authorization submission (278)."""
    section("TEST 4: ClaimMD Prior Authorization")

    api_key = os.getenv("CLAIMMD_API_KEY", "")
    base_url = os.getenv("CLAIMMD_URL", "https://svc.claim.md")

    if not api_key:
        print("SKIP: No CLAIMMD_API_KEY set")
        return False

    from claim_validator.clearinghouse.providers.claimmd import ClaimMDClient

    try:
        start = time.perf_counter()
        client = ClaimMDClient(account_key=api_key, base_url=base_url)

        result = client.submit_prior_auth({
            "payer_id": "00520",
            "npi": "1245319599",
            "subscriber_id": "TEST123",
            "first_name": "John",
            "last_name": "Doe",
            "dob": "1980-01-15",
            "diagnosis_codes": ["M79.3"],
            "service_lines": [
                {
                    "cpt_code": "72148",
                    "from_date": "2026-04-01",
                    "quantity": 1,
                },
            ],
        })

        elapsed = time.perf_counter() - start

        print(f"Status:      {result.status}")
        print(f"Accepted:    {result.accepted}")
        print(f"Reference:   {result.reference_id}")
        print(f"Errors:      {result.errors}")
        print(f"Time:        {elapsed:.2f}s")
        print(f"Raw keys:    {list(result.raw_response.keys())[:10]}")

        client.close()
        print(f"\nPASS: ClaimMD PA submission works")
        return True
    except Exception as e:
        print(f"\nFAIL: {type(e).__name__}: {e}")
        return False


def test_validate_with_groq() -> bool:
    """Test 5: Full claim validation with Groq AI validators."""
    section("TEST 5: Full Claim Validation (Rule-Based + Groq AI)")

    provider = os.getenv("CLAIM_VALIDATOR_AI_PROVIDER", "groq")
    api_key = os.getenv("CLAIM_VALIDATOR_AI_API_KEY", "")
    model = os.getenv("CLAIM_VALIDATOR_AI_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        print("SKIP: No API key")
        return False

    from claim_validator import validate

    try:
        start = time.perf_counter()

        claim = {
            "billing_provider_npi": "1245319599",
            "billing_provider_taxonomy": "207Q00000X",
            "rendering_provider_npi": "1245319599",
            "subscriber_id": "SUB987654",
            "subscriber_first_name": "Jane",
            "subscriber_last_name": "Smith",
            "subscriber_dob": "1985-06-15",
            "subscriber_gender": "F",
            "payer_id": "00520",
            "payer_name": "Test Payer",
            "claim_type": "professional",
            "place_of_service": "11",
            "total_charge": "150.00",
            "diagnosis_codes": [
                {"code": "J06.9", "pointer": 1},
            ],
            "lines": [
                {
                    "procedure_code": "99213",
                    "charge_amount": "150.00",
                    "units": "1",
                    "diagnosis_pointers": [1],
                    "service_date_from": "2026-03-18",
                },
            ],
        }

        result = validate(
            claim,
            ai_config={
                "provider": provider,
                "api_key": api_key,
                "model": model,
                "base_url": "https://api.groq.com/openai/v1",
            },
        )

        elapsed = time.perf_counter() - start

        print(f"Passed:     {result.passed}")
        print(f"Errors:     {len(result.errors)}")
        print(f"Warnings:   {len(result.warnings)}")
        print(f"Time:       {elapsed:.2f}s")
        print(f"Phases:     {len(result.phase_results)}")
        for phase in result.phase_results:
            print(f"  - {phase.phase}: {len(phase.findings)} findings ({phase.execution_time:.2f}s)")

        if result.findings:
            print(f"\nFindings:")
            for f in result.findings[:10]:
                print(f"  [{f.severity.value}] {f.code}: {f.message}")

        print(f"\nPASS: Full validation with Groq AI works")
        return True
    except Exception as e:
        print(f"\nFAIL: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Live Integration Tests: Groq + ClaimMD")
    print(f"Python: {sys.version}")
    print(f"CWD:    {os.getcwd()}")

    results = {}
    results["groq_basic"] = test_groq_provider()
    results["groq_summary"] = test_groq_rejection_summary()
    results["claimmd_elig"] = test_claimmd_eligibility()
    results["claimmd_pa"] = test_claimmd_prior_auth()
    results["validate_groq"] = test_validate_with_groq()

    section("RESULTS")
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {status}: {name}")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\n  {passed}/{total} tests passed")

    sys.exit(0 if passed == total else 1)
