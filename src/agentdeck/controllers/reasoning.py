"""Stated-rationale response controller for AgentDeck."""

from __future__ import annotations

import re
from typing import Optional, Set

from ..core.base.controller import Controller
from ..core.base.game import Game
from ..core.types import ParseResult

# Regex patterns for action extraction (same as ActionOnlyController)
# Anchor ACTION to line start to avoid matching narration blocks like "Last Action:".
ACTION_FIELD = re.compile(r"(?im)^\s*ACTION:\s*(?P<action>[A-Za-z0-9_\-]+)\b")
RATIONALE_ACTION_RESPONSE = re.compile(
    r"^\s*REASONING:\s*(?P<reasoning>.+?)\s*\n" r"\s*ACTION:\s*(?P<action>[A-Za-z0-9_\-]+)\s*$",
    re.DOTALL | re.IGNORECASE,
)


class ReasoningController(Controller):
    """
    Controller that requests and extracts a stated rationale alongside the action.

    Parses responses in "REASONING: ... ACTION: ..." format per SPEC-CONTROLLER v1.1.0.
    Returns ParseResult for stateless, deterministic parsing.

    Example usage:
        >>> game = FixedDamageGame()
        >>> controller = ReasoningController()
        >>> controller.bind_game(game)  # Extracts allowed_actions
        >>> parse_result = controller.parse("REASONING: Attack to win\\nACTION: ATTACK")
        >>> parse_result.success
        True
        >>> parse_result.action
        'ATTACK'
        >>> parse_result.reasoning
        'Attack to win'
    """

    def __init__(self) -> None:
        """
        Initialize ReasoningController.

        Parse failures are surfaced through ``ActionParseError``.
        """
        self._allowed_actions: Optional[Set[str]] = None  # Set during bind_game()

    def bind_game(self, game: Game) -> None:
        """
        Bind to game and extract allowed_actions for validation (per GB1-GB6).

        Args:
            game: Game instance providing allowed_actions
        """
        self._allowed_actions = {action.upper() for action in game.allowed_actions}

    def get_format_instructions(self) -> str:
        """
        Return format instructions for turn prompt (per FI1-FI2, GB4-GB5).

        Returns:
            Dynamic instructions based on binding state
        """
        if self._allowed_actions:
            # GB5: Return game-specific instructions when bound
            actions = ", ".join(sorted(self._allowed_actions))
            return (
                f"Allowed actions: {actions}\n\n"
                "Respond only with exactly these two fields:\n"
                "REASONING: <your stated rationale>\n"
                "ACTION: <action>"
            )
        else:
            # GB4: Return sensible defaults when unbound
            return (
                "Respond only with exactly these two fields:\n"
                "REASONING: <your stated rationale>\n"
                "ACTION: <action>"
            )

    def parse(self, response: str) -> ParseResult:
        """
        Parse turn action response with reasoning extraction.

        Args:
            response: Raw LLM response string

        Returns:
            ParseResult with success, action, reasoning, and metadata

        Parsing strategy:
            1. Extract reasoning from "REASONING: ..." section
            2. Require an explicit "ACTION: <value>" field
            3. Validate against allowed_actions if bound
        """
        # Clean and trim response
        cleaned = response.strip()

        # Extract reasoning
        reasoning_match = re.search(
            r"REASONING:\s*(.+?)(?=ACTION:|$)",
            cleaned,
            re.DOTALL | re.IGNORECASE,
        )
        reasoning = reasoning_match.group(1).strip() if reasoning_match else None

        # Extract action using same strategy as ActionOnlyController
        primary_action = self._extract_action(cleaned)

        # Validate against allowed actions if bound
        if self._allowed_actions:
            valid, validated_action = self._validate_action(primary_action)
            if valid and validated_action:
                contract_satisfied = self._satisfies_response_contract(cleaned, validated_action)
                # Success case
                return ParseResult(
                    success=True,
                    action=validated_action,
                    raw_response=cleaned,
                    reasoning=reasoning,
                    error=None,
                    metadata={
                        "validated": True,
                        "allowed_actions": list(self._allowed_actions),
                        "resolution_method": "explicit_action_field",
                        "declared_action": validated_action,
                        "contract_satisfied": contract_satisfied,
                        "reasoning_extracted": reasoning is not None,
                    },
                )
            else:
                # Failure case - validation failed
                error_msg = (
                    f"Parsed action '{primary_action}' not in allowed set {sorted(self._allowed_actions)}"
                    if primary_action
                    else "No ACTION: field found"
                )
                return ParseResult(
                    success=False,
                    action=None,
                    raw_response=cleaned,
                    reasoning=reasoning,
                    error=error_msg,
                    metadata={
                        "allowed_actions": list(self._allowed_actions),
                        "resolution_method": "unresolved",
                        "declared_action": primary_action,
                        "contract_satisfied": False,
                        "reasoning_extracted": reasoning is not None,
                    },
                )
        else:
            # No validation (unbound) - accept any parsed action
            if primary_action:
                contract_satisfied = self._satisfies_response_contract(cleaned, primary_action)
                # Success case
                return ParseResult(
                    success=True,
                    action=primary_action,
                    raw_response=cleaned,
                    reasoning=reasoning,
                    error=None,
                    metadata={
                        "validated": False,
                        "resolution_method": "explicit_action_field",
                        "declared_action": primary_action,
                        "contract_satisfied": contract_satisfied,
                        "reasoning_extracted": reasoning is not None,
                    },
                )
            else:
                # Failure case - no action found
                return ParseResult(
                    success=False,
                    action=None,
                    raw_response=cleaned,
                    reasoning=reasoning,
                    error="No ACTION: field found",
                    metadata={
                        "resolution_method": "unresolved",
                        "declared_action": None,
                        "contract_satisfied": False,
                        "reasoning_extracted": reasoning is not None,
                    },
                )

    def _extract_action(self, response: str) -> Optional[str]:
        """Extract only an explicit, line-anchored action declaration."""
        match = ACTION_FIELD.search(response)
        if match:
            return match.group("action").strip().upper()
        return None

    def _satisfies_response_contract(self, response: str, action: str) -> bool:
        """Return whether the entire response follows the requested rationale format."""
        match = RATIONALE_ACTION_RESPONSE.fullmatch(response)
        return bool(match and match.group("action").upper() == action.upper())

    def _validate_action(self, action: Optional[str]) -> tuple[bool, Optional[str]]:
        """
        Check whether parsed action belongs to allowed set.

        Args:
            action: Candidate action to validate

        Returns:
            (is_valid, normalized_action)
        """
        if action is None:
            return False, None

        if self._allowed_actions is None:
            # Not bound - accept anything
            return True, action

        # Casefold semantics - compare uppercase
        candidate = action.upper()
        is_valid = candidate in self._allowed_actions

        return is_valid, candidate if is_valid else None

    def describe(self) -> dict:
        """
        Return controller configuration for introspection.

        Returns:
            Dictionary with controller type, format, and validation settings
        """
        descriptor = {
            "type": self.__class__.__name__,
            "format_instructions": "REASONING/ACTION",
        }
        if self._allowed_actions:
            descriptor["allowed_actions"] = list(self._allowed_actions)
            descriptor["bound"] = True
        else:
            descriptor["bound"] = False
        return descriptor
