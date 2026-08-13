"""Adversarial tests for certified measurement support units."""

from __future__ import annotations

import pytest

from agentdeck.instruments.certify import _validate_measurement_provenance


def test_player_match_unit_requires_every_player_gameplay_event() -> None:
    definition = "Share of Player-matches in which every action was ATTACK."
    profile = {
        "metrics": [
            {
                "id": "all_attack_match_rate",
                "definition": definition,
                "output_pointer": "/aggregate_metrics/all_attack_match_rate/value",
            }
        ]
    }
    payloads = [
        {
            "events": [
                {
                    "type": "gameplay",
                    "data": {"phase_index": phase_index, "player": player},
                }
                for phase_index, player in enumerate(["Alpha", "Beta", "Alpha", "Beta"])
            ],
        }
    ]
    scored = {
        "aggregate_metrics": {"all_attack_match_rate": {"value": 1.0}},
        "per_player": {},
        "measurement_provenance": {
            "schema_version": "2.0",
            "aggregate_metrics": {
                "all_attack_match_rate": {
                    "definition": definition,
                    "numerator": 1,
                    "denominator": 1,
                    "unit": "player_match",
                    "eligible_units": [
                        {
                            "unit_id": "player-match:0:Alpha",
                            "match_index": 0,
                            "player": "Alpha",
                            "events": [{"match_index": 0, "phase_index": 0}],
                            "counted_in_numerator": True,
                        }
                    ],
                }
            },
            "per_player": {},
        },
    }

    with pytest.raises(AssertionError, match="player_match measurement unit is incomplete"):
        _validate_measurement_provenance(
            scored,
            profile,
            payloads,
            [{"name": "Alpha"}, {"name": "Beta"}],
        )


def test_measurement_units_cannot_duplicate_one_semantic_player_match() -> None:
    definition = "Share of Player-matches in which every action was ATTACK."
    profile = {
        "metrics": [
            {
                "id": "all_attack_match_rate",
                "definition": definition,
                "output_pointer": "/aggregate_metrics/all_attack_match_rate/value",
            }
        ]
    }
    payloads = [
        {
            "events": [
                {
                    "type": "gameplay",
                    "data": {"phase_index": phase_index, "player": player},
                }
                for phase_index, player in enumerate(["Alpha", "Beta", "Alpha", "Beta"])
            ],
        }
    ]
    unit = {
        "match_index": 0,
        "player": "Alpha",
        "events": [
            {"match_index": 0, "phase_index": 0},
            {"match_index": 0, "phase_index": 2},
        ],
        "counted_in_numerator": True,
    }
    scored = {
        "aggregate_metrics": {"all_attack_match_rate": {"value": 1.0}},
        "per_player": {},
        "measurement_provenance": {
            "schema_version": "2.0",
            "aggregate_metrics": {
                "all_attack_match_rate": {
                    "definition": definition,
                    "numerator": 2,
                    "denominator": 2,
                    "unit": "player_match",
                    "eligible_units": [
                        {"unit_id": "first", **unit},
                        {"unit_id": "second", **unit},
                    ],
                }
            },
            "per_player": {},
        },
    }

    with pytest.raises(AssertionError, match="measurement support unit is duplicated"):
        _validate_measurement_provenance(
            scored,
            profile,
            payloads,
            [{"name": "Alpha"}, {"name": "Beta"}],
        )
