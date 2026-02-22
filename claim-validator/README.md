# claim-validator

Open-source healthcare claim validation library for Python 3.11+.

Rule-based and AI-powered validation for CMS-1500 / 837P claims.

## Installation

```bash
pip install claim-validator
```

## Quick Start

```python
from claim_validator import validate

result = validate({
    "billing_provider_npi": "1234567893",
    "diagnosis_codes": [{"code": "J06.9"}],
    "lines": [{"procedure_code": "99213", "charge_amount": 150.00}],
})
print(result.passed, result.findings)
```

## License

MIT
