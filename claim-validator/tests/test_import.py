"""Verify package imports correctly."""


def test_import_claim_validator() -> None:
    import claim_validator

    assert hasattr(claim_validator, "__version__")
    assert isinstance(claim_validator.__version__, str)


def test_version_is_string() -> None:
    from claim_validator import __version__

    assert isinstance(__version__, str)
    assert len(__version__) > 0
