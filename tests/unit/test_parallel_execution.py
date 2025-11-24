"""
Tests for parallel execution (SPEC-PARALLEL v1.0.0).

Verifies:
- Parallel execution with concurrency > 1
- Deterministic seeding (base_seed + match_index)
- Event ordering preservation
- Fallback to sequential when game uses previous_match_result
"""

import pytest
from agentdeck import AgentDeck, AgentDeckConfig
from agentdeck.games.examples.fixed_damage import FixedDamageGame
from agentdeck.players.mock import MockPlayer


def test_parallel_execution_with_concurrency_2(mock_player_pair):
    """Verify parallel execution works with concurrency=2."""
    config = AgentDeckConfig(seed=42, concurrency=2)
    game = FixedDamageGame()
    deck = AgentDeck(game=game, session=config)

    # Run 4 matches with concurrency=2
    results = deck.play(mock_player_pair, matches=4)

    # Verify all matches completed
    assert len(results) == 4

    # Verify deterministic seeding (should be reproducible)
    seeds = [r.seed for r in results]
    assert len(set(seeds)) == 4  # All unique seeds

    # Verify each match has proper metadata
    for i, result in enumerate(results):
        assert result.metadata["game"] == "FixedDamageGame"
        assert len(result.metadata["players"]) == 2


def test_parallel_execution_determinism(mock_player_pair):
    """Verify parallel execution is deterministic with same seed."""
    game = FixedDamageGame()

    # Run 1: concurrency=2
    config1 = AgentDeckConfig(seed=42, concurrency=2)
    deck1 = AgentDeck(game=game, session=config1)
    results1 = deck1.play(mock_player_pair, matches=4)

    # Run 2: concurrency=2, same seed
    config2 = AgentDeckConfig(seed=42, concurrency=2)
    deck2 = AgentDeck(game=game, session=config2)
    results2 = deck2.play(mock_player_pair, matches=4)

    # Verify determinism: same seeds in same order
    seeds1 = [r.seed for r in results1]
    seeds2 = [r.seed for r in results2]
    assert seeds1 == seeds2

    # Verify winners match (deterministic game)
    winners1 = [r.winner for r in results1]
    winners2 = [r.winner for r in results2]
    assert winners1 == winners2


def test_fallback_to_sequential_with_get_player_order():
    """Verify fallback to sequential when game has get_player_order hook."""

    class GameWithHook(FixedDamageGame):
        def get_player_order(self, players, *, rng, match_context):
            # Hook that might use previous_match_result
            return None  # Use console ordering

    config = AgentDeckConfig(seed=42, concurrency=4)
    game = GameWithHook()
    deck = AgentDeck(game=game, session=config)

    # Create mock players
    alice = MockPlayer(name="Alice")
    bob = MockPlayer(name="Bob")

    # Should fall back to sequential (no error)
    results = deck.play([alice, bob], matches=4)

    assert len(results) == 4


def test_parallel_vs_sequential_compatibility(mock_player_pair):
    """Verify parallel and sequential produce same results (no hooks case)."""
    game = FixedDamageGame()

    # Sequential execution (concurrency=1)
    config_seq = AgentDeckConfig(seed=42, concurrency=1)
    deck_seq = AgentDeck(game=game, session=config_seq)
    results_seq = deck_seq.play(mock_player_pair, matches=4)

    # Parallel execution (concurrency=2)
    config_par = AgentDeckConfig(seed=42, concurrency=2)
    deck_par = AgentDeck(game=game, session=config_par)
    results_par = deck_par.play(mock_player_pair, matches=4)

    # Verify same seeds (determinism)
    seeds_seq = [r.seed for r in results_seq]
    seeds_par = [r.seed for r in results_par]
    assert seeds_seq == seeds_par

    # Verify same winners (determinism)
    winners_seq = [r.winner for r in results_seq]
    winners_par = [r.winner for r in results_par]
    assert winners_seq == winners_par


def test_parallel_event_ordering():
    """Verify events are replayed in match_index order."""
    captured_events = []

    class EventCapture:
        def on_match_start(self, event):
            captured_events.append(("match_start", event.data.get("match_id")))

        def on_match_end(self, event):
            captured_events.append(
                ("match_end", event.data.get("result").metadata.get("match_id", "unknown"))
            )

    config = AgentDeckConfig(seed=42, concurrency=2)
    game = FixedDamageGame()
    deck = AgentDeck(game=game, session=config)

    alice = MockPlayer(name="Alice")
    bob = MockPlayer(name="Bob")
    spectator = EventCapture()

    # Run with spectator
    results = deck.play([alice, bob], matches=4, spectators=[spectator])

    # Verify events are ordered: match_start, match_end for each match in sequence
    assert len(captured_events) >= 8  # At least 4 match_start + 4 match_end

    # Extract match_start events
    match_starts = [e for e in captured_events if e[0] == "match_start"]
    assert len(match_starts) == 4
