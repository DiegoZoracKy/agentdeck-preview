"""Strict action-only controller for AgentDeck."""

from __future__ import annotations

import re
from typing import Optional, Set

from ..core.base.controller import Controller
from ..core.base.game import Game
from ..core.types import ParseResult

# Regex patterns for action extraction
# Anchor ACTION to line start to avoid matching narration blocks like "Last Action:".
ACTION_FIELD = re.compile(r"(?im)^\s*ACTION:\s*(?P<action>[A-Za-z0-9_\-]+)\b")


class ActionOnlyController(Controller):
    """
    Simple action extraction controller with game binding and validation.

    Parses responses only in the explicit ``ACTION: <value>`` format.
    Validates against game.allowed_actions when bound (per GB1-GB6).

    Example usage:
        >>> game = FixedDamageGame()
        >>> controller = ActionOnlyController()
        >>> controller.bind_game(game)  # Extracts allowed_actions
        >>> parse_result = controller.parse("ACTION: ATTACK")
        >>> parse_result.success
        True
        >>> parse_result.action
        'ATTACK'
        >>> parse_result.metadata['validated']
        True
        >>> action_result = parse_result.to_action_result()

    Parsing returns ParseResult:
        - success=True, action=<normalized>: Valid action extracted and validated
        - success=False, action=None, error=<reason>: Parsing or validation failed
        - Failed parses remain failures; callers must not infer an action

    Implements:
        - DS1-DS2: Determinism & stateless parsing
        - GB1-GB6: Game binding for validation
        - AP1-AP3: Action parsing with success/failure indicators
        - VF1: Casefold validation semantics
    """

    def __init__(self):
        """
        Initialize ActionOnlyController.

        Parse failures are surfaced through ``ActionParseError``.
        """
        self._allowed_actions: Optional[Set[str]] = None  # Set during bind_game()

    def bind_game(self, game: Game) -> None:
        """
        Bind to game and extract allowed_actions for validation (per GB1-GB6).

        Args:
            game: Game instance providing allowed_actions

        Note: Idempotent - safe to call multiple times with same game (GB2).
        """
        # GB3: Extract game.allowed_actions for validation
        self._allowed_actions = {action.upper() for action in game.allowed_actions}

    def get_format_instructions(self) -> str:
        """
        Return format instructions for turn prompt (per FI1-FI2, GB4-GB5).

        Returns:
            Dynamic instructions based on binding state

        Behavior:
            - Before binding (GB4): Generic instructions
            - After binding (GB5): Game-specific instructions with allowed actions
        """
        if self._allowed_actions:
            # GB5: Return game-specific instructions when bound
            actions = ", ".join(sorted(self._allowed_actions))
            return f"Respond with: ACTION: <action>\nAllowed actions: {actions}"
        else:
            # GB4: Return sensible defaults when unbound
            return "Respond with: ACTION: <your_action>"

    def parse(self, response: str) -> ParseResult:
        """
        Parse turn action response (per SPEC-CONTROLLER v1.1.0 §4).

        Args:
            response: Raw LLM response string

        Returns:
            ParseResult with success indicator, action, and metadata

        Parsing strategy:
            1. Require a line-anchored "ACTION: <value>" field
            2. Validate against allowed_actions if bound
            3. Return success=True/False without inferring intent from narration

        Requirements (DS1-DS2, AP1-AP3, VF1):
            - DS1: Deterministic and side-effect free for given input
            - DS2: Stateless - no dependency on game_state or turn_context
            - AP1: Populate raw_response with trimmed input
            - AP2: On success, set success=True, action=normalized
            - AP3: On failure, set success=False, action=None, error with reason
            - VF1: Use casefold semantics, include allowed set in metadata
        """
        # AP1: Trim and preserve raw response
        cleaned = response.strip()

        primary_action = self._extract_action(cleaned)

        # Validate against allowed actions if bound
        if self._allowed_actions:
            # GB6: Validation requires binding (already bound, so proceed)
            valid, validated_action = self._validate_action(primary_action)
            if valid and validated_action:
                # AP2: Success case
                return ParseResult(
                    success=True,
                    action=validated_action,
                    raw_response=cleaned,
                    reasoning=None,
                    error=None,
                    metadata={
                        "validated": True,
                        "allowed_actions": list(self._allowed_actions),
                        "resolution_method": "explicit_action_field",
                        "declared_action": validated_action,
                        "contract_satisfied": True,
                    },
                )
            else:
                # AP3: Failure case - validation failed
                error_msg = (
                    f"Parsed action '{primary_action}' not in allowed set {sorted(self._allowed_actions)}"
                    if primary_action
                    else "No ACTION: field found"
                )
                return ParseResult(
                    success=False,
                    action=None,
                    raw_response=cleaned,
                    reasoning=None,
                    error=error_msg,
                    metadata={
                        "allowed_actions": list(self._allowed_actions),
                        "resolution_method": "unresolved",
                        "declared_action": primary_action,
                        "contract_satisfied": False,
                    },
                )
        else:
            # No validation (unbound) - accept any parsed action
            if primary_action:
                # AP2: Success case
                return ParseResult(
                    success=True,
                    action=primary_action,
                    raw_response=cleaned,
                    reasoning=None,
                    error=None,
                    metadata={
                        "validated": False,
                        "resolution_method": "explicit_action_field",
                        "declared_action": primary_action,
                        "contract_satisfied": True,
                    },
                )
            else:
                # AP3: Failure case - no action found
                return ParseResult(
                    success=False,
                    action=None,
                    raw_response=cleaned,
                    reasoning=None,
                    error="No ACTION: field found",
                    metadata={
                        "resolution_method": "unresolved",
                        "declared_action": None,
                        "contract_satisfied": False,
                    },
                )

    def _extract_action(self, response: str) -> Optional[str]:
        """Extract only an explicit, line-anchored action declaration."""
        match = ACTION_FIELD.search(response)
        if match:
            return match.group("action").strip().upper()
        return None

    def _validate_action(self, action: Optional[str]) -> tuple[bool, Optional[str]]:
        """
        Check whether parsed action belongs to allowed set (per VF1).

        Args:
            action: Candidate action to validate

        Returns:
            (is_valid, normalized_action)

        Note: Uses casefold semantics (VF1) - compares uppercase versions.
        """
        if action is None:
            return False, None

        if self._allowed_actions is None:
            # Not bound - accept anything
            return True, action

        # VF1: Casefold semantics - compare uppercase
        candidate = action.upper()
        is_valid = candidate in self._allowed_actions

        return is_valid, candidate if is_valid else None
