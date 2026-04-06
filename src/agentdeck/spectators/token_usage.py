"""Token usage and cost tracking spectator for AgentDeck."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from ..core.base.spectator import Spectator
from ..core.types import Event, EventContext, MatchResult


class TokenUsageTracker(Spectator):
    """
    Tracks LLM API token usage and costs across matches.

    Per SPEC-SPECTATOR v1.0.0:
    - HC1-HC4: Duck-typed handlers, read-only, quick completion
    - SS1-SS4: Resets state per batch, tolerates missing context
    - EI1-EI3: Error-safe, no execution mutations
    - LO1: Uses logger for structured output

    Extracts usage data from ActionResult.metadata in GAMEPLAY events.
    Compatible with Player implementations that include API usage metadata.

    Usage:
        tracker = TokenUsageTracker()
        deck.play(game, players, matches=10, spectators=[tracker])
        print(tracker.get_summary())  # Total tokens, cost breakdown
    """

    def __init__(self, *, logger: Any = None) -> None:
        """Initialize token usage tracker."""
        super().__init__(logger=logger)

        # Per-batch tracking (reset in on_batch_start per SS3)
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_tokens: int = 0
        self.total_cost: float = 0.0
        self.total_calls: int = 0

        # Per-player tracking
        self.player_tokens: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0}
        )
        self.player_costs: Dict[str, float] = defaultdict(float)

        # Per-model tracking
        self.model_usage: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"calls": 0, "tokens": 0, "cost": 0.0}
        )
        self._seen_call_ids: set[str] = set()

    def on_batch_start(
        self,
        batch_id: str,
        game,
        players,
        matches: int,
        context: Optional[EventContext] = None,
        **kwargs: Any,
    ) -> None:
        """Reset state for new batch. Per SS3: explicit state reset."""
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.total_calls = 0
        self.player_tokens.clear()
        self.player_costs.clear()
        self.model_usage.clear()
        self._seen_call_ids.clear()

    def _normalize_usage(self, usage: Any) -> Optional[Dict[str, Any]]:
        """Normalize usage metadata across live, replay, and legacy event shapes."""
        if not isinstance(usage, dict):
            return None

        prompt_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0
        completion_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
        total = usage.get("tokens")
        if total is None:
            total = usage.get("total_tokens")
        if total is None:
            total = prompt_tokens + completion_tokens

        cost = usage.get("cost", 0.0) or 0.0
        if not any([prompt_tokens, completion_tokens, total, cost]):
            return None

        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total,
            "cost": cost,
            "model": usage.get("model") or usage.get("provider_model") or "unknown",
            "call_id": usage.get("call_id"),
        }

    def _extract_usage(self, data: Any) -> Optional[Dict[str, Any]]:
        """Extract usage from event shapes emitted live or replayed from recordings."""
        if not isinstance(data, dict):
            return None

        action_data = data.get("action")
        if isinstance(action_data, dict):
            action_metadata = action_data.get("metadata")
        else:
            action_metadata = getattr(action_data, "metadata", None)

        metadata = data.get("metadata")
        prompt = data.get("prompt")

        candidates = [
            data.get("usage_info"),
            action_metadata,
            action_metadata.get("usage_info") if isinstance(action_metadata, dict) else None,
            metadata,
            metadata.get("usage_info") if isinstance(metadata, dict) else None,
            prompt.get("usage_info") if isinstance(prompt, dict) else None,
        ]

        for candidate in candidates:
            normalized = self._normalize_usage(candidate)
            if normalized:
                return normalized
        return None

    def _track_event(self, event: Event) -> None:
        """Track usage for a single lifecycle or gameplay event."""
        try:
            data = event.data
            if not isinstance(data, dict):
                return

            player = data.get("player")
            if not player:
                return

            usage = self._extract_usage(data)
            if not usage:
                return

            call_id = usage.get("call_id")
            if call_id and call_id in self._seen_call_ids:
                return
            if call_id:
                self._seen_call_ids.add(call_id)

            prompt_tokens = usage["prompt_tokens"]
            completion_tokens = usage["completion_tokens"]
            total = usage["total_tokens"]
            cost = usage["cost"]
            model = usage["model"]

            self.total_prompt_tokens += prompt_tokens
            self.total_completion_tokens += completion_tokens
            self.total_tokens += total
            self.total_cost += cost
            self.total_calls += 1

            self.player_tokens[player]["prompt_tokens"] += prompt_tokens
            self.player_tokens[player]["completion_tokens"] += completion_tokens
            self.player_tokens[player]["total_tokens"] += total
            self.player_tokens[player]["calls"] += 1
            self.player_costs[player] += cost

            self.model_usage[model]["calls"] += 1
            self.model_usage[model]["tokens"] += total
            self.model_usage[model]["cost"] += cost
        except Exception:
            # Per EI1: Silently handle errors, don't crash execution
            pass

    def on_gameplay(self, event: Event) -> None:
        """Track gameplay token usage from current and replayed event payloads."""
        self._track_event(event)

    def on_player_handshake_complete(self, event: Event) -> None:
        """Track handshake token usage."""
        self._track_event(event)

    def on_player_handshake_abort(self, event: Event) -> None:
        """Track rejected handshake token usage."""
        self._track_event(event)

    def on_player_action_parse_failed(self, event: Event) -> None:
        """Track failed parse calls when usage metadata is available."""
        self._track_event(event)

    def on_player_conclusion(self, event: Event) -> None:
        """Track conclusion/reflection token usage."""
        self._track_event(event)

    def on_batch_end(
        self,
        batch_id: str,
        results: List[MatchResult],
        context: Optional[EventContext] = None,
        **kwargs: Any,
    ) -> None:
        """Log batch token usage summary. Per EI2: avoid raising in cleanup."""
        try:
            if self.total_calls == 0:
                return  # No LLM calls tracked

            if self.logger and hasattr(self.logger, "info"):
                self.logger.info(
                    f"\n{'='*60}\n" f"Token Usage Summary (Batch {batch_id[:8]})\n" f"{'='*60}"
                )
                self.logger.info(
                    f"Total API Calls: {self.total_calls} | "
                    f"Total Tokens: {self.total_tokens:,} | "
                    f"Total Cost: ${self.total_cost:.4f}"
                )

                if self.player_tokens:
                    self.logger.info(f"\n{'-'*60}\nPer-Player Usage:")
                    for player, stats in sorted(self.player_tokens.items()):
                        cost = self.player_costs[player]
                        self.logger.info(
                            f"  {player}: {stats['calls']} calls | "
                            f"{stats['total_tokens']:,} tokens | ${cost:.4f}"
                        )

                if self.model_usage:
                    self.logger.info(f"\n{'-'*60}\nPer-Model Usage:")
                    for model, stats in sorted(self.model_usage.items()):
                        self.logger.info(
                            f"  {model}: {stats['calls']} calls | "
                            f"{stats['tokens']:,} tokens | ${stats['cost']:.4f}"
                        )

                self.logger.info(f"{'='*60}\n")
        except Exception:
            # Per EI2: Don't raise in cleanup
            pass

    def get_summary(self) -> Dict[str, Any]:
        """
        Get structured summary of token usage.

        Returns:
            Dictionary with total, per-player, and per-model usage stats.
        """
        return {
            "total": {
                "calls": self.total_calls,
                "prompt_tokens": self.total_prompt_tokens,
                "completion_tokens": self.total_completion_tokens,
                "total_tokens": self.total_tokens,
                "cost": round(self.total_cost, 4),
            },
            "per_player": {
                player: {
                    "calls": stats["calls"],
                    "prompt_tokens": stats["prompt_tokens"],
                    "completion_tokens": stats["completion_tokens"],
                    "total_tokens": stats["total_tokens"],
                    "cost": round(self.player_costs[player], 4),
                }
                for player, stats in self.player_tokens.items()
            },
            "per_model": {
                model: {
                    "calls": stats["calls"],
                    "tokens": stats["tokens"],
                    "cost": round(stats["cost"], 4),
                }
                for model, stats in self.model_usage.items()
            },
        }

    def get_average_cost_per_match(self, num_matches: int) -> float:
        """Calculate average cost per match."""
        return self.total_cost / num_matches if num_matches > 0 else 0.0
