from __future__ import annotations

import json
from pathlib import Path

from scripts import research_export


def _match_payload(match_id: str) -> dict:
    return {
        "schema_version": 1,
        "schema_type": "match_recording",
        "match_id": match_id,
        "game": "FixedDamageGame",
        "players": ["Alpha", "Beta"],
        "winner": "Alpha",
        "final_state": {
            "health": {"Alpha": 80, "Beta": 0},
            "potions": {"Alpha": 3, "Beta": 3},
            "last_action": {"Alpha": "ATTACK", "Beta": "ATTACK"},
            "turn": 3,
        },
        "seed": 42,
        "events": [
            {
                "type": "gameplay",
                "data": {
                    "player": "Alpha",
                    "action": "ATTACK",
                    "state_before": {
                        "health": {"Alpha": 80, "Beta": 80},
                        "potions": {"Alpha": 3, "Beta": 3},
                        "last_action": {"Alpha": None, "Beta": None},
                        "turn": 1,
                    },
                    "state_after": {
                        "health": {"Alpha": 80, "Beta": 60},
                        "potions": {"Alpha": 3, "Beta": 3},
                        "last_action": {"Alpha": "ATTACK", "Beta": None},
                        "turn": 2,
                    },
                    "metadata": {
                        "parser_success": True,
                        "raw_response": "ACTION: ATTACK",
                        "turn_number": 1,
                    },
                    "turn_context": {"turn_number": 1, "player": "Alpha"},
                    "prompt": {"turn_number": 1},
                },
                "timestamp": 1.0,
                "duration": 0.1,
                "context": {
                    "session_id": "session_x",
                    "batch_id": "batch_x",
                    "match_id": match_id,
                    "phase_index": 0,
                    "turn_index": 0,
                    "timestamp": 1.0,
                    "monotonic_time": 1.0,
                },
            }
        ],
        "metadata": {
            "player_summaries": [
                {"name": "Alpha", "controller": "ActionOnlyController"},
                {"name": "Beta", "controller": "ActionOnlyController"},
            ],
            "match": {
                "seed": 42,
                "players": ["Alpha", "Beta"],
                "player_order": [0, 1],
                "player_order_source": "configured",
                "first_player": {"name": "Alpha", "index": 0, "ordered_index": 0},
                "turns": 1,
                "duration": 0.1,
                "duration_seconds": 0.1,
                "cost": 0.0,
                "player_costs": {"Alpha": 0.0, "Beta": 0.0},
                "schema_version": 1,
                "fairness_policy": {
                    "pairing_policy": "paired_side_swap",
                    "first_player_policy": "random",
                },
                "game": {"name": "FixedDamageGame"},
                "started_at": "2026-03-19T00:00:00Z",
                "ended_at": "2026-03-19T00:00:01Z",
                "handshake_completed": True,
                "batch_id": "batch_x",
                "truncated_by_max_turns": False,
            },
            "player_configs": {
                "Alpha": {"module": "agentdeck.players.mock_player", "type": "MockPlayer"},
                "Beta": {"module": "agentdeck.players.mock_player", "type": "MockPlayer"},
            },
        },
        "batch_id": "batch_x",
        "started_at": "2026-03-19T00:00:00Z",
        "ended_at": "2026-03-19T00:00:01Z",
        "duration_seconds": 0.1,
    }


def test_export_results_includes_behavioral_profile(tmp_path, monkeypatch) -> None:
    recordings_dir = tmp_path / "records"
    recordings_dir.mkdir()
    (recordings_dir / "match_001.json").write_text(
        json.dumps(_match_payload("match_001")),
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
        experiment_id="behavioral-export-test",
        include_generated_at=False,
        behavioral_profile_id="auto",
        behavioral_config={"attack_damage": 20, "max_health": 100},
    )

    payload = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
    assert "behavioral_profile" in payload
    assert payload["behavioral_profile"]["profile_id"] == "fixed_damage_behavioral"
    assert payload["behavioral_profile"]["quality_flags"]["complete"] is True
    assert payload["behavioral_profile"]["evidence"]["aggregate_metrics"] == {}
    assert "Alpha" in payload["behavioral_profile"]["evidence"]["per_player"]
    assert payload["behavioral_profile"]["evidence"]["state_metrics"] == {}
