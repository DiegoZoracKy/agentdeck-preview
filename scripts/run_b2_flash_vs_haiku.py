#!/usr/bin/env python3
"""
Run B2 cell c03: FixedDamage — gemini-2.5-flash AO vs claude-haiku-4-5-20251001 AO
N=24, paired seed side-swap (12 seeds x 2 positions), concurrency=5.

Usage:
  python scripts/run_b2_flash_vs_haiku.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agentdeck import AgentDeck, AgentDeckConfig
from agentdeck.controllers import ActionOnlyController
from agentdeck.core.prompt_builder import PromptBuilder
from agentdeck.games.examples import FixedDamageGame
from agentdeck.players import ClaudePlayer
from agentdeck.players.google_player import GeminiPlayer
from agentdeck.spectators import ProgressDisplay, StatsTracker, TokenUsageTracker
from agentdeck.core.types import LogLevel

SEED_BASE = 427000
MATCHES = 24
CONCURRENCY = 5

GAME_CONFIG = dict(
    max_health=100,
    attack_damage=20,
    potion_heal=30,
    starting_potions=2,
    information_level="partial",
)

# Same custom handshake template used in c01 (proven to work with these models)
HANDSHAKE_TEMPLATE = (
    "{game_instructions}\n\n"
    "Use the response format below on gameplay turns:\n"
    "ACTION: [Your chosen action]\n"
    "Allowed actions are defined by the game instructions above.\n\n"
    "Reply with exactly this single token and nothing else: OK"
)


def build_players():
    controller = ActionOnlyController()
    flash = GeminiPlayer(
        name="gemini-2.5-flash-A",
        model="gemini-2.5-flash",
        controller=controller,
        temperature=1.0,
        handshake_template=HANDSHAKE_TEMPLATE,
    )
    haiku = ClaudePlayer(
        name="claude-haiku-4-5-20251001-B",
        model="claude-haiku-4-5-20251001",
        controller=controller,
        temperature=1.0,
        max_tokens=8192,
        handshake_template=HANDSHAKE_TEMPLATE,
    )
    return flash, haiku


def main():
    missing = []
    if not os.getenv("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if not os.getenv("VERTEX_PROJECT_ID"):
        missing.append("VERTEX_PROJECT_ID")
    if missing:
        print(f"Error: missing env vars: {', '.join(missing)}")
        sys.exit(1)

    game = FixedDamageGame(**GAME_CONFIG)
    flash, haiku = build_players()

    config = AgentDeckConfig(
        seed=SEED_BASE,
        concurrency=CONCURRENCY,
        log_level=LogLevel.INFO,
    )

    print("=== B2 c03: gemini-2.5-flash AO vs claude-haiku-4-5-20251001 AO ===")
    print(f"Matches: {MATCHES} | Seed base: {SEED_BASE} | Concurrency: {CONCURRENCY}")
    print()

    deck = None
    try:
        with AgentDeck(game=game, session=config, spectators=[ProgressDisplay(), StatsTracker(), TokenUsageTracker()]) as deck:
            results = deck.play(players=[flash, haiku], matches=MATCHES, seed=SEED_BASE)
            session_id = deck.session.session_id
    except Exception as exc:
        session_id = deck.session.session_id if deck else "unknown"
        print(f"\n=== FAILED === session={session_id} error={exc}")
        raise

    print("\n=== Results ===")
    print(f"Win rates: {results.win_rates}")
    print(f"Session: agentdeck_runs/{session_id}")

    first_wins = sum(
        1 for m in results.matches
        if m.winner and m.metadata.get("first_player", {}).get("name") == m.winner
    )
    print(f"First-player wins: {first_wins}/{len(results.matches)}")


if __name__ == "__main__":
    main()
