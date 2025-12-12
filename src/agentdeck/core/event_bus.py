"""
EventBus implementation for AgentDeck v1.0.0 framework.

Implements the event distribution mechanism per:
- SPEC-OBSERVABILITY v1.0.0 §3-4
- SPEC-SPECTATOR v1.0.0 §5.1-5.3
- SPEC.md §5.4

Key features:
- Duck-typed handler routing (on_<event_name>(event) or on_<event_name>(**kwargs))
- Deep copy payload cloning (prevents spectator mutations from leaking)
- Error isolation (spectator exceptions logged, execution continues)
- Snapshot iteration (safe subscription changes during emit)
- EventContext envelope construction (session/batch/match/phase metadata)
"""

from __future__ import annotations

import copy
import inspect
import logging
import time
from typing import Any, Dict, List, Optional, Union

from .types import Event, EventContext, EventType

# Module-level logger per SPEC (IMPLEMENTATION_KICKOFF.md Design Decision #4)
logger = logging.getLogger("agentdeck.event_bus")


class EventBus:
    """
    Event distribution system for spectator observation.

    Per SPEC-OBSERVABILITY v1.0.0, EventBus routes events to spectators using
    duck-typed handler methods. Spectators implement on_<event_name> methods
    to receive events they care about.

    Critical invariants:
    - EI1: Spectator exceptions MUST be caught and logged (never propagate)
    - Payload cloning: Each spectator receives deep-copied event data
    - Snapshot iteration: Spectators can unsubscribe during event emission

    Handler signatures supported:
    1. Modern: on_<event_name>(event: Event)
    2. Legacy: on_<event_name>(**kwargs)
    3. Fallback: on_event(event: Event) for custom domain events

    Example usage:
        >>> bus = EventBus()
        >>> bus.subscribe(my_spectator)
        >>> bus.emit(EventType.MATCH_START, match_id="m1", players=["Alice", "Bob"])
        >>> bus.emit("bid_placed", player="Alice", bid=100)  # Custom event

    Attributes:
        _spectators: List of subscribed spectators (order preserved)
        _base_context: Base EventContext fields (session_id, batch_id, match_id)
    """

    def __init__(self, session_id: Optional[str] = None, logger: Optional[Any] = None):
        """
        Initialize EventBus with optional session context.

        Args:
            session_id: Optional session identifier for EventContext envelope
            logger: Optional logger for exception handling (defaults to module logger)

        Note: Console will set additional context fields (batch_id, match_id)
              via update_context() as execution progresses.
        """
        self._spectators: List[Any] = []
        self._base_context: Dict[str, Any] = {}
        self._logger = logger  # If provided, use for exception logging instead of module logger

        if session_id is not None:
            self._base_context["session_id"] = session_id

    def subscribe(self, spectator: Any) -> None:
        """
        Register spectator for event delivery.

        Per SPEC-SPECTATOR §5.2 SS1-SS2, spectators implement on_<event_name>
        methods using duck typing. No base class required.

        Args:
            spectator: Any object with on_* methods

        Example:
            >>> class MySpectator:
            ...     def on_match_start(self, event):
            ...         print(f"Match started: {event.data['match_id']}")
            >>> bus.subscribe(MySpectator())
        """
        if spectator not in self._spectators:
            self._spectators.append(spectator)

    def unsubscribe(self, spectator: Any) -> None:
        """
        Remove spectator from delivery.

        Safe to call during event emission (deferred removal via snapshot).

        Args:
            spectator: Previously subscribed spectator
        """
        if spectator in self._spectators:
            self._spectators.remove(spectator)

    def update_context(self, **context_fields: Any) -> None:
        """
        Update base EventContext fields.

        Called by Console to set session/batch/match IDs as execution progresses.

        Args:
            **context_fields: Context fields to update (session_id, batch_id, match_id, etc.)

        Example:
            >>> bus.update_context(batch_id="batch-123")
            >>> bus.update_context(match_id="match-456", phase_index=0)
        """
        self._base_context.update(context_fields)

    def clear_context(self, *fields: str) -> None:
        """
        Clear specific EventContext fields.

        Called by Console when exiting scopes (e.g., clear match_id after MATCH_END).

        Args:
            *fields: Field names to remove from base context

        Example:
            >>> bus.clear_context('match_id', 'phase_index')
        """
        for field in fields:
            self._base_context.pop(field, None)

    def emit(self, event_type: Union[EventType, str], **data: Any) -> None:
        """
        Construct Event object and route to spectator handlers.

        Per SPEC.md §5.4, this method:
        1. Normalizes enum to string (EventType.MATCH_START → "match_start")
        2. Constructs EventContext envelope (adds timestamps to base context)
        3. Creates Event object with cloned data
        4. Routes to spectators using duck typing
        5. Isolates spectator errors (log and continue)

        Args:
            event_type: EventType enum or string (e.g., "bid_placed")
            **data: Event-specific payload (must be JSON-serializable)

        Routing logic:
            - Tries: on_<event_name>(event)  [preferred modern signature]
            - Falls back: on_<event_name>(**kwargs)  [legacy signature]
            - Falls back: on_event(event)  [catch-all for custom events]

        Error handling (EI1 invariant):
            - Catches ALL spectator exceptions
            - Logs exception with spectator name and event type
            - Continues with remaining spectators (never propagates)

        Example:
            >>> bus.emit(EventType.MATCH_START, match_id="m1", players=["A", "B"])
            >>> bus.emit("bid_placed", player="Alice", bid=100)
        """
        # Step 1: Normalize event type to string
        if isinstance(event_type, EventType):
            event_name = event_type.value
        elif isinstance(event_type, str):
            event_name = event_type
        else:
            raise TypeError(
                f"event_type must be EventType enum or str, " f"got {type(event_type).__name__}"
            )

        # Step 2: Construct EventContext envelope
        # Hybrid approach (Design Decision #2):
        # - Base context from Console (session_id, batch_id, match_id, phase_index)
        # - Timestamps added here by EventBus
        context: EventContext = {
            **self._base_context,  # type: ignore
            "timestamp": time.time(),
            "monotonic_time": time.monotonic(),
        }

        # Step 3: Create base Event object (will be cloned for each spectator)
        base_event = Event(
            type=event_name,
            data=data,
            context=context,
            timestamp=context["timestamp"],
            duration=0.1,  # Default duration (may be updated later)
        )

        # Step 4: Route to spectators using snapshot iteration
        # Per Design Decision #5: Use snapshot to allow unsubscribe during emit
        spectators_snapshot = list(self._spectators)

        for spectator in spectators_snapshot:
            try:
                # Clone event for this spectator (prevents mutation leakage)
                cloned_event = self._clone_event(base_event)

                # Try routing in order: on_<event_name> → on_event
                self._route_to_spectator(spectator, event_name, cloned_event, data)

            except Exception as e:
                # EI1 invariant: Catch and log, never propagate
                # Use injected logger if available (for session context), else module logger
                error_logger = self._logger if self._logger else logger

                # Handle different logger APIs:
                # - AgentDeckLogger: uses error(msg, error=exception)
                # - Standard logging: uses error(msg, exc_info=True)
                if (
                    hasattr(error_logger, "__class__")
                    and "AgentDeckLogger" in error_logger.__class__.__name__
                ):
                    error_logger.error(
                        f"Spectator error in {spectator.__class__.__name__}.on_{event_name}",
                        error=e,  # AgentDeckLogger API
                    )
                else:
                    error_logger.error(
                        f"Spectator error in {spectator.__class__.__name__}.on_{event_name}",
                        exc_info=True,  # Standard logging API
                    )

    def _route_to_spectator(
        self, spectator: Any, event_name: str, event: Event, data: Dict[str, Any]
    ) -> None:
        """
        Route event to appropriate spectator handler.

        Tries handlers in order:
        1. on_<event_name>(event) - Modern signature
        2. on_<event_name>(**kwargs) - Legacy signature
        3. on_event(event) - Fallback for custom domain events

        Args:
            spectator: Spectator to route to
            event_name: Normalized event name (e.g., "match_start", "bid_placed")
            event: Cloned Event object
            data: Original data dict (for legacy kwargs signature)
        """
        # Primary handler: on_<event_name>
        handler = getattr(spectator, f"on_{event_name}", None)

        if handler:
            # Determine signature: Event object vs **kwargs
            if self._expects_event_signature(handler):
                # Modern signature: on_match_start(event: Event)
                handler(event)
            else:
                # Legacy signature: on_match_start(**kwargs)
                # Include context in kwargs for backward compatibility
                kwargs = {**data, "context": event.context}
                handler(**kwargs)
            return

        # Fallback for all events (including lifecycle): on_event
        # Per SPEC-SPECTATOR §5.1 HC2, on_event is a catch-all for ANY event
        # when specific handler (on_<event_name>) is not implemented
        fallback = getattr(spectator, "on_event", None)
        if fallback:
            # Check signature for on_event
            if self._expects_event_signature(fallback):
                fallback(event)
            else:
                # Legacy: on_event(event, context=None)
                fallback(event, context=event.context)
            return

        # No handler found - silently skip (duck typing per SPEC-SPECTATOR HC1)

    def _expects_event_signature(self, handler: Any) -> bool:
        """
        Detect whether handler expects Event object vs **kwargs.

        Modern signature: on_match_start(event: Event)
        Legacy signature: on_match_start(**kwargs) or on_match_start(result, context=None, **data)

        Detection logic:
        - Modern: Exactly 1 positional parameter named 'event', no VAR_KEYWORD
        - Legacy: Multiple params OR VAR_KEYWORD (**kwargs) OR param not named 'event'

        Args:
            handler: Callable to inspect

        Returns:
            True if modern Event signature, False if legacy **kwargs
        """
        try:
            sig = inspect.signature(handler)
        except (TypeError, ValueError):
            # Can't inspect (e.g., builtin) - assume legacy
            return False

        params = list(sig.parameters.values())

        # Filter to positional parameters only (ignore self, cls)
        positional = [
            p
            for p in params
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
            and p.default is inspect.Parameter.empty
        ]

        # Has VAR_KEYWORD (**kwargs)? → Legacy signature
        if any(p.kind == p.VAR_KEYWORD for p in params):
            return False

        # Exactly 1 required positional param AND named 'event'? → Modern signature
        if len(positional) == 1 and positional[0].name == "event":
            return True

        # Otherwise → Legacy signature
        return False

    def _clone_event(self, event: Event) -> Event:
        """
        Create deep copy of Event to isolate spectator mutations.

        Per SPEC.md §5.4 and Design Decision #1: Use copy.deepcopy for safety,
        but avoid deepcopying Player/Game/Spectator objects which may contain
        unpicklable elements (e.g., OpenAI client with thread locks).

        Args:
            event: Base Event object to clone

        Returns:
            New Event with deep-copied data dict and independent context dict

        Note: Both event.data AND event.context are cloned to prevent mutations
              from leaking between spectators (per SPEC.md §5.4 payload cloning).
        """
        # Import here to avoid circular dependency
        from .base.game import Game
        from .base.player import Player
        from .base.spectator import Spectator

        # Selectively deepcopy data, excluding unpicklable objects
        cloned_data = {}
        for key, value in event.data.items():
            # Don't deepcopy Player, Game, or Spectator objects - they're read-only in events
            if isinstance(value, (Player, Game, Spectator)):
                cloned_data[key] = value
            # Don't deepcopy lists of Player/Game/Spectator objects
            elif (
                isinstance(value, list)
                and value
                and isinstance(value[0], (Player, Game, Spectator))
            ):
                cloned_data[key] = value
            else:
                cloned_data[key] = copy.deepcopy(value)

        return Event(
            type=event.type,
            data=cloned_data,
            context=dict(event.context),  # Clone context dict (prevent mutation leakage)
            timestamp=event.timestamp,
            duration=event.duration,
        )
