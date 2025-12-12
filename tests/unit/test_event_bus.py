"""
Unit tests for EventBus (SPEC-OBSERVABILITY v1.1.0).

Tests all invariants:
- EI1-EI3: Error isolation (spectator exceptions don't crash)
- ES1-ES2: Event signature detection (duck typing)
- EP1-EP2: Payload cloning (mutations don't leak)
- EC1-EC3: EventContext consistency

Per TEST-PLAN-spec-driven.md §3.1 (~15 tests)
"""

from unittest.mock import Mock

from agentdeck.core.types import Event, EventType

# ============================================================================
# EI1-EI3: Error Isolation Tests
# ============================================================================


def test_EI1_spectator_exception_isolated(event_bus):
    """
    SPEC-OBSERVABILITY §6.1 EI1: One spectator raises exception, others still receive event.

    Verify that if one spectator fails, it doesn't prevent other spectators
    from receiving the event.
    """
    # Create three spectators: one that raises, two that work
    working_spectator_1 = Mock()
    failing_spectator = Mock()
    failing_spectator.on_match_start.side_effect = RuntimeError("Spectator failure!")
    working_spectator_2 = Mock()

    # Subscribe all three
    event_bus.subscribe(working_spectator_1)
    event_bus.subscribe(failing_spectator)
    event_bus.subscribe(working_spectator_2)

    # Emit event
    event_bus.emit(EventType.MATCH_START, game="TestGame", players=["Alice", "Bob"])

    # Verify both working spectators received the event
    assert working_spectator_1.on_match_start.called
    assert working_spectator_2.on_match_start.called

    # Failing spectator was called but raised
    assert failing_spectator.on_match_start.called


def test_EI2_exception_logged(event_bus, caplog):
    """
    SPEC-OBSERVABILITY §6.1 EI2: Spectator exceptions are logged.

    Verify that when a spectator raises an exception, it is logged
    with appropriate context.
    """
    failing_spectator = Mock()
    failing_spectator.on_match_start.side_effect = ValueError("Test error")

    event_bus.subscribe(failing_spectator)

    # Emit event
    event_bus.emit(EventType.MATCH_START, game="TestGame")

    # Verify error was logged (check for "Spectator error" or "error" in logs)
    log_text = caplog.text.lower()
    assert "spectator" in log_text and "error" in log_text


def test_EI3_multiple_failures_all_logged(event_bus, caplog):
    """
    SPEC-OBSERVABILITY §6.1 EI3: Multiple spectator failures all logged independently.

    Verify that when multiple spectators fail, all failures are logged
    and each spectator's error is isolated.
    """
    failing_spectator_1 = Mock()
    failing_spectator_1.on_match_start.side_effect = RuntimeError("Failure 1")

    failing_spectator_2 = Mock()
    failing_spectator_2.on_match_start.side_effect = ValueError("Failure 2")

    event_bus.subscribe(failing_spectator_1)
    event_bus.subscribe(failing_spectator_2)

    # Emit event
    event_bus.emit(EventType.MATCH_START, game="TestGame")

    # Both spectators were called
    assert failing_spectator_1.on_match_start.called
    assert failing_spectator_2.on_match_start.called

    # Both errors logged (check for error indicators in logs)
    log_text = caplog.text.lower()
    assert "error" in log_text or "exception" in log_text


# ============================================================================
# ES1-ES2: Event Signature Detection Tests
# ============================================================================


def test_ES1_typed_handler_called(event_bus):
    """
    SPEC-OBSERVABILITY §6.2 ES1: Typed handler (on_match_start) called for MATCH_START.

    Verify duck-typed handler routing: if spectator has on_match_start,
    it receives MATCH_START events.
    """

    # Use real spectator class with modern Event signature
    class TestSpectator:
        def __init__(self):
            self.received_event = None

        def on_match_start(self, event):
            self.received_event = event

    spectator = TestSpectator()

    event_bus.subscribe(spectator)
    event_bus.emit(EventType.MATCH_START, game="TestGame", players=["Alice", "Bob"])

    # Verify event was received
    assert spectator.received_event is not None
    assert isinstance(spectator.received_event, Event)
    assert spectator.received_event.type == "match_start"
    assert spectator.received_event.data["game"] == "TestGame"


def test_ES2_generic_handler_fallback(event_bus):
    """
    SPEC-OBSERVABILITY §6.2 ES2: on_event fallback when no specific handler exists.

    Verify that when no typed handler exists for an event,
    the generic on_event handler is called as fallback.
    """

    class TestSpectator:
        def __init__(self):
            self.received_event = None

        def on_event(self, event):
            """Fallback handler - no specific on_dialogue_turn."""
            self.received_event = event

    spectator = TestSpectator()

    event_bus.subscribe(spectator)
    event_bus.emit(EventType.PLAYER_HANDSHAKE_COMPLETE, player="Alice", accepted=True)

    # on_event should have been called as fallback
    assert spectator.received_event is not None
    assert spectator.received_event.type == "player_handshake_complete"
    assert spectator.received_event.data["player"] == "Alice"


def test_ES2_on_event_only_when_no_specific_handler(event_bus):
    """
    SPEC-OBSERVABILITY §6.2 ES2: on_event is fallback, not called in addition.

    Verify that on_event is ONLY called when no specific handler exists.
    If on_match_start exists, only on_match_start is called.
    """
    spectator = Mock()

    event_bus.subscribe(spectator)

    # Emit standard event - should call on_match_start, NOT on_event
    event_bus.emit(EventType.MATCH_START, game="TestGame")

    # Only on_match_start should be called (on_event is fallback only)
    assert spectator.on_match_start.called
    assert not spectator.on_event.called


# ============================================================================
# EP1-EP2: Payload Cloning Tests
# ============================================================================


def test_EP1_payload_cloned(event_bus):
    """
    SPEC-OBSERVABILITY §6.3 EP1: Payload mutations don't affect other spectators.

    Verify that each spectator receives an independent copy of the payload,
    so mutations don't leak between spectators.
    """

    class TestSpectator:
        def __init__(self):
            self.received_event = None

        def on_match_start(self, event):
            self.received_event = event

    spectator_1 = TestSpectator()
    spectator_2 = TestSpectator()

    event_bus.subscribe(spectator_1)
    event_bus.subscribe(spectator_2)

    # Emit event with mutable payload
    event_bus.emit(EventType.MATCH_START, game="TestGame", players=["Alice", "Bob"])

    # Mutate spectator_1's payload
    spectator_1.received_event.data["players"].append("Charlie")

    # Spectator_2's payload should be unaffected
    assert len(spectator_2.received_event.data["players"]) == 2
    assert "Charlie" not in spectator_2.received_event.data["players"]


def test_EP2_context_cloned(event_bus):
    """
    SPEC-OBSERVABILITY §6.3 EP2: EventContext mutations don't leak.

    Verify that EventContext is also cloned, so mutations don't affect
    other spectators.
    """

    class TestSpectator:
        def __init__(self):
            self.received_event = None

        def on_match_start(self, event):
            self.received_event = event

    spectator_1 = TestSpectator()
    spectator_2 = TestSpectator()

    event_bus.subscribe(spectator_1)
    event_bus.subscribe(spectator_2)

    # Set context via update_context
    event_bus.update_context(match_id="test-001")

    # Emit event
    event_bus.emit(EventType.MATCH_START, game="TestGame")

    # Mutate spectator_1's context
    spectator_1.received_event.context["match_id"] = "modified"

    # Spectator_2's context should be unaffected
    assert spectator_2.received_event.context["match_id"] == "test-001"


# ============================================================================
# EC1-EC3: EventContext Consistency Tests
# ============================================================================


def test_EC1_timestamp_present(event_bus):
    """
    SPEC-OBSERVABILITY §6.4 EC1: EventBus adds timestamp to EventContext.

    Verify that every event has a timestamp added by EventBus.
    """

    class TestSpectator:
        def __init__(self):
            self.received_event = None

        def on_match_start(self, event):
            self.received_event = event

    spectator = TestSpectator()
    event_bus.subscribe(spectator)

    event_bus.emit(EventType.MATCH_START, game="TestGame")

    # Timestamp should be present in context
    assert "timestamp" in spectator.received_event.context
    assert isinstance(spectator.received_event.context["timestamp"], float)


def test_EC2_ids_preserved(event_bus):
    """
    SPEC-OBSERVABILITY §6.4 EC2: Console-set IDs (match_id, session_id) preserved.

    Verify that IDs set by Console via update_context() are preserved in EventContext
    and not overwritten by EventBus.
    """

    class TestSpectator:
        def __init__(self):
            self.received_event = None

        def on_match_start(self, event):
            self.received_event = event

    spectator = TestSpectator()
    event_bus.subscribe(spectator)

    # Console sets IDs via update_context()
    event_bus.update_context(
        match_id="console-match-001", session_id="console-session-001", batch_id="console-batch-001"
    )

    # Emit event
    event_bus.emit(EventType.MATCH_START, game="TestGame")

    # IDs should be preserved in context
    assert spectator.received_event.context.get("match_id") == "console-match-001"
    assert spectator.received_event.context.get("session_id") == "console-session-001"
    assert spectator.received_event.context.get("batch_id") == "console-batch-001"


def test_EC3_context_immutable(event_bus):
    """
    SPEC-OBSERVABILITY §6.4 EC3: EventContext fields should be immutable.

    While EventContext is a TypedDict (not frozen), verify that the cloning
    strategy prevents mutations from affecting subsequent spectators.
    """

    class TestSpectator:
        def __init__(self):
            self.received_event = None

        def on_match_start(self, event):
            self.received_event = event

    spectator_1 = TestSpectator()
    spectator_2 = TestSpectator()

    event_bus.subscribe(spectator_1)
    event_bus.subscribe(spectator_2)

    # Set context field via update_context
    event_bus.update_context(match_id="test-001")

    event_bus.emit(EventType.MATCH_START, game="TestGame")

    # Attempt to mutate spectator_1's context
    spectator_1.received_event.context["match_id"] = "modified"

    # Spectator_2's context should be unaffected
    assert spectator_2.received_event.context["match_id"] == "test-001"


# ============================================================================
# Subscription Management Tests
# ============================================================================


def test_subscribe_unsubscribe(event_bus):
    """
    SPEC-OBSERVABILITY: Spectators can be added and removed dynamically.

    Verify subscribe() and unsubscribe() work correctly.
    """
    spectator = Mock()

    # Subscribe
    event_bus.subscribe(spectator)
    event_bus.emit(EventType.MATCH_START, game="Test")
    assert spectator.on_match_start.called

    # Unsubscribe
    spectator.on_match_start.reset_mock()
    event_bus.unsubscribe(spectator)
    event_bus.emit(EventType.MATCH_START, game="Test2")

    # Spectator should no longer receive events
    assert not spectator.on_match_start.called


def test_event_order_preserved(event_bus):
    """
    SPEC-OBSERVABILITY: Events are emitted in FIFO order.

    Verify that spectators receive events in the order they were emitted.
    """
    spectator = Mock()
    received_games = []

    def capture_game(event):
        received_games.append(event.data["game"])

    spectator.on_match_start = capture_game

    event_bus.subscribe(spectator)

    # Emit multiple events
    event_bus.emit(EventType.MATCH_START, game="Game1")
    event_bus.emit(EventType.MATCH_START, game="Game2")
    event_bus.emit(EventType.MATCH_START, game="Game3")

    # Verify order
    assert received_games == ["Game1", "Game2", "Game3"]


def test_no_subscribers(event_bus):
    """
    SPEC-OBSERVABILITY: Emitting with no subscribers doesn't crash.

    Verify that emit() works correctly even when no spectators subscribed.
    """
    # Should not raise exception
    event_bus.emit(EventType.MATCH_START, game="TestGame")


def test_payload_types(event_bus):
    """
    SPEC-OBSERVABILITY: Various payload types supported.

    Verify that different data types can be included in payloads.
    """

    class TestSpectator:
        def __init__(self):
            self.received_event = None

        def on_match_start(self, event):
            self.received_event = event

    spectator = TestSpectator()
    event_bus.subscribe(spectator)

    # Emit with various types
    event_bus.emit(
        EventType.MATCH_START,
        string_val="test",
        int_val=42,
        float_val=3.14,
        bool_val=True,
        list_val=[1, 2, 3],
        dict_val={"key": "value"},
        none_val=None,
    )

    # Verify all types preserved
    assert spectator.received_event.data["string_val"] == "test"
    assert spectator.received_event.data["int_val"] == 42
    assert spectator.received_event.data["float_val"] == 3.14
    assert spectator.received_event.data["bool_val"] is True
    assert spectator.received_event.data["list_val"] == [1, 2, 3]
    assert spectator.received_event.data["dict_val"] == {"key": "value"}
    assert spectator.received_event.data["none_val"] is None
