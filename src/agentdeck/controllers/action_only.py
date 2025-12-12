"""
Simple action-only controller for AgentDeck.

Implements ActionOnlyController per SPEC-CONTROLLER v1.1.0 §4.
Parses responses like "ACTION: ATTACK" or detects uppercase tokens.
Returns ParseResult for stateless, deterministic parsing.
"""

from __future__ import annotations

import re
from typing import List, Optional, Set

from ..core.base.controller import Controller
from ..core.base.game import Game
from ..core.types import ParseResult

# Regex patterns for action extraction
ACTION_FIELD = re.compile(r"ACTION:\s*(?P<action>[A-Za-z0-9_\-]+)", re.IGNORECASE)
UPPER_WORDS = re.compile(r"\b([A-Z][A-Z0-9_\-]+)\b")


class ActionOnlyController(Controller):
    """
    Simple action extraction controller with game binding and validation.

    Parses responses in "ACTION: <value>" format or detects uppercase tokens.
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
        >>> # Caller converts to ActionResult with fallback semantics
        >>> action_result = parse_result.to_action_result(fallback="UNKNOWN")

    Parsing returns ParseResult:
        - success=True, action=<normalized>: Valid action extracted and validated
        - success=False, action=None, error=<reason>: Parsing or validation failed
        - Caller applies fallback via to_action_result(fallback)

    Implements:
        - DS1-DS2: Determinism & stateless parsing
        - GB1-GB6: Game binding for validation
        - AP1-AP3: Action parsing with success/failure indicators
        - VF1: Casefold validation semantics
    """

    def __init__(self):
        """
        Initialize ActionOnlyController.

        Note: Fallback semantics are now handled by caller via ParseResult.to_action_result(fallback).
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
            1. Look for "ACTION: <value>" field (preferred)
            2. Fallback to detecting uppercase tokens (e.g., "ATTACK")
            3. Validate against allowed_actions if bound
            4. Return success=True/False based on extraction and validation

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

        # Extract primary action and candidates
        primary_action, candidates = self._extract_action(cleaned)

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
                        "candidates": candidates,
                    },
                )
            else:
                # AP3: Failure case - validation failed
                error_msg = (
                    f"Parsed action '{primary_action}' not in allowed set {sorted(self._allowed_actions)}"
                    if primary_action
                    else "No action token found"
                )
                return ParseResult(
                    success=False,
                    action=None,
                    raw_response=cleaned,
                    reasoning=None,
                    error=error_msg,
                    metadata={
                        "allowed_actions": list(self._allowed_actions),
                        "candidates": candidates,
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
                    metadata={"validated": False, "candidates": candidates},
                )
            else:
                # AP3: Failure case - no action found
                return ParseResult(
                    success=False,
                    action=None,
                    raw_response=cleaned,
                    reasoning=None,
                    error="No action token found",
                    metadata={"candidates": candidates},
                )

    def _extract_action(self, response: str) -> tuple[Optional[str], List[str]]:
        """
        Detect the most likely action token and supporting candidates.

        Args:
            response: Cleaned response string

        Returns:
            (primary_action, all_candidates)

        Strategy:
            1. Check for "ACTION: <value>" field first (most explicit)
            2. Fallback to detecting uppercase words (ATTACK, DEFEND, etc.)
            3. Return None if no candidates found
        """
        candidates: List[str] = []

        # Strategy 1: Look for "ACTION: <value>" field
        match = ACTION_FIELD.search(response)
        if match:
            primary = match.group("action").strip().upper()
            candidates.append(primary)
            return primary, candidates

        # Strategy 2: Look for uppercase tokens
        for token in UPPER_WORDS.findall(response):
            normalized = token.upper()
            if normalized not in candidates:
                candidates.append(normalized)

        # Return last candidate as primary (most likely to be action)
        primary = candidates[-1] if candidates else None
        return primary, candidates

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
