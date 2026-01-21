#!/usr/bin/env python3
"""
Run multiple FixedDamageGame matches with two Claude Haiku players.

Usage:
  export ANTHROPIC_API_KEY=your_api_key_here
  python scripts/run_fixed_damage_claude_one_match_codex.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Load environment variables from .env if available.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Add src to path for local development.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentdeck import AgentDeck, AgentDeckConfig
from agentdeck.controllers import ActionOnlyController, ReasoningController
from agentdeck.games.examples import FixedDamageGame
from agentdeck.players import ClaudePlayer
from agentdeck.spectators import ProgressDisplay, StatsTracker, TokenUsageTracker
from agentdeck.core.types import LogLevel


MATCHES = 5
SEED = 42
CONCURRENCY = 1
CHEAPEST_ANTHROPIC_MODEL = "claude-3-haiku-20240307"
MODEL_HAIKU = os.getenv("ANTHROPIC_MODEL", CHEAPEST_ANTHROPIC_MODEL)
USE_REASONING = os.getenv("CLAUDE_USE_REASONING", "false").strip().lower() in (
    "1",
    "true",
    "yes",
)


class StrictReasoningController(ReasoningController):
    """Reasoning controller with a strict handshake response requirement."""

    def get_handshake_format_instructions(self) -> str:
        return (
            "Reply with ONLY the single word 'OK' (nothing else). "
            "Do not add any explanation or additional text."
        )


class StrictActionController(ActionOnlyController):
    """Action-only controller with stricter parsing and formatting."""

    def get_handshake_format_instructions(self) -> str:
        return (
            "Reply with ONLY the single word 'OK' (nothing else). "
            "Do not add any explanation or additional text."
        )

    def get_format_instructions(self) -> str:
        actions = ", ".join(sorted(self._allowed_actions or []))
        return (
            "Respond with ONLY the following format:\n"
            "ACTION: <action>\n"
            f"Allowed actions: {actions}"
        )

    def parse(self, response: str):
        result = super().parse(response)
        if result.success or not self._allowed_actions:
            return result

        # Fallback: accept any allowed action token (case-insensitive) found in response.
        cleaned = response.strip()
        for action in sorted(self._allowed_actions):
            if action.lower() in cleaned.lower():
                from agentdeck.core.types import ParseResult

                return ParseResult(
                    success=True,
                    action=action,
                    raw_response=cleaned,
                    reasoning=None,
                    error=None,
                    metadata={
                        "validated": True,
                        "allowed_actions": list(self._allowed_actions),
                        "fallback": True,
                    },
                )
        return result


def build_game() -> FixedDamageGame:
    return FixedDamageGame(
        max_health=100,
        attack_damage=20,
        potion_heal=30,
        starting_potions=2,
        information_level="partial",
    )


def build_players() -> tuple[ClaudePlayer, ClaudePlayer]:
    controller = StrictReasoningController() if USE_REASONING else StrictActionController()
    haiku_a = ClaudePlayer(
        name="Claude-Haiku-A",
        model=MODEL_HAIKU,
        temperature=0.2 if USE_REASONING else 0.0,
        controller=controller,
        max_tokens=200,
    )
    haiku_b = ClaudePlayer(
        name="Claude-Haiku-B",
        model=MODEL_HAIKU,
        temperature=0.2 if USE_REASONING else 0.0,
        controller=controller,
        max_tokens=200,
    )
    return haiku_a, haiku_b


def main() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY is not set.")
        print("Set it with: export ANTHROPIC_API_KEY=your_api_key_here")
        sys.exit(1)

    game = build_game()
    player_a, player_b = build_players()

    config = AgentDeckConfig(
        seed=SEED,
        concurrency=CONCURRENCY,
        log_level=LogLevel.INFO,
    )

    spectators = [ProgressDisplay(), StatsTracker(), TokenUsageTracker()]

    deck = None
    try:
        with AgentDeck(game=game, session=config, spectators=spectators) as deck:
            results = deck.play(players=[player_a, player_b], matches=MATCHES, seed=SEED)
            session_id = deck.session.session_id
    except Exception as exc:
        session_id = deck.session.session_id if deck else "unknown"
        session_dir = Path(config.run_dir) / session_id
        print("\n=== Match Failed ===")
        print(f"Session: {session_dir}")
        print(f"Logs: {session_dir / 'logs'}")
        print(f"Records: {session_dir / 'records'}")
        print(f"Error: {exc}")
        sys.exit(1)

    session_dir = Path(config.run_dir) / session_id / "records"

    first_players = [
        match.metadata.get("first_player", {}).get("name") for match in results.matches
    ]
    unique_first_players = {name for name in first_players if name}

    print("\n=== Match Summary ===")
    print(f"Controller: {'Reasoning' if USE_REASONING else 'ActionOnly'}")
    print(f"Model: {MODEL_HAIKU}")
    print(f"Matches: {MATCHES}")
    print(f"Win rates: {results.win_rates}")
    print(f"First players: {', '.join(first_players)}")
    if len(unique_first_players) <= 1:
        print("Note: first player did not vary across matches (possible with RNG).")
    print(f"Recordings: {session_dir}")


if __name__ == "__main__":
    main()
