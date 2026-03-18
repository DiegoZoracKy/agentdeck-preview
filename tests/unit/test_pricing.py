"""Unit tests for pricing utilities and packaged pricing data."""

from __future__ import annotations

import logging

import pytest

from agentdeck.utils import pricing


@pytest.fixture(autouse=True)
def reset_pricing_cache():
    """Keep tests isolated from the global pricing cache."""
    pricing.reload_pricing()
    yield
    pricing.reload_pricing()


def test_load_pricing_data_reads_packaged_yaml():
    """The packaged pricing snapshot should expose providers and metadata."""
    data = pricing.load_pricing_data()

    assert "metadata" in data
    assert "openai" in data
    assert "anthropic" in data
    assert "google" in data
    assert "sources" in data["metadata"]


def test_validate_pricing_structure_rejects_non_mapping_root():
    """Validation should fail loudly before iterating malformed roots."""
    with pytest.raises(ValueError, match="pricing.yaml root must be a dict"):
        pricing._validate_pricing_structure([])  # type: ignore[arg-type]


def test_get_model_pricing_uses_provider_default():
    """Unknown models should fall back to provider _default when present."""
    data = pricing.load_pricing_data()
    expected = data["openai"]["_default"]
    input_cost, output_cost = pricing.get_model_pricing("openai", "nonexistent-openai-model")

    assert input_cost == expected["input_cost_per_million"]
    assert output_cost == expected["output_cost_per_million"]


def test_calculate_cost_returns_zero_and_warns_for_unknown_provider(caplog):
    """calculate_cost should preserve the zero-cost fallback on missing pricing."""
    with caplog.at_level(logging.WARNING):
        cost = pricing.calculate_cost("missing-provider", "missing-model", 1000, 500)

    assert cost == 0.0
    assert "Returning $0.00" in caplog.text


def test_load_pricing_data_returns_empty_dict_when_file_missing(monkeypatch):
    """Missing pricing.yaml should not crash callers."""
    pricing._pricing_data = None
    monkeypatch.setattr(pricing.Path, "exists", lambda self: False)

    data = pricing.load_pricing_data()

    assert data == {}
