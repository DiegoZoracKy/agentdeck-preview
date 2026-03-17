"""
Unit tests for AgentDeckConfig.concurrency field (SPEC-PARALLEL v1.0.0 §4).

Tests verify:
- Default concurrency is 1 (sequential execution)
- Concurrency can be set to values >= 1
- Validation rejects invalid values (< 1)
"""

import pytest

from agentdeck.core.session import AgentDeckConfig


def test_concurrency_default_is_one():
    """Verify default concurrency is 1 (sequential)."""
    config = AgentDeckConfig()
    assert config.concurrency == 1


def test_concurrency_can_be_set():
    """Verify concurrency can be set to valid positive values."""
    config = AgentDeckConfig(concurrency=4)
    assert config.concurrency == 4

    config = AgentDeckConfig(concurrency=8)
    assert config.concurrency == 8

    config = AgentDeckConfig(concurrency=1)
    assert config.concurrency == 1


def test_concurrency_validation_rejects_zero():
    """Verify concurrency=0 raises ValueError."""
    with pytest.raises(ValueError, match="concurrency must be >= 1"):
        AgentDeckConfig(concurrency=0)


def test_concurrency_validation_rejects_negative():
    """Verify negative concurrency raises ValueError."""
    with pytest.raises(ValueError, match="concurrency must be >= 1"):
        AgentDeckConfig(concurrency=-1)

    with pytest.raises(ValueError, match="concurrency must be >= 1"):
        AgentDeckConfig(concurrency=-10)


def test_concurrency_error_message_helpful():
    """Verify error message includes guidance."""
    try:
        AgentDeckConfig(concurrency=0)
        pytest.fail("Should have raised ValueError")
    except ValueError as e:
        error_msg = str(e)
        assert "concurrency must be >= 1" in error_msg
        assert "got 0" in error_msg
        assert "Use concurrency=1 for sequential execution" in error_msg


def test_concurrency_works_with_other_config_fields():
    """Verify concurrency plays nicely with other config fields."""
    config = AgentDeckConfig(
        seed=42,
        run_dir="custom_runs",
        max_turns=500,
        concurrency=4,
    )

    assert config.seed == 42
    assert config.run_dir == "custom_runs"
    assert config.max_turns == 500
    assert config.concurrency == 4


def test_max_turns_validation_rejects_zero():
    """Verify max_turns=0 raises ValueError."""
    with pytest.raises(ValueError, match="max_turns must be >= 1"):
        AgentDeckConfig(max_turns=0)


def test_max_turns_validation_rejects_negative():
    """Verify negative max_turns raises ValueError."""
    with pytest.raises(ValueError, match="max_turns must be >= 1"):
        AgentDeckConfig(max_turns=-1)
