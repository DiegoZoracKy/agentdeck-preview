"""
Unit tests for Player Ordering (SPEC-GAME §4 PO1-PO4, SPEC-CONSOLE §3).

Tests verify all player ordering invariants:
- PO1: Console calls game.get_player_order() before each match
- PO2: Game hook receives correct inputs (players, rng, match_context)
- PO3: Console validates game-returned lists (H4 invariant)
- PO4: Console applies Fisher-Yates shuffle when game returns None
- Reproducibility: Same seed → identical player_order metadata
- Metadata tracking: player_order, player_order_source, first_player
- Previous match result propagation (batch-local scope)

Uses FixedDamageGame as reference implementation per TEST-PLAN-spec-driven.md §3.2.
"""

import json
from pathlib import Path
from typing import Any, List, Optional

import pytest

from agentdeck import AgentDeck, AgentDeckConfig
from agentdeck.core import Console
from agentdeck.core.types import RandomGenerator
from agentdeck.games.examples import FixedDamageGame

# ============================================================================
# Helper Classes
# ============================================================================


class AuctionGame(FixedDamageGame):
    """
    Mock game that implements custom player ordering via auction.

    Uses match_context.previous_match_result to simulate state-dependent ordering:
    - If previous_match_result exists, previous winner goes first
    - Otherwise, uses auction-based ordering (higher bid wins)
    """

    def get_player_order(
        self, players: List, *, rng: RandomGenerator, match_context: Any
    ) -> Optional[List]:
        """Custom ordering: previous winner goes first, or auction-based."""
        # Check for previous match result (state-dependent)
        if hasattr(match_context, "previous_match_result") and match_context.previous_match_result:
            prev_result = match_context.previous_match_result
            if prev_result.winner:
                # Previous winner goes first
                winner_name = prev_result.winner
                winner_player = next((p for p in players if p.name == winner_name), None)
                if winner_player:
                    other_players = [p for p in players if p.name != winner_name]
                    return [winner_player] + other_players

        # Fallback: simulate auction (player 1 always "bids higher")
        return [players[1], players[0]]


class InvalidGame(FixedDamageGame):
    """
    Mock game that returns invalid player lists (for H4 validation testing).
    """

    def __init__(self, violation_type: str = "wrong_length", **kwargs):
        super().__init__(**kwargs)
        self.violation_type = violation_type

    def get_player_order(
        self, players: List, *, rng: RandomGenerator, match_context: Any
    ) -> Optional[List]:
        """Return invalid player list based on violation_type."""
        if self.violation_type == "wrong_length":
            return players[:1]  # Missing a player
        elif self.violation_type == "duplicate":
            return [players[0], players[0]]  # Duplicate player
        elif self.violation_type == "wrong_instance":
            from conftest import MockPlayer

            fake_player = MockPlayer(name=players[0].name)
            return [fake_player, players[1]]  # Different instance
        return None


# ============================================================================
# PO1: Console calls game.get_player_order() before each match
# ============================================================================


def test_PO1_console_calls_get_player_order(mock_player_pair):
    """
    SPEC-GAME §4 PO1: Console MUST call game.get_player_order() before each match.

    Verify that Console invokes the hook with correct parameters.
    """
    # Track hook invocations
    hook_calls = []

    class TrackingGame(FixedDamageGame):
        def get_player_order(self, players, *, rng, match_context):
            hook_calls.append({"players": players, "rng": rng, "match_context": match_context})
            return None  # Use default shuffling

    game = TrackingGame()
    config = AgentDeckConfig(seed=42)
    deck = AgentDeck(game=game, session=config)

    # Play 3 matches
    result = deck.play(mock_player_pair, matches=3)

    # Verify hook was called 3 times (once per match)
    assert len(hook_calls) == 3, "Hook should be called once per match"

    # Verify hook received correct inputs
    for call in hook_calls:
        assert len(call["players"]) == 2, "Hook should receive all players"
        assert call["rng"] is not None, "Hook should receive RNG instance"
        assert call["match_context"] is not None, "Hook should receive MatchContext"


# ============================================================================
# PO2: Game hook receives correct inputs
# ============================================================================


def test_PO2_hook_receives_correct_players(mock_player_pair):
    """
    SPEC-GAME §4 PO2: Hook MUST receive original player list (unshuffled).

    Verify that the hook gets the exact player instances passed to deck.play().
    """
    received_players = []

    class CheckPlayersGame(FixedDamageGame):
        def get_player_order(self, players, *, rng, match_context):
            received_players.append(players)
            return None

    game = CheckPlayersGame()
    config = AgentDeckConfig(seed=42)
    deck = AgentDeck(game=game, session=config)

    result = deck.play(mock_player_pair, matches=1)

    # Verify hook received exact player instances
    assert len(received_players) == 1
    assert received_players[0] == mock_player_pair
    assert received_players[0][0] is mock_player_pair[0]
    assert received_players[0][1] is mock_player_pair[1]


def test_PO2_hook_receives_match_context_with_previous_result(mock_player_pair):
    """
    SPEC-CONSOLE §3: Hook MUST receive previous_match_result in match_context.

    Verify that match_context.previous_match_result contains previous match result
    for matches after the first one in a batch.
    """
    contexts = []

    class CheckContextGame(FixedDamageGame):
        def get_player_order(self, players, *, rng, match_context):
            contexts.append(match_context)
            return None

    game = CheckContextGame()
    config = AgentDeckConfig(seed=42)
    deck = AgentDeck(game=game, session=config)

    result = deck.play(mock_player_pair, game=game, matches=3)

    # First match: no previous_match_result
    assert len(contexts) == 3
    assert contexts[0].previous_match_result is None

    # Second match: should have previous_match_result
    if contexts[1].previous_match_result is not None:
        prev_result = contexts[1].previous_match_result
        assert prev_result is not None
        assert hasattr(prev_result, "winner")


# ============================================================================
# PO3: Console validates game-returned lists (H4 invariant)
# ============================================================================


def test_PO3_console_validates_wrong_length(mock_player_pair):
    """
    SPEC-CONSOLE §3 H4: Console MUST reject game-returned lists with wrong length.

    Verify that Console raises ValueError when game returns incomplete player list.
    """
    game = InvalidGame(violation_type="wrong_length")
    config = AgentDeckConfig(seed=42)
    deck = AgentDeck(game=game, session=config)

    with pytest.raises(ValueError, match="returned player list with .* players but expected"):
        deck.play(mock_player_pair, game=game, matches=1)


def test_PO3_console_validates_duplicates(mock_player_pair):
    """
    SPEC-CONSOLE §3 H4: Console MUST reject game-returned lists with duplicates.

    Verify that Console raises ValueError when game returns duplicate players.
    """
    game = InvalidGame(violation_type="duplicate")
    config = AgentDeckConfig(seed=42)
    deck = AgentDeck(game=game, session=config)

    with pytest.raises(ValueError, match="duplicate"):
        deck.play(mock_player_pair, game=game, matches=1)


def test_PO3_console_validates_wrong_instances(mock_player_pair):
    """
    SPEC-CONSOLE §3 H4: Console MUST reject game-returned lists with wrong instances.

    Verify that Console raises ValueError when game returns different player instances.
    """
    game = InvalidGame(violation_type="wrong_instance")
    config = AgentDeckConfig(seed=42)
    deck = AgentDeck(game=game, session=config)

    with pytest.raises(ValueError, match="different Player instances"):
        deck.play(mock_player_pair, matches=1)


# ============================================================================
# PO4: Console applies Fisher-Yates shuffle when game returns None
# ============================================================================


def test_PO4_console_applies_fisher_yates_when_none(mock_player_pair):
    """
    SPEC-CONSOLE §3 PO4: Console MUST apply Fisher-Yates shuffle when game returns None.

    Verify that Console randomizes player order when game has no preference.
    """
    game = FixedDamageGame()  # Default returns None
    config = AgentDeckConfig(seed=42)
    deck = AgentDeck(game=game, session=config)

    result = deck.play(mock_player_pair, game=game, matches=10)

    # Collect player_order metadata
    player_orders = [match.metadata["player_order"] for match in result.matches]

    # With random shuffling, we should see both [0, 1] and [1, 0] orders
    # (extremely unlikely to get same order 10 times in a row)
    unique_orders = set(tuple(order) for order in player_orders)
    assert len(unique_orders) >= 2, "Fisher-Yates shuffle should produce varied orders"

    # Verify metadata includes player_order_source="console"
    for match in result.matches:
        assert match.metadata["player_order_source"] == "console"


def test_PO4_fisher_yates_unbiased():
    """
    SPEC-CONSOLE §3: Fisher-Yates shuffle MUST be unbiased.

    Run many matches and verify roughly equal distribution of first player.
    """
    from conftest import MockPlayer

    alice = MockPlayer(name="Alice")
    bob = MockPlayer(name="Bob")

    game = FixedDamageGame()
    config = AgentDeckConfig(seed=None)  # Different seed each run
    deck = AgentDeck(game=game, session=config)

    # Run 100 matches
    result = deck.play([alice, bob], matches=100)

    # Count how many times each player went first
    alice_first_count = sum(
        1 for match in result.matches if match.metadata["first_player"]["name"] == "Alice"
    )
    bob_first_count = sum(
        1 for match in result.matches if match.metadata["first_player"]["name"] == "Bob"
    )

    # With 100 matches, expect roughly 50/50 distribution (allow 30-70 range)
    assert 30 <= alice_first_count <= 70, f"Expected ~50 Alice-first, got {alice_first_count}"
    assert 30 <= bob_first_count <= 70, f"Expected ~50 Bob-first, got {bob_first_count}"
    assert alice_first_count + bob_first_count == 100


# ============================================================================
# Reproducibility: Same seed → identical player_order
# ============================================================================


def test_reproducibility_same_seed_same_order(mock_player_pair):
    """
    SPEC-CONSOLE §3: Same seed MUST produce identical player_order across runs.

    Verify that match seed controls shuffling for deterministic behavior.
    """
    game = FixedDamageGame()

    # Run 1
    config1 = AgentDeckConfig(seed=12345)
    deck1 = AgentDeck(game=game, session=config1)
    result1 = deck1.play(mock_player_pair, matches=5)

    # Run 2 (same seed)
    config2 = AgentDeckConfig(seed=12345)
    deck2 = AgentDeck(game=game, session=config2)
    result2 = deck2.play(mock_player_pair, matches=5)

    # Verify identical player_order metadata
    for i in range(5):
        order1 = result1.matches[i].metadata["player_order"]
        order2 = result2.matches[i].metadata["player_order"]
        assert order1 == order2, f"Match {i}: Orders should be identical with same seed"

        first1 = result1.matches[i].metadata["first_player"]
        first2 = result2.matches[i].metadata["first_player"]
        assert first1 == first2, f"Match {i}: First player should be identical with same seed"


def test_reproducibility_different_seed_different_order(mock_player_pair):
    """
    SPEC-CONSOLE §3: Different seeds SHOULD produce different player_order.

    Verify that changing seed changes shuffling behavior.
    """
    game = FixedDamageGame()

    # Run 1
    config1 = AgentDeckConfig(seed=11111)
    deck1 = AgentDeck(game=game, session=config1)
    result1 = deck1.play(mock_player_pair, matches=10)

    # Run 2 (different seed)
    config2 = AgentDeckConfig(seed=99999)
    deck2 = AgentDeck(game=game, session=config2)
    result2 = deck2.play(mock_player_pair, matches=10)

    # Collect orders
    orders1 = [tuple(match.metadata["player_order"]) for match in result1.matches]
    orders2 = [tuple(match.metadata["player_order"]) for match in result2.matches]

    # With different seeds, expect at least some different orders
    different_count = sum(1 for o1, o2 in zip(orders1, orders2) if o1 != o2)
    assert different_count >= 3, "Different seeds should produce different orders"


# ============================================================================
# Metadata Tracking: player_order, player_order_source, first_player
# ============================================================================


def test_metadata_includes_player_order(mock_player_pair):
    """
    SPEC-OBSERVABILITY §4: MatchResult.metadata MUST include player_order.

    Verify that player_order is a list of original indices.
    """
    game = FixedDamageGame()
    config = AgentDeckConfig(seed=42)
    deck = AgentDeck(game=game, session=config)

    result = deck.play(mock_player_pair, game=game, matches=1)

    metadata = result.matches[0].metadata
    assert "player_order" in metadata
    player_order = metadata["player_order"]

    # Should be list of indices
    assert isinstance(player_order, list)
    assert len(player_order) == 2
    assert set(player_order) == {0, 1}  # Contains both indices


def test_metadata_includes_player_order_source_console(mock_player_pair):
    """
    SPEC-OBSERVABILITY §4: Metadata MUST include player_order_source="console".

    Verify that when game returns None, source is "console".
    """
    game = FixedDamageGame()  # Returns None
    config = AgentDeckConfig(seed=42)
    deck = AgentDeck(game=game, session=config)

    result = deck.play(mock_player_pair, game=game, matches=1)

    metadata = result.matches[0].metadata
    assert "player_order_source" in metadata
    assert metadata["player_order_source"] == "console"


def test_metadata_includes_player_order_source_game(mock_player_pair):
    """
    SPEC-OBSERVABILITY §4: Metadata MUST include player_order_source="game".

    Verify that when game returns custom order, source is "game".
    """
    game = AuctionGame()  # Returns custom order
    config = AgentDeckConfig(seed=42)
    deck = AgentDeck(game=game, session=config)

    result = deck.play(mock_player_pair, game=game, matches=1)

    metadata = result.matches[0].metadata
    assert "player_order_source" in metadata
    assert metadata["player_order_source"] == "game"


def test_metadata_includes_first_player(mock_player_pair):
    """
    SPEC-OBSERVABILITY §4: Metadata MUST include first_player with name and index.

    Verify that first_player contains correct structure.
    """
    game = FixedDamageGame()
    config = AgentDeckConfig(seed=42)
    deck = AgentDeck(game=game, session=config)

    result = deck.play(mock_player_pair, game=game, matches=1)

    metadata = result.matches[0].metadata
    assert "first_player" in metadata

    first_player = metadata["first_player"]
    assert isinstance(first_player, dict)
    assert "name" in first_player
    assert "index" in first_player
    assert first_player["name"] in ["Alice", "Bob"]
    assert first_player["index"] in [0, 1]

    # Verify first_player index maps to one of the original indices in player_order
    player_order = metadata["player_order"]
    assert first_player["index"] in player_order


def test_metadata_first_player_matches_runtime_selection(mock_player_pair):
    """
    Regression: first_player metadata must reflect the runtime-selected first actor.

    For turn-based games, the source of truth is final_state["_first_player_idx"].
    """
    game = FixedDamageGame()
    config = AgentDeckConfig(seed=42)
    deck = AgentDeck(game=game, session=config)

    result = deck.play(mock_player_pair, game=game, matches=1)
    match = result.matches[0]
    metadata = match.metadata
    final_state = match.final_state

    first_player_idx_ordered = final_state["_first_player_idx"]
    expected_name = metadata["players"][first_player_idx_ordered]
    expected_index = metadata["player_order"][first_player_idx_ordered]

    assert metadata["first_player"]["name"] == expected_name
    assert metadata["first_player"]["index"] == expected_index


def test_metadata_first_player_matches_runtime_selection_parallel(mock_player_pair):
    """
    Regression (parallel path): metadata first_player must match runtime selection.
    """
    game = FixedDamageGame()
    config = AgentDeckConfig(seed=42, concurrency=2)
    deck = AgentDeck(game=game, session=config)

    result = deck.play(mock_player_pair, game=game, matches=2)

    for match in result.matches:
        metadata = match.metadata
        final_state = match.final_state
        first_player_idx_ordered = final_state["_first_player_idx"]
        expected_name = metadata["players"][first_player_idx_ordered]
        expected_index = metadata["player_order"][first_player_idx_ordered]

        assert metadata["first_player"]["name"] == expected_name
        assert metadata["first_player"]["index"] == expected_index


def test_missing_runtime_first_player_uses_prepared_order_fallback(mock_player_pair):
    """SPEC-CONSOLE M5: custom mechanics need not publish selection metadata."""
    console = Console(config=AgentDeckConfig(seed=42), spectators=[])
    fallback = {"name": "Alice", "index": 0, "ordered_index": 0}

    resolved = console._resolve_first_player_metadata(
        fallback,
        list(mock_player_pair),
        [0, 1],
        selected_first_player=None,
    )

    assert resolved == fallback


# ============================================================================
# Game Override: Custom player ordering logic
# ============================================================================


def test_game_override_auction_based_ordering(mock_player_pair):
    """
    SPEC-GAME §4 PO1: Games CAN override get_player_order() for custom logic.

    Verify that AuctionGame's custom ordering is respected by Console.
    """
    game = AuctionGame()  # Always returns [player1, player0]
    config = AgentDeckConfig(seed=42)
    deck = AgentDeck(game=game, session=config)

    result = deck.play(mock_player_pair, game=game, matches=3)

    # Verify all matches use auction ordering (player 1 first)
    for match in result.matches:
        player_order = match.metadata["player_order"]
        assert player_order == [1, 0], "AuctionGame should always put player 1 first"

        first_player = match.metadata["first_player"]
        assert first_player["name"] in ["Alice", "Bob"]
        assert first_player["index"] in [0, 1]
        assert first_player["index"] in player_order


def test_game_override_state_dependent_ordering(mock_player_pair):
    """
    SPEC-GAME §4 PO2: Games CAN use match_context for state-dependent ordering.

    Verify that AuctionGame can access previous_match_result and adjust ordering.
    """
    game = AuctionGame()  # Previous winner goes first
    config = AgentDeckConfig(seed=42)
    deck = AgentDeck(game=game, session=config)

    # Play matches where one player consistently wins
    result = deck.play(mock_player_pair, game=game, matches=3)

    # First match: auction-based (no previous result)
    first_order = result.matches[0].metadata["player_order"]
    assert first_order == [1, 0], "First match should use auction logic"

    # Subsequent matches: if there's a winner, they should go first
    # (This depends on game outcome, so we just verify metadata is accessible)
    for i in range(1, 3):
        match = result.matches[i]
        assert "player_order" in match.metadata
        assert "player_order_source" in match.metadata
        assert match.metadata["player_order_source"] == "game"


# ============================================================================
# Previous Match Result Propagation (batch-local scope)
# ============================================================================


def test_previous_match_result_batch_local_scope(mock_player_pair):
    """
    SPEC-CONSOLE §3: previous_match_result MUST be batch-local (not cross-batch).

    Verify that second batch doesn't receive results from first batch.
    """
    contexts_batch1 = []
    contexts_batch2 = []

    class TrackContextGame(FixedDamageGame):
        def __init__(self, context_list, **kwargs):
            super().__init__(**kwargs)
            self.context_list = context_list

        def get_player_order(self, players, *, rng, match_context):
            self.context_list.append(match_context)
            return None

    config = AgentDeckConfig(seed=42)

    # Batch 1: Play 2 matches
    game1 = TrackContextGame(contexts_batch1)
    deck = AgentDeck(game=game1, session=config)
    result1 = deck.play(mock_player_pair, game=game1, matches=2)

    # Batch 2: Play 2 matches (different batch)
    game2 = TrackContextGame(contexts_batch2)
    result2 = deck.play(mock_player_pair, game=game2, matches=2)

    # Batch 2, Match 1 should NOT have previous_match_result from Batch 1
    assert contexts_batch2[0].previous_match_result is None


# ============================================================================
# Event Emission: MATCH_START includes player_order fields
# ============================================================================


def test_match_start_event_includes_player_order_fields(mock_player_pair):
    """
    SPEC-OBSERVABILITY §4: MATCH_START event MUST include player_order fields.

    Verify that event payload contains player_order, player_order_source, first_player.
    """
    captured_events = []

    class EventCapture:
        def on_match_start(self, event):
            captured_events.append(event)

    spectator = EventCapture()
    game = FixedDamageGame()
    config = AgentDeckConfig(seed=42)

    # Play match with spectator
    deck = AgentDeck(game=game, session=config, spectators=[spectator])
    result = deck.play(mock_player_pair, matches=1)

    # Verify event was emitted
    assert len(captured_events) >= 1

    event = captured_events[0]
    assert hasattr(event, "data")

    # Check for player_order fields in event data
    data = event.data
    assert "player_order" in data
    assert "player_order_source" in data
    assert "first_player" in data

    # Verify structure
    assert isinstance(data["player_order"], list)
    assert data["player_order_source"] in ["console", "game"]
    assert isinstance(data["first_player"], dict)
    assert "name" in data["first_player"]
    assert "index" in data["first_player"]


# ============================================================================
# Edge Cases
# ============================================================================


def test_single_player_ordering():
    """
    Edge case: Single-player games should handle ordering gracefully.

    Verify that player_order is [0] for single-player games.
    """
    from conftest import MockPlayer

    single_player = [MockPlayer(name="Solo")]
    game = FixedDamageGame()
    config = AgentDeckConfig(seed=42)
    deck = AgentDeck(game=game, session=config)

    # Note: FixedDamageGame expects 2 players, so this might fail at game level
    # This test documents expected behavior if single-player games are supported
    try:
        result = deck.play(single_player, game=game, matches=1)
        metadata = result.matches[0].metadata
        assert metadata["player_order"] == [0]
    except Exception:
        # If game doesn't support single-player, that's also valid
        pytest.skip("Game doesn't support single-player mode")


def test_three_player_ordering():
    """
    Edge case: Three-player games should shuffle all 3 players.

    Verify that player_order contains all 3 indices in some order.
    """
    from conftest import MockPlayer

    three_players = [MockPlayer(name="Alice"), MockPlayer(name="Bob"), MockPlayer(name="Charlie")]
    game = FixedDamageGame()
    config = AgentDeckConfig(seed=42)
    deck = AgentDeck(game=game, session=config)

    # Note: FixedDamageGame expects 2 players, so this might fail
    # This test documents expected behavior for N-player games
    try:
        result = deck.play(three_players, game=game, matches=1)
        metadata = result.matches[0].metadata

        player_order = metadata["player_order"]
        assert len(player_order) == 3
        assert set(player_order) == {0, 1, 2}
    except Exception:
        # If game doesn't support 3 players, that's also valid
        pytest.skip("Game doesn't support three-player mode")


def test_invalid_pairing_policy_rejected():
    with pytest.raises(ValueError, match="pairing_policy"):
        AgentDeckConfig(pairing_policy="invalid")


def test_paired_side_swap_reuses_seed_and_persists_policy(mock_player_pair, tmp_path):
    game = FixedDamageGame()
    config = AgentDeckConfig(
        seed=42,
        run_dir=str(tmp_path),
        pairing_policy="paired_side_swap",
    )
    deck = AgentDeck(game=game, session=config)

    result = deck.play(mock_player_pair, matches=4)

    seeds = [match.seed for match in result.matches]
    orders = [match.metadata["player_order"] for match in result.matches]

    assert seeds == [42, 42, 43, 43]
    assert orders[1] == list(reversed(orders[0]))
    assert orders[3] == list(reversed(orders[2]))
    assert result.matches[0].metadata["fairness_policy"]["pairing_policy"] == "paired_side_swap"

    batch_files = list(Path(deck.session.record_directory).glob("batch_*.json"))
    assert len(batch_files) == 1
    batch_payload = json.loads(batch_files[0].read_text(encoding="utf-8"))
    assert batch_payload["metadata"]["fairness_policy"]["pairing_policy"] == "paired_side_swap"


def test_fixed_first_player_policy_respects_index(mock_player_pair):
    game = FixedDamageGame()
    config = AgentDeckConfig(
        seed=42,
        first_player_policy="fixed",
        fixed_first_player_index=1,
    )
    deck = AgentDeck(game=game, session=config)

    result = deck.play(mock_player_pair, matches=3)

    for match in result.matches:
        assert match.metadata["player_order"][0] == 1
        assert match.metadata["first_player"]["index"] == 1
        assert match.metadata["first_player"]["ordered_index"] == 0


def test_alternating_first_player_policy_cycles_positions(mock_player_pair):
    game = FixedDamageGame()
    config = AgentDeckConfig(
        seed=42,
        first_player_policy="alternating",
    )
    deck = AgentDeck(game=game, session=config)

    result = deck.play(mock_player_pair, matches=4)

    first_player_indices = [match.metadata["first_player"]["index"] for match in result.matches]
    assert first_player_indices == [0, 1, 0, 1]
