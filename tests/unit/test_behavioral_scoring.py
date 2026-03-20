from __future__ import annotations

from agentdeck.games.examples.fixed_damage.behavioral import (
    EVIDENCE_MAX_EXAMPLES,
    FixedDamageBehavioralScorer,
)
from agentdeck.research.behavioral import compute_behavioral_profile


def _gameplay_event(
    *,
    player: str,
    opponent: str,
    turn_number: int,
    own_hp: int,
    own_potions: int,
    action: str,
    opponent_last_action: str | None,
) -> dict:
    return {
        "type": "gameplay",
        "data": {
            "player": player,
            "action": action,
            "state_before": {
                "health": {player: own_hp, opponent: 80},
                "potions": {player: own_potions, opponent: 3},
                "last_action": {
                    player: None,
                    opponent: opponent_last_action,
                },
                "turn": turn_number,
            },
            "state_after": {
                "health": {player: own_hp, opponent: 80},
                "potions": {player: own_potions - 1 if action == "POTION" else own_potions, opponent: 3},
                "last_action": {
                    player: action,
                    opponent: opponent_last_action,
                },
                "turn": turn_number + 1,
            },
            "turn_context": {
                "turn_number": turn_number,
                "player": player,
            },
            "metadata": {
                "turn_number": turn_number,
            },
        },
    }


def _match_payload(
    *,
    match_id: str,
    first_player: str,
    alpha_action: str,
    beta_action: str,
    winner: str,
    alpha_final_potions: int,
    beta_final_potions: int,
) -> dict:
    second_player = "Beta" if first_player == "Alpha" else "Alpha"
    events = []
    if first_player == "Alpha":
        events.append(
            _gameplay_event(
                player="Alpha",
                opponent="Beta",
                turn_number=1,
                own_hp=80,
                own_potions=3,
                action=alpha_action,
                opponent_last_action=None,
            )
        )
        events.append(
            _gameplay_event(
                player="Beta",
                opponent="Alpha",
                turn_number=2,
                own_hp=80,
                own_potions=3,
                action=beta_action,
                opponent_last_action=alpha_action,
            )
        )
    else:
        events.append(
            _gameplay_event(
                player="Beta",
                opponent="Alpha",
                turn_number=1,
                own_hp=80,
                own_potions=3,
                action=beta_action,
                opponent_last_action=None,
            )
        )
        events.append(
            _gameplay_event(
                player="Alpha",
                opponent="Beta",
                turn_number=2,
                own_hp=80,
                own_potions=3,
                action=alpha_action,
                opponent_last_action=beta_action,
            )
        )

    return {
        "match_id": match_id,
        "game": "FixedDamageGame",
        "players": ["Alpha", "Beta"],
        "winner": winner,
        "final_state": {
            "health": {"Alpha": 80, "Beta": 80},
            "potions": {
                "Alpha": alpha_final_potions,
                "Beta": beta_final_potions,
            },
            "last_action": {"Alpha": alpha_action, "Beta": beta_action},
            "turn": 3,
        },
        "events": events,
        "metadata": {
            "match": {
                "players": ["Alpha", "Beta"],
                "first_player": {"name": first_player},
            },
        },
    }


def _sample_payloads() -> list[dict]:
    return [
        _match_payload(
            match_id="m1",
            first_player="Alpha",
            alpha_action="ATTACK",
            beta_action="ATTACK",
            winner="Alpha",
            alpha_final_potions=3,
            beta_final_potions=3,
        ),
        _match_payload(
            match_id="m2",
            first_player="Alpha",
            alpha_action="ATTACK",
            beta_action="ATTACK",
            winner="Alpha",
            alpha_final_potions=3,
            beta_final_potions=3,
        ),
        _match_payload(
            match_id="m3",
            first_player="Beta",
            alpha_action="POTION",
            beta_action="ATTACK",
            winner="Beta",
            alpha_final_potions=2,
            beta_final_potions=3,
        ),
        _match_payload(
            match_id="m4",
            first_player="Beta",
            alpha_action="POTION",
            beta_action="ATTACK",
            winner="Beta",
            alpha_final_potions=2,
            beta_final_potions=3,
        ),
    ]


def _cross_match_boundary_payloads() -> list[dict]:
    return [
        {
            "match_id": "m1",
            "game": "FixedDamageGame",
            "players": ["Alpha", "Beta"],
            "winner": "Beta",
            "final_state": {
                "health": {"Alpha": 0, "Beta": 20},
                "potions": {"Alpha": 1, "Beta": 1},
                "last_action": {"Alpha": "ATTACK", "Beta": "ATTACK"},
                "turn": 2,
            },
            "events": [
                _gameplay_event(
                    player="Alpha",
                    opponent="Beta",
                    turn_number=1,
                    own_hp=40,
                    own_potions=1,
                    action="ATTACK",
                    opponent_last_action=None,
                )
            ],
            "metadata": {
                "match": {
                    "players": ["Alpha", "Beta"],
                    "first_player": {"name": "Alpha"},
                },
            },
        },
        {
            "match_id": "m2",
            "game": "FixedDamageGame",
            "players": ["Alpha", "Beta"],
            "winner": "Alpha",
            "final_state": {
                "health": {"Alpha": 20, "Beta": 0},
                "potions": {"Alpha": 0, "Beta": 1},
                "last_action": {"Alpha": "POTION", "Beta": "ATTACK"},
                "turn": 2,
            },
            "events": [
                _gameplay_event(
                    player="Alpha",
                    opponent="Beta",
                    turn_number=1,
                    own_hp=40,
                    own_potions=1,
                    action="POTION",
                    opponent_last_action=None,
                )
            ],
            "metadata": {
                "match": {
                    "players": ["Alpha", "Beta"],
                    "first_player": {"name": "Alpha"},
                },
            },
        },
    ]


def _alpha_only_match_payload(
    *,
    match_id: str,
    alpha_position: str,
    own_hp: int,
    own_potions: int,
    action: str,
) -> dict:
    if alpha_position not in {"first", "second"}:
        raise ValueError("alpha_position must be 'first' or 'second'")

    first_player = "Alpha" if alpha_position == "first" else "Beta"
    turn_number = 1 if alpha_position == "first" else 2
    opponent_last_action = None if alpha_position == "first" else "ATTACK"

    return {
        "match_id": match_id,
        "game": "FixedDamageGame",
        "players": ["Alpha", "Beta"],
        "winner": "Alpha",
        "final_state": {
            "health": {"Alpha": own_hp, "Beta": 80},
            "potions": {
                "Alpha": own_potions - 1 if action == "POTION" else own_potions,
                "Beta": 3,
            },
            "last_action": {"Alpha": action, "Beta": opponent_last_action},
            "turn": turn_number + 1,
        },
        "events": [
            _gameplay_event(
                player="Alpha",
                opponent="Beta",
                turn_number=turn_number,
                own_hp=own_hp,
                own_potions=own_potions,
                action=action,
                opponent_last_action=opponent_last_action,
            )
        ],
        "metadata": {
            "match": {
                "players": ["Alpha", "Beta"],
                "first_player": {"name": first_player},
            },
        },
    }


def _evidence_rich_payloads() -> list[dict]:
    payloads: list[dict] = []

    configs = [
        ("s1", 80, 3, ["ATTACK", "ATTACK"], ["POTION", "POTION"]),
        ("s2", 60, 2, ["ATTACK", "ATTACK"], ["ATTACK", "POTION"]),
        ("s3", 40, 1, ["ATTACK", "POTION"], ["ATTACK", "ATTACK"]),
        ("s4", 20, 1, ["ATTACK", "ATTACK"], ["ATTACK", "ATTACK"]),
    ]

    counter = 1
    for state_id, hp, potions, first_actions, second_actions in configs:
        for action in first_actions:
            payloads.append(
                _alpha_only_match_payload(
                    match_id=f"{state_id}_m{counter}",
                    alpha_position="first",
                    own_hp=hp,
                    own_potions=potions,
                    action=action,
                )
            )
            counter += 1
        for action in second_actions:
            payloads.append(
                _alpha_only_match_payload(
                    match_id=f"{state_id}_m{counter}",
                    alpha_position="second",
                    own_hp=hp,
                    own_potions=potions,
                    action=action,
                )
            )
            counter += 1

    return payloads


def test_fixed_damage_behavioral_profile_metrics_with_config() -> None:
    players = [{"name": "Alpha"}, {"name": "Beta"}]
    profile = compute_behavioral_profile(
        players=players,
        match_payloads=_sample_payloads(),
        config={"attack_damage": 20, "max_health": 100},
    )

    assert profile is not None
    assert profile["quality_flags"]["complete"] is True
    assert profile["quality_flags"]["unsupported_metrics"] == []
    assert profile["schema_version"] == 2

    alpha = profile["per_player"]["Alpha"]
    beta = profile["per_player"]["Beta"]

    assert alpha["all_attack_match_rate"]["value"] == 0.5
    assert beta["all_attack_match_rate"]["value"] == 1.0

    assert alpha["first_potion_profile"]["median_first_potion_hp"] == 80.0
    assert alpha["first_potion_profile"]["never_used_rate"] == 0.5
    assert alpha["unused_potions_on_loss_rate"]["value"] == 1.0
    assert alpha["state_action_consistency"]["value"] == 1.0
    assert alpha["position_policy_delta"]["value"] == 1.0

    assert alpha["critical_potion_response_rate"]["critical_hp_threshold"] == 40
    assert alpha["critical_potion_response_rate"]["support_turns"] == 0
    assert alpha["error_recovery_rate"]["support_events"] == 0
    assert alpha["wasted_full_health_potion_rate"]["support_potions"] == 2
    assert alpha["wasted_full_health_potion_rate"]["value"] == 0.0

    assert profile["state_metrics"]["scarcity_action_profile"]["Alpha"]["3"]["potion_count"] == 2
    assert profile["state_metrics"]["action_by_state"]["Alpha"]["position=first|hp=80|potions=3"]["attack_count"] == 2
    assert profile["state_metrics"]["action_by_state"]["Alpha"]["position=second|hp=80|potions=3"]["potion_count"] == 2

    alpha_evidence = profile["evidence"]["per_player"]["Alpha"]
    position_example = alpha_evidence["position_policy_delta"]["examples"][0]
    assert position_example["shared_state_key"] == "hp=80|potions=3"
    assert position_example["delta"] == 1.0
    assert position_example["first"]["source_path"] == (
        "state_metrics.action_by_state.Alpha.position=first|hp=80|potions=3"
    )
    assert position_example["second"]["source_path"] == (
        "state_metrics.action_by_state.Alpha.position=second|hp=80|potions=3"
    )

    consistency_example = alpha_evidence["state_action_consistency"]["examples"][0]
    assert consistency_example["decision_key"] == (
        "position=first|hp=80|potions=3|self=NONE|opp=NONE"
    )
    assert consistency_example["consistency"] == 1.0
    assert consistency_example["support_turns"] == 2
    assert consistency_example["attack_rate"] == 1.0
    assert consistency_example["potion_rate"] == 0.0
    assert consistency_example["dominant_action"] == "ATTACK"


def test_fixed_damage_behavioral_profile_marks_heuristics_unsupported_without_config() -> None:
    players = [{"name": "Alpha"}, {"name": "Beta"}]
    profile = compute_behavioral_profile(
        players=players,
        match_payloads=_sample_payloads(),
        config=None,
    )

    assert profile is not None
    assert profile["quality_flags"]["complete"] is False
    assert profile["quality_flags"]["unsupported_metrics"] == [
        "critical_potion_response_rate",
        "error_recovery_rate",
        "wasted_full_health_potion_rate",
    ]
    assert profile["schema_version"] == 2
    assert profile["per_player"]["Alpha"]["critical_potion_response_rate"] is None
    assert profile["per_player"]["Alpha"]["error_recovery_rate"] is None
    assert profile["per_player"]["Alpha"]["wasted_full_health_potion_rate"] is None
    assert "position_policy_delta" in profile["evidence"]["per_player"]["Alpha"]


def test_fixed_damage_behavioral_scorer_canonical_json_is_stable() -> None:
    scorer = FixedDamageBehavioralScorer()
    first_payload = scorer.score(
        players=[{"name": "Alpha"}, {"name": "Beta"}],
        match_payloads=_sample_payloads(),
        config={"attack_damage": 20, "max_health": 100},
    )
    second_payload = scorer.score(
        players=[{"name": "Alpha"}, {"name": "Beta"}],
        match_payloads=_sample_payloads(),
        config={"attack_damage": 20, "max_health": 100},
    )

    assert scorer.canonical_json(first_payload) == scorer.canonical_json(second_payload)


def test_error_recovery_rate_does_not_cross_match_boundaries() -> None:
    scorer = FixedDamageBehavioralScorer()
    payload = scorer.score(
        players=[{"name": "Alpha"}, {"name": "Beta"}],
        match_payloads=_cross_match_boundary_payloads(),
        config={"attack_damage": 20, "max_health": 100},
    )

    alpha = payload["per_player"]["Alpha"]
    assert alpha["critical_potion_response_rate"]["support_turns"] == 2
    assert alpha["error_recovery_rate"]["missed_events"] == 1
    assert alpha["error_recovery_rate"]["support_events"] == 0
    assert alpha["error_recovery_rate"]["recovered_events"] == 0


def test_behavioral_evidence_is_sorted_and_capped() -> None:
    scorer = FixedDamageBehavioralScorer()
    payload = scorer.score(
        players=[{"name": "Alpha"}, {"name": "Beta"}],
        match_payloads=_evidence_rich_payloads(),
        config={"attack_damage": 20, "max_health": 100},
    )

    alpha_evidence = payload["evidence"]["per_player"]["Alpha"]

    position_examples = alpha_evidence["position_policy_delta"]["examples"]
    assert len(position_examples) == EVIDENCE_MAX_EXAMPLES
    assert [example["shared_state_key"] for example in position_examples] == [
        "hp=80|potions=3",
        "hp=40|potions=1",
        "hp=60|potions=2",
    ]
    assert [example["delta"] for example in position_examples] == [1.0, 0.5, 0.5]

    consistency_examples = alpha_evidence["state_action_consistency"]["examples"]
    assert len(consistency_examples) == EVIDENCE_MAX_EXAMPLES
    assert [example["consistency"] for example in consistency_examples] == [0.5, 0.5, 1.0]
    assert [example["decision_key"] for example in consistency_examples[:2]] == [
        "position=first|hp=40|potions=1|self=NONE|opp=NONE",
        "position=second|hp=60|potions=2|self=NONE|opp=ATTACK",
    ]
    assert consistency_examples[0]["attack_rate"] == 0.5
    assert consistency_examples[0]["potion_rate"] == 0.5
    assert consistency_examples[0]["dominant_action"] is None
    assert consistency_examples[1]["attack_rate"] == 0.5
    assert consistency_examples[1]["potion_rate"] == 0.5
    assert consistency_examples[1]["dominant_action"] is None
    assert consistency_examples[2]["dominant_action"] == "ATTACK"
