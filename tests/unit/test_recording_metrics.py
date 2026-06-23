"""Tests for reusable recording metrics helpers."""

from __future__ import annotations

from agentdeck.research.recording_metrics import (
    compute_format_strictness,
    compute_inferential_statistics,
    compute_position_effect,
)


def test_compute_inferential_statistics_two_player() -> None:
    players = [{"name": "Alice"}, {"name": "Bob"}]
    matches = [
        {"winner": "Alice", "players": ["Alice", "Bob"]},
        {"winner": "Alice", "players": ["Alice", "Bob"]},
        {"winner": "Bob", "players": ["Alice", "Bob"]},
        {"winner": None, "players": ["Alice", "Bob"]},
    ]

    stats = compute_inferential_statistics(players=players, matches=matches)

    assert stats["n_total"] == 4
    assert stats["n_decisive"] == 3
    assert stats["players"]["Alice"]["wins"] == 2
    assert stats["players"]["Bob"]["wins"] == 1
    assert "Alice_vs_Bob" in stats["pairwise_comparisons"]
    comparison = stats["pairwise_comparisons"]["Alice_vs_Bob"]
    assert comparison["comparison_scope"] == "direct_head_to_head"
    assert comparison["wins_a"] == 2
    assert comparison["wins_b"] == 1
    assert comparison["head_to_head_matches"] == 4
    assert comparison["head_to_head_decisive"] == 3


def test_compute_inferential_statistics_pairwise_uses_direct_matches_only() -> None:
    players = [
        {"name": "Alice"},
        {"name": "Bob"},
        {"name": "Carol"},
        {"name": "Dana"},
    ]
    matches = [
        {"winner": "Alice", "players": ["Alice", "Bob"]},
        {"winner": "Bob", "players": ["Bob", "Alice"]},
        {"winner": "Carol", "players": ["Carol", "Dana"]},
        {"winner": "Carol", "players": ["Dana", "Carol"]},
    ]

    stats = compute_inferential_statistics(players=players, matches=matches)
    pairwise = stats["pairwise_comparisons"]

    assert set(pairwise) == {"Alice_vs_Bob", "Carol_vs_Dana"}
    assert pairwise["Alice_vs_Bob"]["wins_a"] == 1
    assert pairwise["Alice_vs_Bob"]["wins_b"] == 1
    assert pairwise["Carol_vs_Dana"]["wins_a"] == 2
    assert pairwise["Carol_vs_Dana"]["wins_b"] == 0


def test_compute_format_strictness_mixed_contracts() -> None:
    match_payloads = [
        {
            "metadata": {
                "player_summaries": [
                    {"name": "Alice", "controller": "ActionOnlyController"},
                    {"name": "Bob", "controller": "ReasoningController"},
                ]
            },
            "events": [
                {
                    "type": "gameplay",
                    "data": {
                        "player": "Alice",
                        "action": {"value": "ATTACK", "metadata": {"parser_success": True}},
                        "interaction": {"response_text": "ACTION: ATTACK"},
                    },
                },
                {
                    "type": "gameplay",
                    "data": {
                        "player": "Bob",
                        "action": {"value": "POTION", "metadata": {"parser_success": True}},
                        "interaction": {"response_text": "REASONING: safe\nACTION: POTION"},
                    },
                },
                {
                    "type": "gameplay",
                    "data": {
                        "player": "Bob",
                        "action": {"value": "POTION", "metadata": {"parser_success": True}},
                        "interaction": {"response_text": "POTION"},
                    },
                },
                {
                    "type": "player_action_parse_failed",
                    "data": {
                        "player": "Alice",
                        "raw_response": "ACTION:",
                    },
                },
            ],
        }
    ]

    strictness = compute_format_strictness(match_payloads)
    alice = strictness["by_player"]["Alice"]
    bob = strictness["by_player"]["Bob"]
    overall = strictness["overall"]

    assert alice["turn_attempts"] == 2
    assert alice["parse_failures"] == 1
    assert alice["strict_contract_passes"] == 1

    assert bob["turn_attempts"] == 2
    assert bob["parse_failures"] == 0
    assert bob["strict_contract_passes"] == 1
    assert bob["recoverable_non_strict"] == 1

    assert overall["turn_attempts"] == 4
    assert overall["parse_failures"] == 1
    assert overall["contract_evaluable_attempts"] == 4
    assert overall["strict_contract_passes"] == 2


def test_compute_position_effect_two_player() -> None:
    players = [{"name": "Alice"}, {"name": "Bob"}]
    matches = [
        {
            "winner": "Alice",
            "players": ["Alice", "Bob"],
            "first_player": {"name": "Alice"},
        },
        {
            "winner": "Alice",
            "players": ["Alice", "Bob"],
            "first_player": {"name": "Bob"},
        },
        {
            "winner": "Bob",
            "players": ["Alice", "Bob"],
            "first_player": {"name": "Bob"},
        },
        {
            "winner": "Bob",
            "players": ["Alice", "Bob"],
            "first_player": {"name": "Alice"},
        },
    ]

    position = compute_position_effect(players=players, matches=matches)
    assert position["total_matches"] == 4
    assert position["first_player_wins"] == 2
    assert position["second_player_wins"] == 2
    assert position["first_player_win_rate"] == 0.5
    assert position["upset_rate"] == 0.5
    assert position["by_player"]["Alice"]["first_count"] == 2
    assert position["by_player"]["Bob"]["first_count"] == 2
