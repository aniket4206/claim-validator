"""Command-line interface for claim-validator.

Provides two commands:
    claim-validator validate <file.json>   — validate a claim from JSON
    claim-validator serve                   — start the REST API server
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _validate_command(args: argparse.Namespace) -> None:
    """Run validation on a JSON claim file or stdin."""
    from claim_validator._api import validate
    from claim_validator.conf import ClaimValidatorSettings

    # Read claim JSON
    if args.file == "-":
        raw = sys.stdin.read()
    else:
        path = Path(args.file)
        if not path.exists():
            print(json.dumps({"error": f"File not found: {args.file}"}))
            sys.exit(1)
        raw = path.read_text()

    try:
        claim_data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"Invalid JSON: {exc}"}))
        sys.exit(1)

    # Build settings
    settings_kwargs: dict[str, Any] = {}
    if args.ai_provider:
        ai_config: dict[str, Any] = {"provider": args.ai_provider}
        if args.ai_api_key:
            ai_config["api_key"] = args.ai_api_key
        if args.ai_model:
            ai_config["model"] = args.ai_model
        if args.ai_base_url:
            ai_config["base_url"] = args.ai_base_url
        settings_kwargs["ai_config"] = ai_config
        settings_kwargs["ai_validators"] = [
            "claim_validator.validators.ai.code_validation.CodeValidationAI",
            "claim_validator.validators.ai.coverage_check.CoverageCheckAI",
            "claim_validator.validators.ai.prior_auth.PriorAuthAI",
        ]

    if args.skip_ai_on_failure is not None:
        settings_kwargs["skip_ai_on_rule_failure"] = args.skip_ai_on_failure

    settings = ClaimValidatorSettings(**settings_kwargs) if settings_kwargs else None

    # Validate
    try:
        result = validate(claim_data, settings=settings)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)

    # Output
    output = {
        "passed": result.passed,
        "execution_time": result.execution_time,
        "total_findings": len(result.findings),
        "total_errors": len(result.errors),
        "total_warnings": len(result.warnings),
        "findings": [
            {
                "code": f.code,
                "message": f.message,
                "severity": f.severity.value,
                "field_name": f.field_name,
                "line_number": f.line_number,
                "suggestion": f.suggestion,
            }
            for f in result.findings
        ],
        "phases": [
            {
                "phase": p.phase,
                "execution_time": p.execution_time,
                "validators": [
                    {
                        "name": v.validator_name,
                        "findings_count": len(v.findings),
                    }
                    for v in p.validator_outputs
                ],
            }
            for p in result.phase_results
        ],
    }

    indent = 2 if args.pretty else None
    print(json.dumps(output, indent=indent))
    sys.exit(0 if result.passed else 1)


def _serve_command(args: argparse.Namespace) -> None:
    """Start the REST API server."""
    try:
        import uvicorn  # noqa: F811
    except ImportError:
        print(
            "Error: uvicorn is required to run the server.\n"
            "Install it with: pip install 'claim-validator[server]'"
        )
        sys.exit(1)

    try:
        from claim_validator.server import app  # noqa: F401
    except ImportError:
        print(
            "Error: fastapi is required to run the server.\n"
            "Install it with: pip install 'claim-validator[server]'"
        )
        sys.exit(1)

    uvicorn.run(
        "claim_validator.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def _version_command(args: argparse.Namespace) -> None:  # noqa: ARG001
    """Print version information."""
    from claim_validator import __version__

    print(f"claim-validator {__version__}")


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="claim-validator",
        description="Healthcare claim validation — rule-based and AI-powered",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── validate ──────────────────────────────────────────────
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate a claim from a JSON file",
    )
    validate_parser.add_argument(
        "file",
        help='Path to JSON claim file, or "-" for stdin',
    )
    validate_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    validate_parser.add_argument(
        "--ai-provider",
        help="AI provider: anthropic, openai, openai_compatible",
    )
    validate_parser.add_argument(
        "--ai-api-key",
        help="API key for the AI provider",
    )
    validate_parser.add_argument(
        "--ai-model",
        help="Model name for the AI provider",
    )
    validate_parser.add_argument(
        "--ai-base-url",
        help="Base URL for OpenAI-compatible providers (e.g., Ollama)",
    )
    validate_parser.add_argument(
        "--skip-ai-on-failure",
        type=lambda v: v.lower() in ("true", "1", "yes"),
        default=None,
        help="Skip AI phase if rule-based has errors (true/false)",
    )
    validate_parser.set_defaults(func=_validate_command)

    # ── serve ─────────────────────────────────────────────────
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start the REST API server",
    )
    serve_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind host (default: 0.0.0.0)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port (default: 8000)",
    )
    serve_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    serve_parser.set_defaults(func=_serve_command)

    # ── version ───────────────────────────────────────────────
    version_parser = subparsers.add_parser(
        "version",
        help="Print version information",
    )
    version_parser.set_defaults(func=_version_command)

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
