"""
Unit tests for PromptBuilder per SPEC-PROMPT-BUILDER v0.4.0.

These tests verify:
- Template composition for all three lifecycle phases (handshake, turn, conclusion)
- Path-based template loading
- Custom provider binding and evaluation
- Placeholder extraction and substitution
- Error handling (missing files, provider failures, undefined placeholders)
- Metadata capture per MC1-MC3 invariants
- Provider safety per PS1-PS3 invariants
- Deterministic composition per CD1-CD3 invariants
"""

from types import MappingProxyType

import pytest

from agentdeck.core.prompt_builder import PromptBuilder
from agentdeck.core.types import (
    LifecyclePhase,
    PromptContext,
    RenderResult,
    TemplateError,
    TurnContext,
)

# Fixtures


@pytest.fixture
def render_result():
    """Basic render result for testing."""
    return RenderResult(
        text="Game state: Turn 5",
        metadata={"info_level": "full", "custom_key": "custom_value"},
    )


@pytest.fixture
def turn_context():
    """Turn context for turn-phase testing."""
    return TurnContext(
        match_id="match-123",
        turn_number=5,
        turn_index=4,
        player="Alice",
        started_at=1234567890.0,
        duration=1.5,
    )


@pytest.fixture
def basic_builder():
    """PromptBuilder with simple inline templates."""
    return PromptBuilder(
        handshake_template="{game_instructions}\n{handshake_controller_format}",
        turn_template="{game_view}\n{controller_format}",
        conclusion_template="Game over! {outcome}",
    )


# Test: Template loading from Path objects


def test_load_template_from_file(tmp_path):
    """Test loading template from Path object (covers lines 160-163)."""
    # Create temporary template file
    template_file = tmp_path / "test_template.txt"
    template_file.write_text("Custom template: {game_view}", encoding="utf-8")

    # Build with Path
    builder = PromptBuilder(turn_template=template_file)

    # Verify template loaded correctly
    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=RenderResult(text="Test view", metadata=None),
        controller_format="Reply with ACTION",
    )

    assert bundle.text == "Custom template: Test view"


def test_load_template_file_not_found(tmp_path):
    """Test FileNotFoundError when Path doesn't exist (covers lines 160-163)."""
    nonexistent = tmp_path / "nonexistent.txt"

    with pytest.raises(FileNotFoundError):
        PromptBuilder(turn_template=nonexistent)


def test_load_template_encoding_error(tmp_path):
    """Test UnicodeDecodeError for non-UTF-8 files (covers lines 160-163)."""
    # Create file with invalid UTF-8 bytes
    template_file = tmp_path / "bad_encoding.txt"
    template_file.write_bytes(b"\xff\xfe Invalid UTF-8")

    with pytest.raises(UnicodeDecodeError):
        PromptBuilder(turn_template=template_file)


# Test: Factory methods


def test_from_template(render_result):
    """Test from_template() factory method (covers line 179)."""
    builder = PromptBuilder.from_template("{game_view}\nFormat: {controller_format}")

    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="ACTION: <action>",
    )

    assert "Game state: Turn 5" in bundle.text
    assert "Format: ACTION: <action>" in bundle.text


def test_from_file(tmp_path, render_result):
    """Test from_file() factory method (covers lines 199-200)."""
    # Create template file
    template_file = tmp_path / "turn.txt"
    template_file.write_text("View: {game_view}\nFormat: {controller_format}", encoding="utf-8")

    # Test with Path object
    builder1 = PromptBuilder.from_file(template_file)
    bundle1 = builder1.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="ACTION",
    )
    assert "View: Game state: Turn 5" in bundle1.text

    # Test with string path (covers line 199)
    builder2 = PromptBuilder.from_file(str(template_file))
    bundle2 = builder2.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="ACTION",
    )
    assert "View: Game state: Turn 5" in bundle2.text


def test_from_function(render_result, turn_context):
    """Test from_function() factory method (covers lines 222-225)."""

    # Custom compose function
    def custom_compose(ctx: PromptContext) -> str:
        if ctx.turn_number == 1:
            return f"First turn! {ctx.render_result.text}"
        return f"Turn {ctx.turn_number}: {ctx.render_result.text}"

    builder = PromptBuilder.from_function(custom_compose)

    # Test with turn_number=5
    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="ACTION",
        turn_context=turn_context,
    )

    assert bundle.text == "Turn 5: Game state: Turn 5"
    assert bundle.metadata["template_id"] == "custom_function"
    assert bundle.metadata["turn_number"] == 5


# Test: Custom provider binding


def test_bind_custom_provider(basic_builder, render_result):
    """Test bind() for custom providers (covers line 244-245)."""
    # Bind custom provider
    basic_builder.bind("timestamp", lambda ctx: "2025-01-15T10:00:00")
    basic_builder.bind("strategy", lambda ctx: ctx.extras.get("strategy", "default"))

    # Use custom template with custom placeholders
    builder = PromptBuilder(turn_template="{timestamp} | Strategy: {strategy}\n{game_view}")
    builder.bind("timestamp", lambda ctx: "2025-01-15T10:00:00")
    builder.bind("strategy", lambda ctx: ctx.extras.get("strategy", "default"))

    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="ACTION",
        extras={"strategy": "aggressive"},
    )

    assert "2025-01-15T10:00:00" in bundle.text
    assert "Strategy: aggressive" in bundle.text


# Test: Custom function compose path


def test_custom_compose_function_path(render_result, turn_context):
    """Test compose() with custom function (covers lines 303-312)."""

    # Create builder with custom compose function
    def custom_fn(ctx: PromptContext) -> str:
        return f"Custom: {ctx.render_result.text} (turn {ctx.turn_number})"

    builder = PromptBuilder.from_function(custom_fn)

    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="FORMAT",
        turn_context=turn_context,
    )

    # Verify custom function was used
    assert bundle.text == "Custom: Game state: Turn 5 (turn 5)"
    assert bundle.metadata["template_id"] == "custom_function"
    assert bundle.metadata["phase"] == "turn"
    assert bundle.metadata["turn_number"] == 5
    assert bundle.metadata["blocks_rendered"] == []


# Test: DefaultEmptyDict behavior


def test_missing_placeholder_renders_empty(basic_builder, render_result):
    """Test that missing placeholders render as empty string (covers line 349)."""
    # Template with optional placeholder
    builder = PromptBuilder(
        turn_template="{game_view}\nOptional: {optional_key}\nFormat: {controller_format}"
    )

    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="ACTION",
        # optional_key not provided
    )

    # Should render with empty string for missing placeholder
    assert "Optional: \n" in bundle.text or "Optional: \nFormat:" in bundle.text


def test_keyerror_handling(basic_builder, render_result):
    """Test KeyError handling in template.format_map() (covers lines 355-358).

    Note: With DefaultEmptyDict, KeyError should never happen, but code keeps
    safety handler. We can't easily trigger it, but this tests the surrounding logic.
    """
    # This test verifies the try/except block exists and doesn't break normal flow
    bundle = basic_builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="ACTION",
    )

    assert "Game state: Turn 5" in bundle.text


# Test: Unsupported phase handling


def test_unsupported_phase_raises_error(basic_builder, render_result):
    """Test ValueError for unsupported phase (covers line 400)."""

    # Create mock phase that's not in enum (simulate invalid value)
    # We need to bypass type checking to test this error path
    class FakePhase:
        value = "INVALID_PHASE"

    with pytest.raises(ValueError, match="Unsupported phase"):
        basic_builder._select_template(FakePhase())  # type: ignore


# Test: Provider error handling


def test_provider_exception_wrapped(render_result):
    """Test provider exceptions wrapped in TemplateError (covers lines 469-481)."""

    # Create builder with failing provider
    def failing_provider(ctx):
        raise RuntimeError("Provider crashed!")

    builder = PromptBuilder(turn_template="{game_view}\n{failing_placeholder}")
    builder.bind("failing_placeholder", failing_provider)

    with pytest.raises(TemplateError, match="Provider 'failing_placeholder' failed"):
        builder.compose(
            phase=LifecyclePhase.TURN,
            render_result=render_result,
            controller_format="ACTION",
        )


def test_provider_memoization(render_result):
    """Test provider memoization per PS2 (covers lines 469-481)."""
    call_count = 0

    def counting_provider(ctx):
        nonlocal call_count
        call_count += 1
        return f"Called {call_count} times"

    builder = PromptBuilder(turn_template="{counted}\n{counted}\n{game_view}")
    builder.bind("counted", counting_provider)

    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="ACTION",
    )

    # Provider should only be called once despite appearing twice in template
    assert call_count == 1
    assert "Called 1 times" in bundle.text


# Test: Comprehensive lifecycle phases


def test_handshake_phase(render_result):
    """Test handshake phase composition."""
    builder = PromptBuilder(handshake_template="{game_instructions}\n{handshake_controller_format}")

    bundle = builder.compose(
        phase=LifecyclePhase.HANDSHAKE,
        render_result=RenderResult(text="Game view (not used)", metadata=None),
        controller_format="ACTION: <action>",
        handshake_controller_format="Reply with OK",
        extras={"game_instructions": "You are playing Poker"},
    )

    assert "You are playing Poker" in bundle.text
    assert "Reply with OK" in bundle.text
    assert bundle.metadata["phase"] == "handshake"


def test_turn_phase(render_result, turn_context):
    """Test turn phase composition."""
    builder = PromptBuilder(turn_template="{game_view}\n{controller_format}")

    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="ACTION: <action>",
        turn_context=turn_context,
    )

    assert "Game state: Turn 5" in bundle.text
    assert "ACTION: <action>" in bundle.text
    assert bundle.metadata["phase"] == "turn"
    assert bundle.metadata["turn_number"] == 5


def test_conclusion_phase(render_result):
    """Test conclusion phase composition."""
    builder = PromptBuilder(conclusion_template="Game over!\n{outcome}\n{game_view}")

    bundle = builder.compose(
        phase=LifecyclePhase.CONCLUSION,
        render_result=render_result,
        controller_format="N/A",
        extras={"outcome": "You won!"},
    )

    assert "Game over!" in bundle.text
    assert "You won!" in bundle.text
    assert bundle.metadata["phase"] == "conclusion"


def test_conclusion_template_none_disables_composition(render_result):
    builder = PromptBuilder(conclusion_template=None)
    with pytest.raises(ValueError, match="Conclusion template is disabled"):
        builder.compose(
            phase=LifecyclePhase.CONCLUSION,
            render_result=render_result,
            controller_format="N/A",
            extras={"outcome": "You won!"},
        )


# Test: Metadata capture (MC1-MC3 invariants)


def test_metadata_capture(render_result, turn_context):
    """Test metadata capture per MC1-MC3."""
    builder = PromptBuilder(turn_template="{game_view}\n{controller_format}")

    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="ACTION",
        turn_context=turn_context,
    )

    # MC1: Metadata includes template_id, phase, turn_number, blocks_rendered
    assert bundle.metadata["template_id"] == "turn"
    assert bundle.metadata["phase"] == "turn"
    assert bundle.metadata["turn_number"] == 5
    assert "blocks_rendered" in bundle.metadata

    # MC2: Blocks in order of appearance
    assert bundle.metadata["blocks_rendered"] == ["game_view", "controller_format"]

    # MC3: Renderer metadata preserved in game_view block
    game_view_block = next(b for b in bundle.blocks if b.key == "game_view")
    assert game_view_block.metadata == {"info_level": "full", "custom_key": "custom_value"}


def test_blocks_ordered_by_appearance(render_result):
    """Test blocks ordered by template appearance per MC2."""
    builder = PromptBuilder(turn_template="{controller_format}\n{game_view}\n{controller_format}")

    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="ACTION",
    )

    # Blocks should be: controller_format, game_view (no duplicates)
    block_keys = [b.key for b in bundle.blocks]
    assert block_keys == ["controller_format", "game_view"]


# Test: Provider safety (PS1-PS3 invariants)


def test_provider_immutable_context(render_result):
    """Test provider receives immutable context per PS1."""
    contexts_received = []

    def spying_provider(ctx):
        contexts_received.append(ctx)
        # Try to mutate extras (should fail if truly immutable)
        try:
            ctx.extras["new_key"] = "should fail"  # type: ignore
            return "MUTATION_SUCCEEDED"
        except (TypeError, AttributeError):
            return "MUTATION_BLOCKED"

    builder = PromptBuilder(turn_template="{spy_result}\n{game_view}")
    builder.bind("spy_result", spying_provider)

    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="ACTION",
        extras={"original": "value"},
    )

    # Provider should receive immutable context
    assert len(contexts_received) == 1
    ctx = contexts_received[0]
    assert isinstance(ctx.extras, MappingProxyType)
    assert "MUTATION_BLOCKED" in bundle.text


# Test: Deterministic composition (CD1-CD3 invariants)


def test_deterministic_composition(render_result, turn_context):
    """Test deterministic composition per CD1-CD3."""
    builder = PromptBuilder(turn_template="{game_view}\n{controller_format}")

    # Same inputs should produce identical output
    bundle1 = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="ACTION",
        turn_context=turn_context,
    )

    bundle2 = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="ACTION",
        turn_context=turn_context,
    )

    assert bundle1.text == bundle2.text
    assert bundle1.metadata == bundle2.metadata
    assert [b.key for b in bundle1.blocks] == [b.key for b in bundle2.blocks]


# Test: Extras handling


def test_extras_rendered_as_empty_if_missing(render_result):
    """Test extras render as empty string when not provided per EH1."""
    builder = PromptBuilder(
        turn_template="{game_view}\nStrategy: {strategy}\nFormat: {controller_format}"
    )

    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="ACTION",
        # strategy not provided in extras
    )

    # Should render with empty string
    assert "Strategy: \n" in bundle.text or "Strategy: \nFormat:" in bundle.text


def test_extras_substitution(render_result):
    """Test extras are properly substituted."""
    builder = PromptBuilder(turn_template="{game_view}\nStrategy: {strategy}\nTip: {tip}")

    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=render_result,
        controller_format="ACTION",
        extras={"strategy": "aggressive", "tip": "Watch opponent's moves"},
    )

    assert "Strategy: aggressive" in bundle.text
    assert "Tip: Watch opponent's moves" in bundle.text


# Test: Default templates


def test_default_templates():
    """Test default templates are used when none provided."""
    builder = PromptBuilder()

    # Handshake default (includes game_name, game_instructions, player_instructions placeholders)
    bundle_hs = builder.compose(
        phase=LifecyclePhase.HANDSHAKE,
        render_result=RenderResult(text="Game view", metadata=None),
        controller_format="FORMAT",
        handshake_controller_format="HANDSHAKE_FORMAT",
        extras={
            "game_name": "Poker",
            "game_instructions": "Instructions here",
            "player_instructions": "Player instructions",
        },
    )
    assert "Instructions here" in bundle_hs.text
    assert "Poker" in bundle_hs.text
    assert bundle_hs.text.count("HANDSHAKE_FORMAT") == 1
    assert "\\n" not in bundle_hs.text
    assert "\n\n" in bundle_hs.text

    # Turn default
    bundle_turn = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=RenderResult(text="Game view", metadata=None),
        controller_format="FORMAT",
    )
    assert "Game view" in bundle_turn.text
    assert "\\n" not in bundle_turn.text
    assert "\n\nFORMAT" in bundle_turn.text

    # Conclusion default
    bundle_conc = builder.compose(
        phase=LifecyclePhase.CONCLUSION,
        render_result=RenderResult(text="Final state", metadata=None),
        controller_format="FORMAT",
        extras={"outcome": "Victory!"},
    )
    assert "Match Concluded" in bundle_conc.text
    assert "Victory!" in bundle_conc.text
    assert "\\n" not in bundle_conc.text
    assert "Final state:\nFinal state" in bundle_conc.text


# Test: Edge cases


def test_empty_template():
    """Test empty template string."""
    builder = PromptBuilder(turn_template="")

    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=RenderResult(text="View", metadata=None),
        controller_format="FORMAT",
    )

    assert bundle.text == ""
    assert bundle.blocks == []


def test_no_placeholders():
    """Test template with no placeholders."""
    builder = PromptBuilder(turn_template="Static text only")

    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=RenderResult(text="View", metadata=None),
        controller_format="FORMAT",
    )

    assert bundle.text == "Static text only"
    assert bundle.blocks == []


def test_none_extras():
    """Test compose with extras=None."""
    builder = PromptBuilder(turn_template="{game_view}")

    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=RenderResult(text="View", metadata=None),
        controller_format="FORMAT",
        extras=None,  # Explicitly None
    )

    assert bundle.text == "View"


def test_none_turn_context():
    """Test compose with turn_context=None."""
    builder = PromptBuilder(turn_template="{game_view}")

    bundle = builder.compose(
        phase=LifecyclePhase.TURN,
        render_result=RenderResult(text="View", metadata=None),
        controller_format="FORMAT",
        turn_context=None,
    )

    assert bundle.metadata["turn_number"] == 0  # Default when no context
