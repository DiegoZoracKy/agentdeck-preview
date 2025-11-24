"""Match narrative spectator for AgentDeck."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from ..core.base.spectator import Spectator
from ..core.types import Event, EventContext, MatchResult


class MatchNarrator(Spectator):
    """
    Provides real-time match narration showing turn-by-turn progression.

    Per SPEC-SPECTATOR v1.2.0:
    - HC1-HC4: Duck-typed handlers, read-only, quick completion
    - SS1-SS4: Resets state per batch/match, tolerates missing context
    - EI1-EI3: Error-safe, no execution mutations
    - LI1-LI5: Uses injected logger for INFO-level output to core streams

    Output includes:
    - Match start with game/players
    - Handshake phase: player acknowledgments
    - Turn-by-turn: player, reasoning, action, token usage, state changes, duration
    - Conclusion phase: player reflections
    - Match completion with winner, turns, total duration

    Example output:
        Match match_abc123 starting
        Game: FixedDamageGame
        Players: ['GPT-A', 'GPT-B']
        ✓ GPT-A handshake: OK
        ✓ GPT-B handshake: READY

        Turn 1: GPT-A
        Reasoning: Opponent is at full health, attacking is the best strategy to reduce their HP
        Action: ATTACK
        Usage: tokens=155 (prompt=153, completion=2)
        State After:
        Δ last_action.GPT-A:None->ATTACK, health.GPT-B:100->80
        Turn Duration: 1.04s

        💭 GPT-A reflection: Good match, aggressive strategy paid off
        💭 GPT-B reflection: Should have defended more early on

        Match match_abc123 complete
        Winner: GPT-A
        Turns: 21
        Duration: 18.00s
    """

    def __init__(self, *, logger: Any = None, show_state_changes: bool = True) -> None:
        """
        Initialize match narrator.

        Args:
            logger: Optional logger (auto-injected by Console/ReplayEngine per LI1)
            show_state_changes: Show state delta after each turn
        """
        super().__init__(logger=logger)
        self.show_state_changes = show_state_changes

        # Match state (reset per match)
        self.match_id: Optional[str] = None
        self.match_start_time: float = 0.0
        self.turn_start_time: float = 0.0
        self.game_name: Optional[str] = None
        self.player_names: List[str] = []
        self.first_player_selected: bool = False

        # Handshake prompt cache (keyed by player name)
        self._handshake_prompts: Dict[str, str] = {}

    def on_match_start(
        self,
        game: Any,
        players: List[Any],
        match_id: Optional[str] = None,
        context: Optional[EventContext] = None,
        **kwargs: Any,  # Accept player ordering fields (seed, player_order, etc.)
    ) -> None:
        """Display match start banner. Per SS3: explicit state reset."""
        self.match_id = match_id
        self.match_start_time = time.time()
        self.game_name = game.__class__.__name__ if game else "Unknown"
        self.player_names = [p.name for p in players] if players else []
        self.first_player_selected = False

        # Clear handshake prompt cache (SS3: reset state between matches)
        self._handshake_prompts.clear()

        # Log match start
        if self.logger:
            self.logger.info(f"Match {match_id} starting")
            self.logger.info(f"Game: {self.game_name}")
            self.logger.info(f"Players: {self.player_names}")

    def on_dialogue_turn(self, event: Event) -> None:
        """
        Cache handshake prompts for later display.

        When a dialogue turn with phase="handshake" arrives, store the prompt
        text so we can display it alongside the handshake completion/abort.
        """
        data = event.data
        phase = data.get("phase")

        if phase == "handshake":
            player = data.get("player")
            # Recorder/replay use prompt_text; live dialogue_turn events use prompt
            prompt_text = data.get("prompt_text") or data.get("prompt") or ""

            if player and prompt_text:
                self._handshake_prompts[player] = prompt_text

    def on_player_handshake_complete(self, event: Event) -> None:
        """Display player handshake completion with full prompt context."""
        if not self.logger:
            return

        data = event.data
        player = data.get("player", "Unknown")
        response = data.get("response", "")

        # Log the handshake acceptance
        prompt = data.get("prompt_text") or self._handshake_prompts.get(player)
        if prompt:
            cleaned = prompt.replace("\\n", "\n")
            self.logger.info(f"{player} handshake instructions:")
            self.logger.info(cleaned)

            # Clear the cached prompt if we stored it locally
            self._handshake_prompts.pop(player, None)

        self.logger.info(f"✓ {player} handshake: {response}")

    def on_player_handshake_abort(self, event: Event) -> None:
        """Display player handshake rejection with full prompt context."""
        if not self.logger:
            return

        data = event.data
        player = data.get("player", "Unknown")
        reason = data.get("reason", "No reason provided")

        # Log the handshake rejection
        prompt = event.data.get("prompt_text") or self._handshake_prompts.get(player)
        if prompt:
            cleaned = prompt.replace("\\n", "\n")
            self.logger.info(f"{player} handshake instructions:")
            self.logger.info(cleaned)

            # Clear the cached prompt if we stored it locally
            self._handshake_prompts.pop(player, None)

        self.logger.info(f"✗ {player} rejected handshake: {reason}")

    def on_gameplay(self, event: Event) -> None:
        """
        Narrate turn-by-turn gameplay.

        Per HC3: Read-only access to event data.
        Per SPEC-OBSERVABILITY §3.2: GAMEPLAY event has mechanic, phase_index,
        state_before, state_after, player, action, metadata, etc.
        """
        if not self.logger:
            return

        data = event.data
        ctx = event.context

        # Extract turn info
        mechanic = data.get("mechanic")
        if mechanic != "turn_based":
            return  # Only narrate turn-based games for now

        # Get current player from GAMEPLAY event
        player = data.get("player")
        if not player:
            return

        # Check if this is turn 0 (first turn) - log first player selection
        turn_index = ctx.get("turn_index", 0)
        if turn_index == 0 and not self.first_player_selected:
            player_index = self.player_names.index(player) if player in self.player_names else -1
            if player_index >= 0:
                self.logger.info(f"🎲 First player selected: {player} (index {player_index})")
                self.first_player_selected = True

        # Start timing this turn
        self.turn_start_time = time.time()

        # Extract action info (handle ActionResult dataclass, dict, or string)
        action_obj = data.get("action")
        if action_obj is None:
            return  # No action to narrate

        # Normalize action text and metadata based on type
        if isinstance(action_obj, dict):
            # Console emits action as dict: {"action": "...", "metadata": {...}, ...}
            action_text = action_obj.get("action", str(action_obj))
            reasoning = action_obj.get("reasoning")
            metadata = action_obj.get("metadata", {})
        elif hasattr(action_obj, "action"):
            # ActionResult dataclass from tests or future TurnLoop
            action_text = getattr(action_obj, "action", str(action_obj))
            reasoning = getattr(action_obj, "reasoning", None)
            action_metadata = getattr(action_obj, "metadata", {}) or {}
            data_metadata = data.get("metadata", {})
            metadata = action_metadata or data_metadata
        else:
            # Plain string action
            action_text = str(action_obj)
            reasoning = None
            metadata = data.get("metadata", {})

        if not isinstance(action_text, str):
            action_text = str(action_text)

        # Extract turn context if available
        turn_context = data.get("turn_context", {})
        turn_number = turn_context.get("turn_number", turn_index + 1)  # 1-based for display

        # Log turn header
        self.logger.info(f"Turn {turn_number}: {player}")

        # Show reasoning if available (from ReasoningController)
        if reasoning:
            self.logger.info(f"Reasoning: {reasoning}")

        self.logger.info(f"Action: {action_text}")

        # Show token usage if available in metadata
        usage_info = metadata.get("usage_info")
        if usage_info:
            prompt_tokens = usage_info.get("prompt_tokens", 0)
            completion_tokens = usage_info.get("completion_tokens", 0)
            total_tokens = usage_info.get("total_tokens", 0)
            self.logger.info(
                f"Usage: tokens={total_tokens} (prompt={prompt_tokens}, completion={completion_tokens})"
            )

        # Show state changes if enabled
        if self.show_state_changes:
            state_before = data.get("state_before", {})
            state_after = data.get("state_after", {})

            # Compute delta
            changes = self._compute_state_delta(state_before, state_after)
            if changes:
                self.logger.info("State After:")
                self.logger.info(f"Δ {changes}")

        # Show turn duration
        turn_duration = turn_context.get("duration", time.time() - self.turn_start_time)
        self.logger.info(f"Turn Duration: {turn_duration:.2f}s")

    def on_player_conclusion(self, event: Event) -> None:
        """Display player conclusion/reflection."""
        if not self.logger:
            return

        data = event.data
        player = data.get("player", "Unknown")
        reflection = data.get("reflection")

        if reflection:
            self.logger.info(f"💭 {player} reflection: {reflection}")

    def on_match_end(self, result: MatchResult, context: Optional[EventContext] = None) -> None:
        """Display match completion summary. Per HC3: read-only access to result."""
        if not self.logger:
            return

        # Calculate match duration
        duration = time.time() - self.match_start_time if self.match_start_time > 0 else 0

        # Extract match metadata
        winner = result.winner or "Draw"
        turns = result.metadata.get("turns", "?")

        # Log match end
        self.logger.info(f"Match {self.match_id} complete")
        self.logger.info(f"Winner: {winner}")
        self.logger.info(f"Turns: {turns}")
        self.logger.info(f"Duration: {duration:.2f}s")

    def _compute_state_delta(self, before: Dict[str, Any], after: Dict[str, Any]) -> str:
        """
        Compute human-readable state delta.

        Returns a string like: "health.Alice:100->80, potions.Bob:3->2"
        """
        changes = []

        # Find changed keys
        all_keys = set(before.keys()) | set(after.keys())

        for key in sorted(all_keys):
            before_val = before.get(key)
            after_val = after.get(key)

            if before_val != after_val:
                # Handle nested dicts (common in game states)
                if isinstance(before_val, dict) and isinstance(after_val, dict):
                    for subkey in sorted(set(before_val.keys()) | set(after_val.keys())):
                        before_sub = before_val.get(subkey)
                        after_sub = after_val.get(subkey)
                        if before_sub != after_sub:
                            changes.append(f"{key}.{subkey}:{before_sub}->{after_sub}")
                else:
                    changes.append(f"{key}:{before_val}->{after_val}")

        return ", ".join(changes) if changes else "(no changes)"
