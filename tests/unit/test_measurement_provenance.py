"""Adversarial tests for certified measurement support units."""

from __future__ import annotations

import pytest

from agentdeck.instruments.certify import validate_measurement_provenance


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
        validate_measurement_provenance(
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
        validate_measurement_provenance(
            scored,
            profile,
            payloads,
            [{"name": "Alpha"}, {"name": "Beta"}],
        )


def test_measurement_record_facts_must_match_the_canonical_record() -> None:
    definition = "Share of decisive losses that ended with an unused potion."
    profile = {
        "metrics": [
            {
                "id": "unused_potions_on_loss_rate",
                "definition": definition,
                "output_pointer": "/aggregate_metrics/unused_potions_on_loss_rate/value",
            }
        ]
    }
    payloads = [
        {
            "winner": "Beta",
            "final_state": {"potions": {"Alpha": 1, "Beta": 0}},
            "events": [
                {
                    "type": "gameplay",
                    "data": {"phase_index": 0, "player": "Alpha"},
                }
            ],
        }
    ]
    scored = {
        "aggregate_metrics": {"unused_potions_on_loss_rate": {"value": 1.0}},
        "per_player": {},
        "measurement_provenance": {
            "schema_version": "2.0",
            "aggregate_metrics": {
                "unused_potions_on_loss_rate": {
                    "definition": definition,
                    "numerator": 1,
                    "denominator": 1,
                    "unit": "player_match",
                    "eligible_units": [
                        {
                            "unit_id": "loss:0:Alpha",
                            "match_index": 0,
                            "player": "Alpha",
                            "events": [{"match_index": 0, "phase_index": 0}],
                            "record_facts": [
                                {"match_index": 0, "pointer": "/winner", "value": "Beta"},
                                {
                                    "match_index": 0,
                                    "pointer": "/final_state/potions/Alpha",
                                    "value": 2,
                                },
                            ],
                            "counted_in_numerator": True,
                        }
                    ],
                }
            },
            "per_player": {},
        },
    }

    with pytest.raises(AssertionError, match="record fact does not match Record"):
        validate_measurement_provenance(
            scored,
            profile,
            payloads,
            [{"name": "Alpha"}, {"name": "Beta"}],
        )
