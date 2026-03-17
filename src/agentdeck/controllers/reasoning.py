"""Chain-of-thought reasoning controller for AgentDeck."""

from __future__ import annotations

import re
from typing import List, Optional, Set

from ..core.base.controller import Controller
from ..core.base.game import Game
from ..core.types import ParseResult

# Regex patterns for action extraction (same as ActionOnlyController)
# Anchor ACTION to line start to avoid matching narration blocks like "Last Action:".
ACTION_FIELD = re.compile(r"(?im)^\s*ACTION:\s*(?P<action>[A-Za-z0-9_\-]+)\b")
UPPER_WORDS = re.compile(r"\b([A-Z][A-Z0-9_\-]+)\b")


class ReasoningController(Controller):
    """
    Controller that extracts reasoning alongside the action.

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

        Note: Fallback semantics are handled by caller via ParseResult.to_action_result(fallback).
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
                "Please respond in the following format:\n"
                "REASONING: [Your step-by-step thought process]\n"
                f"ACTION: [Your chosen action]\nAllowed actions: {actions}"
            )
        else:
            # GB4: Return sensible defaults when unbound
            return (
                "Please respond in the following format:\n"
                "REASONING: [Your step-by-step thought process]\n"
                "ACTION: [Your chosen action]"
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
            2. Extract action from "ACTION: <value>" field or uppercase tokens
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
        primary_action, candidates = self._extract_action(cleaned)

        # Validate against allowed actions if bound
        if self._allowed_actions:
            valid, validated_action = self._validate_action(primary_action)
            resolution_strategy = "primary"
            allowed_candidates: List[str] = []

            if not valid:
                validated_action, resolution_strategy, allowed_candidates = (
                    self._resolve_bound_action(
                        response=cleaned,
                        primary_action=primary_action,
                        candidates=candidates,
                    )
                )
                valid = validated_action is not None

            if valid and validated_action:
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
                        "candidates": candidates,
                        "allowed_candidates": allowed_candidates,
                        "resolution_strategy": resolution_strategy,
                        "reasoning_extracted": reasoning is not None,
                    },
                )
            else:
                # Failure case - validation failed
                error_msg = (
                    f"Parsed action '{primary_action}' not in allowed set {sorted(self._allowed_actions)}"
                    if primary_action
                    else "No action token found"
                )
                return ParseResult(
                    success=False,
                    action=None,
                    raw_response=cleaned,
                    reasoning=reasoning,
                    error=error_msg,
                    metadata={
                        "allowed_actions": list(self._allowed_actions),
                        "candidates": candidates,
                        "allowed_candidates": allowed_candidates,
                        "resolution_strategy": resolution_strategy,
                        "reasoning_extracted": reasoning is not None,
                    },
                )
        else:
            # No validation (unbound) - accept any parsed action
            if primary_action:
                # Success case
                return ParseResult(
                    success=True,
                    action=primary_action,
                    raw_response=cleaned,
                    reasoning=reasoning,
                    error=None,
                    metadata={
                        "validated": False,
                        "candidates": candidates,
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
                    error="No action token found",
                    metadata={
                        "candidates": candidates,
                        "reasoning_extracted": reasoning is not None,
                    },
                )

    def _extract_action(self, response: str) -> tuple[Optional[str], List[str]]:
        """
        Detect the most likely action token and supporting candidates.

        Args:
            response: Cleaned response string

        Returns:
            (primary_action, all_candidates)

        Strategy:
            1. Check for explicit "ACTION: <value>" field
            2. If not found, look for uppercase words ONLY in the region after reasoning ends
               (to avoid picking up words from reasoning like "NO" in "no potions left")
        """
        candidates: List[str] = []

        # Strategy 1: Look for explicit "ACTION: <value>" field
        match = ACTION_FIELD.search(response)
        if match:
            primary = match.group("action").strip().upper()
            candidates.append(primary)
            return primary, candidates

        # Strategy 2: Look for uppercase words, but only AFTER reasoning section
        # Find where reasoning ends (look for "ACTION:" marker or end of reasoning)
        reasoning_end = 0
        reasoning_match = re.search(
            r"REASONING:\s*(.+?)(?=ACTION:|$)", response, re.DOTALL | re.IGNORECASE
        )
        if reasoning_match:
            reasoning_end = reasoning_match.end()

        # Only search for uppercase words in text after reasoning
        post_reasoning = response[reasoning_end:]
        for token in UPPER_WORDS.findall(post_reasoning):
            normalized = token.upper()
            # Filter out common non-action words
            if normalized not in ["NO", "YES", "NONE", "NULL"] and normalized not in candidates:
                candidates.append(normalized)

        # Return last candidate as primary (most likely to be action)
        primary = candidates[-1] if candidates else None
        return primary, candidates

    def _resolve_bound_action(
        self,
        *,
        response: str,
        primary_action: Optional[str],
        candidates: List[str],
    ) -> tuple[Optional[str], str, List[str]]:
        """Resolve action from bound allowed_actions when primary token is invalid."""
        if self._allowed_actions is None:
            return None, "unbound", []

        allowed_candidates = [
            token.upper() for token in candidates if token.upper() in self._allowed_actions
        ]
        if not allowed_candidates:
            mentioned_actions = self._find_allowed_action_mentions(response)
            if not mentioned_actions:
                return None, "no_allowed_candidate", []
            if len(mentioned_actions) == 1:
                return mentioned_actions[0], "single_allowed_mention", []

            intent_action = self._extract_intent_action(response, mentioned_actions)
            if intent_action:
                return intent_action, "intent_pattern", []

            return mentioned_actions[0], "first_allowed_mention", []

        if len(allowed_candidates) == 1:
            return allowed_candidates[0], "single_allowed_candidate", allowed_candidates

        intent_action = self._extract_intent_action(response, allowed_candidates)
        if intent_action:
            return intent_action, "intent_pattern", allowed_candidates

        return allowed_candidates[0], "first_allowed_candidate", allowed_candidates

    def _extract_intent_action(self, response: str, allowed_candidates: List[str]) -> Optional[str]:
        """Infer likely action from first-person intent when multiple allowed tokens appear."""
        if not allowed_candidates:
            return None

        actions_pattern = "|".join(
            re.escape(token) for token in sorted(set(allowed_candidates), key=len, reverse=True)
        )
        patterns = [
            rf"\bI(?:'ll| will| choose| chose| pick| picked| use| used| am going to)?\b[^\n]{{0,120}}\b({actions_pattern})\b",
            rf"\b(?:my|the)\s+action(?:\s+is)?\s*[:\-]?\s*({actions_pattern})\b",
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(1).upper()

        return None

    def _find_allowed_action_mentions(self, response: str) -> List[str]:
        """Find allowed actions mentioned in response text, case-insensitively."""
        if self._allowed_actions is None:
            return []

        mentioned: List[str] = []
        for action in sorted(self._allowed_actions):
            pattern = rf"\b{re.escape(action)}\b"
            if re.search(pattern, response, re.IGNORECASE):
                mentioned.append(action)
        return mentioned

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
