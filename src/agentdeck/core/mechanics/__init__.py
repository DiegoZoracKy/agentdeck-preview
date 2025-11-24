"""
Game mechanics module for AgentDeck.

Contains mechanic-specific base classes and helpers that implement different
execution patterns (turn-based, simultaneous, realtime) using the MatchRuntime
infrastructure context.

Modules:
    turn_based: TurnBasedGame base class + TurnLoop helper + TurnResult dataclass

See:
    - SPEC-GAME-MECHANIC-TURN-BASED.md: Turn-based mechanic contract
    - SPEC-MATCH-RUNTIME.md: Infrastructure context contract
"""

from .turn_based import TurnBasedGame, TurnLoop, TurnResult

__all__ = [
    "TurnBasedGame",
    "TurnLoop",
    "TurnResult",
]
