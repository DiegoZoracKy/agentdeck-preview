"""Unit tests for observability event helpers."""

from __future__ import annotations

from agentdeck.core.event_bus import EventBus
from agentdeck.core.event_factory import EventFactory
from agentdeck.core.game_event_emitter import GameEventEmitter
from agentdeck.core.types import ActionResult, TurnContext


def _turn_context(turn_index: int = 2) -> TurnContext:
    return TurnContext(
        match_id="match-1",
        turn_number=turn_index + 1,
        turn_index=turn_index,
        player="Alice",
        started_at=100.0,
        duration=0.5,
        rng_seed=123,
        rng_label=f"turn_{turn_index + 1}",
    )


def test_event_factory_turn_matches_canonical_gameplay_shape():
    """SPEC-OBSERVABILITY §8/§9.2: EventFactory.turn mirrors canonical gameplay payloads."""
    factory = EventFactory("match-1")
    state_before = {"health": {"Alice": 50, "Bob": 20}}
    state_after = {"health": {"Alice": 50, "Bob": 0}}
    action = ActionResult(
        action="ATTACK",
        reasoning="Finish the match.",
        raw_response="ACTION: ATTACK",
        metadata={
            "raw_prompt": "Take your turn.",
            "prompt_blocks": [{"role": "system", "content": "Take your turn."}],
            "controller_metadata": {"parser": "action_only"},
            "controller_format": "ACTION: <MOVE>",
            "usage_info": {"input_tokens": 10, "output_tokens": 4},
            "renderer_output": {"template_id": "default"},
        },
    )

    event = factory.turn(
        player="Alice",
        action=action,
        state_before=state_before,
        state_after=state_after,
        turn_context=_turn_context(),
    )

    state_before["health"]["Bob"] = 999
    action.metadata["usage_info"]["input_tokens"] = 999

    assert event.type == "gameplay"
    assert event.context["match_id"] == "match-1"
    assert event.context["phase_index"] == 2
    assert event.context["turn_index"] == 2
    assert event.data["mechanic"] == "turn_based"
    assert event.data["phase_index"] == 2
    assert event.data["turn_index"] == 2
    assert event.data["action"] == {
        "action": "ATTACK",
        "reasoning": "Finish the match.",
        "metadata": {
            "raw_prompt": "Take your turn.",
            "prompt_blocks": [{"role": "system", "content": "Take your turn."}],
            "controller_metadata": {"parser": "action_only"},
            "controller_format": "ACTION: <MOVE>",
            "usage_info": {"input_tokens": 10, "output_tokens": 4},
            "renderer_output": {"template_id": "default"},
        },
        "raw_response": "ACTION: ATTACK",
    }
    assert event.data["prompt_text"] == "Take your turn."
    assert event.data["response_text"] == "ACTION: ATTACK"
    assert event.data["prompt_blocks"] == [{"role": "system", "content": "Take your turn."}]
    assert event.data["controller_metadata"] == {"parser": "action_only"}
    assert event.data["usage_info"] == {"input_tokens": 10, "output_tokens": 4}
    assert event.data["renderer_output"] == {"template_id": "default"}
    assert event.data["state_before"]["health"]["Bob"] == 20


def test_event_factory_custom_injects_context_without_overwriting_explicit_payload():
    """SPEC-OBSERVABILITY §8.1: custom events inherit match/phase context via defaults only."""
    factory = EventFactory("match-1")
    event = factory.custom(
        "card_drawn",
        {"match_id": "override", "card": "Ace"},
        turn_context=_turn_context(turn_index=4),
    )

    assert event.type == "card_drawn"
    assert event.data["match_id"] == "override"
    assert event.data["card"] == "Ace"
    assert event.data["turn_context"]["turn_index"] == 4
    assert event.context == {
        "match_id": "match-1",
        "phase_index": 4,
        "turn_index": 4,
    }


def test_game_event_emitter_injects_match_and_phase_metadata():
    """SPEC-OBSERVABILITY §7.1: GameEventEmitter injects structural metadata into payloads."""

    class CaptureSpectator:
        def __init__(self):
            self.events = []

        def on_card_drawn(self, event):
            self.events.append(event)

    bus = EventBus(session_id="session-1")
    spectator = CaptureSpectator()
    bus.subscribe(spectator)

    emitter = GameEventEmitter(bus, "match-1")
    emitter.set_phase_index(3)
    emitter.emit("card_drawn", card="Ace")
    emitter.clear_phase_index()
    emitter.emit("card_drawn", match_id="override", card="King")

    assert len(spectator.events) == 2
    first, second = spectator.events
    assert first.data == {
        "match_id": "match-1",
        "phase_index": 3,
        "turn_index": 3,
        "card": "Ace",
    }
    assert second.data == {
        "match_id": "override",
        "card": "King",
    }
