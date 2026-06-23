from __future__ import annotations

import json
import sys
from pathlib import Path

from agentdeck.games.examples.variable_damage.behavioral import (
    EVIDENCE_MAX_EXAMPLES,
    VariableDamageBehavioralScorer,
)
from agentdeck.research.behavioral import compute_behavioral_profile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _variable_gameplay_event(
    *,
    player: str,
    opponent: str,
    turn_number: int,
    own_hp: int,
    own_potions: int,
    action: str,
    opponent_last_action: str | None,
    opponent_hp_before: int = 80,
    attack_damage: int = 20,
    potion_heal: int = 30,
    max_health: int = 100,
) -> dict:
    if action == "ATTACK":
        own_hp_after = own_hp
        own_potions_after = own_potions
        opponent_hp_after = max(0, opponent_hp_before - attack_damage)
    elif action == "POTION":
        own_hp_after = min(max_health, own_hp + potion_heal) if own_potions > 0 else own_hp
        own_potions_after = own_potions - 1 if own_potions > 0 else own_potions
        opponent_hp_after = opponent_hp_before
    else:
        raise ValueError(f"Unsupported action {action}")

    return {
        "type": "gameplay",
        "data": {
            "player": player,
            "action": {"value": action, "reasoning": None, "metadata": {}},
            "state_before": {
                "health": {player: own_hp, opponent: opponent_hp_before},
                "potions": {player: own_potions, opponent: 3},
                "last_action": {
                    player: None,
                    opponent: opponent_last_action,
                },
                "turn": turn_number,
            },
            "state_after": {
                "health": {player: own_hp_after, opponent: opponent_hp_after},
                "potions": {player: own_potions_after, opponent: 3},
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
        },
    }


def _alpha_only_variable_match_payload(
    *,
    match_id: str,
    alpha_position: str,
    own_hp: int,
    own_potions: int,
    action: str,
    winner: str,
    alpha_final_potions: int,
) -> dict:
    if alpha_position not in {"first", "second"}:
        raise ValueError("alpha_position must be 'first' or 'second'")

    first_player = "Alpha" if alpha_position == "first" else "Beta"
    turn_number = 1 if alpha_position == "first" else 2
    opponent_last_action = None if alpha_position == "first" else "ATTACK"

    return {
        "match_id": match_id,
        "game": "VariableDamageGame",
        "players": ["Alpha", "Beta"],
        "winner": winner,
        "final_state": {
            "health": {"Alpha": own_hp, "Beta": 80},
            "potions": {
                "Alpha": alpha_final_potions,
                "Beta": 3,
            },
            "last_action": {"Alpha": action, "Beta": opponent_last_action},
            "turn": turn_number + 1,
        },
        "events": [
            _variable_gameplay_event(
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


def _variable_sample_payloads() -> list[dict]:
    payloads: list[dict] = []

    for suffix in ("a", "b"):
        payloads.append(
            _alpha_only_variable_match_payload(
                match_id=f"first80_{suffix}",
                alpha_position="first",
                own_hp=80,
                own_potions=3,
                action="ATTACK",
                winner="Alpha",
                alpha_final_potions=3,
            )
        )
        payloads.append(
            _alpha_only_variable_match_payload(
                match_id=f"second80_{suffix}",
                alpha_position="second",
                own_hp=80,
                own_potions=3,
                action="POTION",
                winner="Beta",
                alpha_final_potions=2,
            )
        )
        payloads.append(
            _alpha_only_variable_match_payload(
                match_id=f"first20_{suffix}",
                alpha_position="first",
                own_hp=20,
                own_potions=1,
                action="POTION",
                winner="Alpha",
                alpha_final_potions=0,
            )
        )
        payloads.append(
            _alpha_only_variable_match_payload(
                match_id=f"second20_{suffix}",
                alpha_position="second",
                own_hp=20,
                own_potions=1,
                action="ATTACK",
                winner="Beta",
                alpha_final_potions=1,
            )
        )
        payloads.append(
            _alpha_only_variable_match_payload(
                match_id=f"first40_{suffix}",
                alpha_position="first",
                own_hp=40,
                own_potions=2,
                action="POTION",
                winner="Alpha",
                alpha_final_potions=1,
            )
        )
        payloads.append(
            _alpha_only_variable_match_payload(
                match_id=f"second40_{suffix}",
                alpha_position="second",
                own_hp=40,
                own_potions=2,
                action="ATTACK",
                winner="Beta",
                alpha_final_potions=2,
            )
        )

    return payloads


def _high_roll_recovery_payloads() -> list[dict]:
    def build(match_id: str, alpha_action: str) -> dict:
        beta_attack = _variable_gameplay_event(
            player="Beta",
            opponent="Alpha",
            turn_number=1,
            own_hp=80,
            own_potions=3,
            action="ATTACK",
            opponent_last_action=None,
            opponent_hp_before=40,
            attack_damage=20,
        )
        alpha_follow_up = _variable_gameplay_event(
            player="Alpha",
            opponent="Beta",
            turn_number=2,
            own_hp=20,
            own_potions=1,
            action=alpha_action,
            opponent_last_action="ATTACK",
        )
        alpha_final_potions = 0 if alpha_action == "POTION" else 1

        return {
            "match_id": match_id,
            "game": "VariableDamageGame",
            "players": ["Alpha", "Beta"],
            "winner": "Alpha" if alpha_action == "POTION" else "Beta",
            "final_state": {
                "health": {
                    "Alpha": 50 if alpha_action == "POTION" else 20,
                    "Beta": 80,
                },
                "potions": {"Alpha": alpha_final_potions, "Beta": 3},
                "last_action": {"Alpha": alpha_action, "Beta": "ATTACK"},
                "turn": 3,
            },
            "events": [beta_attack, alpha_follow_up],
            "metadata": {
                "match": {
                    "players": ["Alpha", "Beta"],
                    "first_player": {"name": "Beta"},
                },
            },
        }

    return [build("recover_yes", "POTION"), build("recover_no", "ATTACK")]


def test_variable_damage_behavioral_profile_metrics_with_config() -> None:
    players = [{"name": "Alpha"}, {"name": "Beta"}]
    profile = compute_behavioral_profile(
        players=players,
        match_payloads=_variable_sample_payloads(),
        config={
            "min_attack_damage": 15,
            "max_attack_damage": 25,
            "potion_heal": 30,
            "max_health": 100,
        },
    )

    assert profile is not None
    assert profile["profile_id"] == "variable_damage_behavioral"
    assert profile["quality_flags"]["complete"] is True

    alpha = profile["per_player"]["Alpha"]
    assert alpha["all_attack_match_rate"]["value"] == 0.5
    assert alpha["first_potion_profile"]["median_first_potion_hp"] == 40.0
    assert alpha["first_potion_profile"]["never_used_rate"] == 0.5
    assert alpha["first_lethal_entry_inventory"]["median_potions_on_first_lethal_entry"] == 1.0
    assert alpha["first_lethal_entry_inventory"]["first_lethal_entry_potion_values"] == [1, 1, 1, 1]
    assert alpha["first_lethal_entry_inventory"]["zero_potions_rate"] == 0.0
    assert alpha["first_lethal_entry_inventory"]["never_entered_rate"] == 2 / 3
    assert alpha["unused_potions_on_loss_rate"]["value"] == 1.0
    assert alpha["state_action_consistency"]["value"] == 1.0
    assert alpha["position_policy_delta"]["value"] == 1.0
    assert alpha["lethal_zone_potion_rate"]["value"] == 0.5
    assert alpha["safe_zone_potion_rate"]["value"] == 0.5
    assert alpha["danger_zone_potion_rate"]["value"] == 0.5
    assert alpha["lower_danger_zone_potion_rate"]["value"] == 0.5
    assert alpha["lower_danger_zone_potion_rate"]["danger_split_hp"] == 40
    assert alpha["upper_danger_zone_potion_rate"]["value"] == 0.0
    assert alpha["upper_danger_zone_potion_rate"]["support_turns"] == 0
    assert alpha["lethal_zone_attack_rate"]["value"] == 0.5
    assert alpha["danger_zone_attack_rate"]["value"] == 0.5
    assert alpha["risk_band_potion_rate_by_scarcity"]["entries"] == {
        "risk=danger|scarcity=multiple": {
            "value": 0.5,
            "potion_turns": 2,
            "support_turns": 4,
        },
        "risk=lethal|scarcity=one": {
            "value": 0.5,
            "potion_turns": 2,
            "support_turns": 4,
        },
        "risk=safe|scarcity=multiple": {
            "value": 0.5,
            "potion_turns": 2,
            "support_turns": 4,
        },
    }
    assert alpha["risk_band_policy_delta"]["value"] == 1.0
    assert alpha["high_roll_recovery_rate"]["support_events"] == 0
    assert alpha["wasted_full_health_potion_rate"]["value"] == 0.0

    state_metrics = profile["state_metrics"]
    assert (
        state_metrics["action_by_state"]["Alpha"]["position=first|hp=80|potions=3"]["attack_count"]
        == 2
    )
    assert (
        state_metrics["action_by_risk_band"]["Alpha"]["position=second|risk=safe|potions=3"][
            "potion_count"
        ]
        == 2
    )
    assert (
        state_metrics["action_by_risk_band"]["Alpha"]["position=first|risk=lethal|potions=1"][
            "potion_rate"
        ]
        == 1.0
    )

    alpha_evidence = profile["evidence"]["per_player"]["Alpha"]
    assert (
        alpha_evidence["position_policy_delta"]["examples"][0]["shared_state_key"]
        == "hp=20|potions=1"
    )
    assert (
        alpha_evidence["risk_band_policy_delta"]["examples"][0]["shared_risk_key"]
        == "risk=danger|potions=2"
    )
    assert len(alpha_evidence["risk_band_policy_delta"]["examples"]) == EVIDENCE_MAX_EXAMPLES
    assert [
        example["dominant_action"]
        for example in alpha_evidence["state_action_consistency"]["examples"]
    ] == [
        "POTION",
        "POTION",
        "ATTACK",
    ]

    aggregate = profile["aggregate_metrics"]
    assert aggregate["safe_zone_potion_rate"]["value"] == 0.5
    assert aggregate["lower_danger_zone_potion_rate"]["value"] == 0.5
    assert aggregate["upper_danger_zone_potion_rate"]["support_turns"] == 0
    assert aggregate["risk_band_potion_rate_by_scarcity"]["entries"] == {
        "risk=danger|scarcity=multiple": {
            "value": 0.5,
            "potion_turns": 2,
            "support_turns": 4,
        },
        "risk=lethal|scarcity=one": {
            "value": 0.5,
            "potion_turns": 2,
            "support_turns": 4,
        },
        "risk=safe|scarcity=multiple": {
            "value": 0.5,
            "potion_turns": 2,
            "support_turns": 4,
        },
    }


def test_variable_damage_high_roll_recovery_metric() -> None:
    scorer = VariableDamageBehavioralScorer()
    profile = scorer.score(
        players=[{"name": "Alpha"}, {"name": "Beta"}],
        match_payloads=_high_roll_recovery_payloads(),
        config={
            "min_attack_damage": 15,
            "max_attack_damage": 25,
            "potion_heal": 30,
            "max_health": 100,
        },
    )

    alpha = profile["per_player"]["Alpha"]
    assert alpha["high_roll_recovery_rate"]["value"] == 0.5
    assert alpha["high_roll_recovery_rate"]["recovered_events"] == 1
    assert alpha["high_roll_recovery_rate"]["support_events"] == 2
    assert alpha["high_roll_recovery_rate"]["shock_events"] == 2
    assert alpha["high_roll_recovery_rate"]["high_roll_min_damage"] == 20

    aggregate = profile["aggregate_metrics"]["high_roll_recovery_rate"]
    assert aggregate["value"] == 0.5
    assert aggregate["recovered_events"] == 1
    assert aggregate["support_events"] == 2
    assert aggregate["high_roll_min_damage"] == 20


def test_variable_damage_marks_high_roll_unsupported_without_state_after() -> None:
    payloads = _high_roll_recovery_payloads()
    payloads[0]["events"][0]["data"].pop("state_after")
    payloads[1]["events"][0]["data"].pop("state_after")

    profile = compute_behavioral_profile(
        players=[{"name": "Alpha"}, {"name": "Beta"}],
        match_payloads=payloads,
        config={
            "min_attack_damage": 15,
            "max_attack_damage": 25,
            "potion_heal": 30,
            "max_health": 100,
        },
    )

    assert profile is not None
    assert profile["quality_flags"]["complete"] is False
    assert profile["quality_flags"]["unsupported_metrics"] == ["high_roll_recovery_rate"]
    assert profile["per_player"]["Alpha"]["high_roll_recovery_rate"] is None
    assert profile["aggregate_metrics"]["high_roll_recovery_rate"] is None


def test_variable_damage_marks_danger_subbands_unsupported_without_min_attack_damage() -> None:
    profile = compute_behavioral_profile(
        players=[{"name": "Alpha"}, {"name": "Beta"}],
        match_payloads=_variable_sample_payloads(),
        config={
            "max_attack_damage": 25,
            "potion_heal": 30,
            "max_health": 100,
        },
    )

    assert profile is not None
    assert profile["quality_flags"]["complete"] is False
    assert profile["quality_flags"]["unsupported_metrics"] == [
        "high_roll_recovery_rate",
        "lower_danger_zone_potion_rate",
        "upper_danger_zone_potion_rate",
    ]
    assert profile["per_player"]["Alpha"]["lower_danger_zone_potion_rate"] is None
    assert profile["per_player"]["Alpha"]["upper_danger_zone_potion_rate"] is None
    assert profile["aggregate_metrics"]["lower_danger_zone_potion_rate"] is None
    assert profile["aggregate_metrics"]["upper_danger_zone_potion_rate"] is None


def test_variable_damage_behavioral_scorer_canonical_json_is_stable() -> None:
    scorer = VariableDamageBehavioralScorer()
    first_payload = scorer.score(
        players=[{"name": "Alpha"}, {"name": "Beta"}],
        match_payloads=_variable_sample_payloads(),
        config={
            "min_attack_damage": 15,
            "max_attack_damage": 25,
            "potion_heal": 30,
            "max_health": 100,
        },
    )
    second_payload = scorer.score(
        players=[{"name": "Alpha"}, {"name": "Beta"}],
        match_payloads=_variable_sample_payloads(),
        config={
            "min_attack_damage": 15,
            "max_attack_damage": 25,
            "potion_heal": 30,
            "max_health": 100,
        },
    )

    assert scorer.canonical_json(first_payload) == scorer.canonical_json(second_payload)


def test_variable_damage_export_auto_selects_variable_scorer(tmp_path, monkeypatch) -> None:
    from agentdeck.research import export as research_export

    recordings_dir = tmp_path / "records"
    recordings_dir.mkdir()
    payload = _high_roll_recovery_payloads()[0]
    payload["metadata"]["player_summaries"] = [
        {"name": "Alpha", "controller": "ActionOnlyController"},
        {"name": "Beta", "controller": "ActionOnlyController"},
    ]
    payload["metadata"]["player_configs"] = {
        "Alpha": {"module": "agentdeck.players.mock_player", "type": "MockPlayer"},
        "Beta": {"module": "agentdeck.players.mock_player", "type": "MockPlayer"},
    }
    payload["metadata"]["match"].update(
        {
            "seed": 42,
            "player_order": [1, 0],
            "player_order_source": "configured",
            "turns": 2,
            "duration": 0.1,
            "duration_seconds": 0.1,
            "cost": 0.0,
            "player_costs": {"Alpha": 0.0, "Beta": 0.0},
            "schema_version": 1,
            "fairness_policy": {
                "pairing_policy": "paired_side_swap",
                "first_player_policy": "random",
            },
            "game": {"name": "VariableDamageGame"},
            "started_at": "2026-03-23T00:00:00Z",
            "ended_at": "2026-03-23T00:00:01Z",
            "handshake_completed": True,
            "batch_id": "batch_x",
            "truncated_by_max_turns": False,
        }
    )
    payload["metadata"]["game_config"] = {
        "name": "VariableDamageGame",
        "module": "agentdeck.games.examples.variable_damage.game",
    }
    payload["seed"] = 42
    payload["batch_id"] = "batch_x"
    payload["started_at"] = "2026-03-23T00:00:00Z"
    payload["ended_at"] = "2026-03-23T00:00:01Z"
    payload["duration_seconds"] = 0.1
    (recordings_dir / "match_001.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        research_export,
        "validate_artifact_invariants",
        lambda payloads: {
            "matches_checked": len(payloads),
            "all_passed": True,
            "checks": {
                "monotonic_gameplay_timeline": {"passed": len(payloads), "failed": 0},
                "top_level_timing_consistency": {"passed": len(payloads), "failed": 0},
                "prompt_turn_number_coherence": {"passed": len(payloads), "failed": 0},
                "winner_final_state_consistency": {"passed": len(payloads), "failed": 0},
            },
            "failures": [],
        },
    )

    output_dir = tmp_path / "out"
    research_export.export_results(
        recordings_dir,
        output_dir,
        experiment_id="variable-behavioral-export-test",
        include_generated_at=False,
        behavioral_profile_id="auto",
        behavioral_config={
            "min_attack_damage": 15,
            "max_attack_damage": 25,
            "potion_heal": 30,
            "max_health": 100,
        },
    )

    exported = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
    assert exported["behavioral_profile"]["profile_id"] == "variable_damage_behavioral"
    assert exported["behavioral_profile"]["quality_flags"]["complete"] is True
    assert (
        "risk_band_policy_delta"
        in exported["behavioral_profile"]["evidence"]["per_player"]["Alpha"]
    )
