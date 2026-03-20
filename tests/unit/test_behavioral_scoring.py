from __future__ import annotations

from agentdeck.games.examples.fixed_damage.behavioral import (
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
    assert profile["per_player"]["Alpha"]["critical_potion_response_rate"] is None
    assert profile["per_player"]["Alpha"]["error_recovery_rate"] is None
    assert profile["per_player"]["Alpha"]["wasted_full_health_potion_rate"] is None


def test_fixed_damage_behavioral_scorer_canonical_json_is_stable() -> None:
    scorer = FixedDamageBehavioralScorer()
    payload = scorer.score(
        players=[{"name": "Alpha"}, {"name": "Beta"}],
        match_payloads=_sample_payloads(),
        config={"attack_damage": 20, "max_health": 100},
    )

    assert scorer.canonical_json(payload) == scorer.canonical_json(payload)
