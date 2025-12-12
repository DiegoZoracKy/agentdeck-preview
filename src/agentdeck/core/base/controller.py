"""
Controller base class for AgentDeck framework.

Implements unified controller architecture per:
- SPEC-CONTROLLER v1.3.0 §4 (Public API - Single Controller)
- SPEC-CONTROLLER v1.3.0 §5 (Invariants & Guarantees)

Key responsibilities:
- Controller handles ALL player-game interaction phases:
  - Handshake validation (default implementation, overridable)
  - Turn action parsing (abstract, must implement)
  - Conclusion parsing (default passthrough, overridable)
- Provide format instructions for all phases
- Capture metadata for recorder (PM1-PM6 support)
- Support game binding for action validation (GB1-GB6)

Critical invariants:
- HV1-HV5: Handshake validation (determinism, normalization, default behavior)
- AP1-AP3: Action parsing (success/failure, metadata capture)
- GB1-GB6: Game binding (idempotent, fail-fast, dynamic instructions)
- MI1-MI2: Metadata integrity (JSON-serializable, debug aids)
- DS1-DS2: Determinism & safety (no side effects, repeatable)

Architecture note (v1.3.0):
- Handshake is lifecycle method with default implementation (accepts OK/READY/YES)
- Subclasses override validate_handshake() for custom validation
- Parallel pattern with Renderer (multiple methods, one object)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional

from ..types import HandshakeContext, HandshakeResult, ParseResult, TurnContext

if TYPE_CHECKING:
    from .game import Game


class Controller(ABC):
    """
    Unified controller handling all player-game interaction phases (per SPEC-CONTROLLER v1.3.0 §4).

    Controllers handle three lifecycle phases:
    1. **Handshake validation** - Default implementation (accepts OK/READY/YES), overridable
    2. **Turn action parsing** - Abstract method (must implement)
    3. **Conclusion parsing** - Default passthrough, overridable

    Lifecycle:
        **Handshake Phase**:
        1. Console calls controller.get_handshake_format_instructions()
        2. PromptBuilder injects instructions via {controller_format}
        3. Player invokes LLM → raw acknowledgement string
        4. Console calls controller.validate_handshake(raw, context) → HandshakeResult
        5. Console enforces policy: accepted=True → proceed, accepted=False → abort

        **Turn Phase**:
        1. Console calls controller.bind_game(game) before handshake (GB1)
        2. PromptBuilder injects controller.get_format_instructions() via {controller_format}
        3. Player invokes LLM during turn → raw response string
        4. Player calls controller.parse(raw) → ParseResult
        5. Player converts ParseResult → ActionResult via to_action_result()
        6. Console applies action via game.update()

    Example minimal controller:
        >>> class ActionOnlyController(Controller):
        ...     def __init__(self):
        ...         self._allowed_actions = None
        ...
        ...     # Inherits default validate_handshake() - accepts OK/READY/YES
        ...
        ...     def bind_game(self, game):
        ...         self._allowed_actions = {a.upper() for a in game.allowed_actions}
        ...
        ...     def get_format_instructions(self) -> str:
        ...         if self._allowed_actions:
        ...             actions = ', '.join(sorted(self._allowed_actions))
        ...             return f"Respond with: ACTION: <action>\\nAllowed: {actions}"
        ...         return "Respond with: ACTION: <action>"
        ...
        ...     def parse(self, response: str) -> ParseResult:
        ...         # Extract "ACTION: <value>" from response
        ...         # Validate against self._allowed_actions if bound
        ...         # Return ParseResult(success, action, raw_response, error?, metadata)
        ...         pass

    Example custom handshake:
        >>> class StrictReasoningController(ReasoningController):
        ...     def validate_handshake(self, response, *, context=None):
        ...         \"\"\"Override: Require explicit confirmation phrase.\"\"\"
        ...         if "I understand and am ready" not in response:
        ...             return HandshakeResult(
        ...                 accepted=False,
        ...                 reason="Must say 'I understand and am ready'",
        ...                 raw_response=response
        ...             )
        ...         return HandshakeResult(accepted=True, raw_response=response)
        ...
        ...     # Inherits all turn-phase logic from ReasoningController

    See also:
        - ActionOnlyController: Default implementation (ACTION: format)
        - ReasoningController: Extended implementation (REASONING: + ACTION: format)
        - SPEC-CONTROLLER.md §8: Complete examples
    """

    # -------------------------------------------------------------------------
    # Handshake Phase (Default Implementation - Rarely Overridden)
    # -------------------------------------------------------------------------

    def validate_handshake(
        self, response: str, *, context: Optional[HandshakeContext] = None
    ) -> HandshakeResult:
        """
        Validate handshake acknowledgement (per HV1-HV5).

        Default implementation accepts {"OK", "READY", "YES"} (case-insensitive,
        punctuation-tolerant). Override for custom validation logic.

        Args:
            response: Raw LLM response from handshake phase
            context: Optional context (player_name, game_name, etc.)

        Returns:
            HandshakeResult with acceptance status, normalized response, reason

        Requirements (HV1-HV5):
            - HV1: MUST be deterministic and side-effect free
            - HV2: MUST normalize whitespace/punctuation, preserve raw response
            - HV3: Rejection MUST set accepted=False and populate reason
            - HV4: Default implementation accepts {"OK", "READY", "YES"}
            - HV5: Subclasses MAY override but MUST maintain HV1-HV3

        Example (default behavior):
            >>> result = controller.validate_handshake(" ok!!! ")
            >>> result.accepted
            True
            >>> result.normalized_response
            'OK'

        Example (custom override):
            >>> class StrictController(ActionOnlyController):
            ...     def validate_handshake(self, response, *, context=None):
            ...         if "I confirm" not in response:
            ...             return HandshakeResult(accepted=False, reason="Need confirmation")
            ...         return HandshakeResult(accepted=True, raw_response=response)
        """
        raw = response.strip()
        normalized = raw.upper().rstrip("!.")

        allowed = {"OK", "READY", "YES"}
        accepted = normalized in allowed

        reason = None if accepted else f"Expected one of {sorted(allowed)}, got '{raw}'"

        metadata: Dict[str, Any] = {"allowed": sorted(allowed)}
        if context:
            metadata["player"] = context.player_name

        return HandshakeResult(
            accepted=accepted,
            normalized_response=normalized if accepted else None,
            raw_response=raw,
            reason=reason,
            metadata=metadata,
        )

    def get_handshake_format_instructions(self) -> str:
        """
        Return format instructions for handshake phase (per FI1-FI2).

        Default: Simple "Reply with OK" instruction.
        Override to match custom validate_handshake() logic.

        Returns:
            Deterministic instruction text for handshake prompt

        Requirements (FI1, FI2):
            - FI1: MUST align with validate_handshake() expectations
            - FI2: MUST be deterministic (no randomness or state dependency)

        Example (default):
            >>> controller.get_handshake_format_instructions()
            "Reply with 'OK' if you understand and are ready to begin."

        Example (custom override):
            >>> class StrictController(ActionOnlyController):
            ...     def get_handshake_format_instructions(self):
            ...         return "Reply with 'I confirm' to acknowledge."

        Usage: PromptBuilder inserts this into handshake templates via
               {controller_format} placeholder.
        """
        return "Reply with 'OK' if you understand and are ready to begin."

    # -------------------------------------------------------------------------
    # Turn Phase (Abstract - Must Implement)
    # -------------------------------------------------------------------------

    def bind_game(self, game: Game) -> None:
        """
        Bind controller to game for action validation (per GB1-GB6).

        Called by Console before handshake phase. Controllers SHOULD extract
        game.allowed_actions and use it for validation in parse() and
        get_format_instructions().

        Args:
            game: Game instance providing allowed_actions and other config

        Requirements (GB1-GB6):
            - GB1: Console MUST call this before match starts
            - GB2: MUST be idempotent (safe to call multiple times with same game)
            - GB3: SHOULD extract game.allowed_actions for validation
            - GB4: MUST NOT require binding before get_format_instructions() (sensible defaults)
            - GB5: SHOULD return game-specific instructions when bound
            - GB6: MUST raise RuntimeError in parse() if unbound and validation required

        Default: No-op (controllers that don't validate can skip this)

        Example:
            >>> def bind_game(self, game: Game) -> None:
            ...     self._allowed_actions = {action.upper() for action in game.allowed_actions}

        Note: Binding happens once per match. Controllers maintain binding state
              for duration of match.
        """
        pass  # Default no-op for controllers that don't validate

    @abstractmethod
    def get_format_instructions(self) -> str:
        """
        Return action format instructions for prompt composition (per FI1-FI2, GB4-GB5).

        Returns:
            Deterministic instruction text for {controller_format} placeholder

        Requirements (FI1, FI2, GB4, GB5):
            - FI1: MUST align with parse() expectations (mention required format)
            - FI2: MUST be deterministic (no randomness or state dependency)
            - GB4: MUST work before bind_game() (return sensible defaults)
            - GB5: SHOULD return game-specific instructions when bound

        Example (before binding):
            >>> def get_format_instructions(self) -> str:
            ...     return "Respond with: ACTION: <your_action>"

        Example (after binding):
            >>> def get_format_instructions(self) -> str:
            ...     if self._allowed_actions:
            ...         actions = ', '.join(sorted(self._allowed_actions))
            ...         return f"Respond with: ACTION: <action>\\nAllowed: {actions}"
            ...     return "Respond with: ACTION: <your_action>"

        Usage: PromptBuilder inserts this into turn templates via {controller_format}
               placeholder.
        """

    @abstractmethod
    def parse(self, response: str) -> ParseResult:
        """
        Parse turn action response (per SPEC-CONTROLLER v1.1.0 §4).

        Args:
            response: Raw LLM response string

        Returns:
            ParseResult with success indicator, action, and metadata

        Requirements (DS1-DS2, AP1-AP3, VF1, GB6):
            - DS1: MUST be deterministic and side-effect free for given input
            - DS2: MUST NOT depend on game_state or turn_context (stateless parsing)
            - AP1: MUST populate ParseResult.raw_response with trimmed input
            - AP2: On success, set success=True, action=normalized, reasoning if extracted
            - AP3: On failure, set success=False, action=None, error with reason
            - VF1: MUST use casefold semantics, include allowed set in metadata
            - GB6: MUST raise RuntimeError if unbound and validation required

        Example (success):
            >>> parse_result = controller.parse("ACTION: ATTACK")
            >>> parse_result.success
            True
            >>> parse_result.action
            'ATTACK'
            >>> parse_result.metadata
            {'allowed_actions': ['ATTACK', 'DEFEND'], 'validated': True}

        Example (failure):
            >>> parse_result = controller.parse("I attack!")
            >>> parse_result.success
            False
            >>> parse_result.action
            None
            >>> parse_result.error
            'No ACTION: field found'

        Caller conversion pattern:
            >>> parse_result = controller.parse(raw_response)
            >>> action_result = parse_result.to_action_result(fallback="UNKNOWN")

        Note: This method is called by Player.decide() during turn phase. Console
              never calls this directly - it only binds the game before handshake.
              The caller is responsible for converting ParseResult to ActionResult
              via to_action_result(fallback) to apply fallback semantics.
        """

    # -------------------------------------------------------------------------
    # Conclusion Phase (Default Passthrough - Rarely Overridden)
    # -------------------------------------------------------------------------

    def parse_conclusion(self, response: str, *, context: Optional[TurnContext] = None) -> str:
        """
        Parse conclusion-phase response (per SPEC-CONTROLLER v1.3.0 §4).

        Default implementation returns response as-is (trimmed). Override for
        custom conclusion parsing (e.g., extracting reflections, emotions).

        Args:
            response: Raw LLM response from conclusion phase
            context: Optional context (game state, turn history, etc.)

        Returns:
            Parsed conclusion string

        Requirements (CP1-CP2):
            - CP1: MUST be deterministic and side-effect free
            - CP2: Default returns trimmed response (passthrough)

        Example (default behavior):
            >>> result = controller.parse_conclusion("  Good game!  ")
            >>> result
            'Good game!'

        Example (custom override):
            >>> class ReflectiveController(ActionOnlyController):
            ...     def parse_conclusion(self, response, *, context=None):
            ...         # Extract reflection from "REFLECTION: ..." format
            ...         if "REFLECTION:" in response:
            ...             return response.split("REFLECTION:")[1].strip()
            ...         return response.strip()

        Usage: Console calls this during conclusion phase to parse final message.
        """
        return response.strip()
