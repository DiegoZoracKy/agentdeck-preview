from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentdeck.research.score import rescore_experiment


def _write_manifest(experiment_dir: Path) -> None:
    (experiment_dir / "manifest.yaml").write_text(
        "\n".join(
            [
                "schema_version: 1",
                "experiment_id: test-exp",
                "status: complete",
                "game:",
                "  name: CustomGame",
                "  config: {}",
                "run:",
                "  matches_planned: 1",
                "  matches_completed: 1",
            ]
        ),
        encoding="utf-8",
    )


def _write_results(experiment_dir: Path) -> Path:
    results_path = experiment_dir / "results.json"
    results_path.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "experiment_id": "test-exp",
                "source": {"recordings_dir": str((experiment_dir / "records").resolve())},
                "summary": {"total_matches": 1, "decisive_matches": 1, "draws": 0},
                "statistics": {},
                "matches": [],
                "behavioral_profile": None,
                "sentinel": "preserve-me",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return results_path


def _write_match_payload(records_dir: Path) -> None:
    records_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "match_id": "match_001",
        "game": "CustomGame",
        "players": ["Alpha", "Beta"],
        "winner": "Alpha",
        "events": [],
        "metadata": {
            "player_configs": {
                "Alpha": {"module": "agentdeck.players.gpt", "model": "gpt-4o-mini"},
                "Beta": {"module": "agentdeck.players.gpt", "model": "gpt-4o-mini"},
            },
            "player_summaries": [
                {
                    "name": "Alpha",
                    "model": "gpt-4o-mini",
                    "controller": "ActionOnlyController",
                    "renderer": "TextRenderer",
                },
                {
                    "name": "Beta",
                    "model": "gpt-4o-mini",
                    "controller": "ActionOnlyController",
                    "renderer": "TextRenderer",
                },
            ],
            "match": {
                "players": ["Alpha", "Beta"],
                "first_player": {"name": "Alpha"},
            },
        },
    }
    (records_dir / "match_001.json").write_text(json.dumps(payload), encoding="utf-8")


def _base_profile() -> str:
    return """
from agentdeck.research.behavioral import BehavioralScorer


class CustomBehavioralScorer(BehavioralScorer):
    game_id = "custom_game"
    profile_id = "custom_behavioral"
    profile_version = "0.1.0"

    def supports(self, *, match_payloads):
        return True

    def score(self, *, players, match_payloads, config=None):
        matches = list(match_payloads)
        return {
            "schema_version": 2,
            "game_id": self.game_id,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "coverage": {
                "matches_total": len(matches),
                "matches_evaluable": len(matches),
                "turns_total": 0,
                "turns_evaluable": 0,
            },
            "aggregate_metrics": {"behavioral_score": 1.0},
            "per_player": {},
            "state_metrics": {},
            "evidence": {
                "aggregate_metrics": {},
                "per_player": {},
                "state_metrics": {},
            },
            "quality_flags": {
                "complete": True,
                "unsupported_metrics": [],
            },
        }
"""


def _write_package_local_scorer(experiment_dir: Path, source: str) -> None:
    scripts_dir = experiment_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "behavioral_scorer.py").write_text(source, encoding="utf-8")


def _create_experiment(tmp_path: Path) -> Path:
    experiment_dir = tmp_path / "research" / "test-exp"
    experiment_dir.mkdir(parents=True, exist_ok=True)
    _write_manifest(experiment_dir)
    _write_results(experiment_dir)
    _write_match_payload(experiment_dir / "records")
    return experiment_dir


def test_rs2_rescore_experiment_changes_only_behavioral_profile(tmp_path: Path) -> None:
    experiment_dir = _create_experiment(tmp_path)
    _write_package_local_scorer(
        experiment_dir,
        _base_profile() + "\nSCORER = CustomBehavioralScorer()\n",
    )

    before = json.loads((experiment_dir / "results.json").read_text(encoding="utf-8"))
    result = rescore_experiment(experiment_dir=experiment_dir, trust_mode="trusted-local")

    assert result["scorer_found"] is True
    assert result["scorer_source"] == "package_local"
    payload = json.loads((experiment_dir / "results.json").read_text(encoding="utf-8"))
    assert payload["behavioral_profile"]["profile_id"] == "custom_behavioral"
    assert payload["sentinel"] == "preserve-me"
    assert {key: value for key, value in payload.items() if key != "behavioral_profile"} == {
        key: value for key, value in before.items() if key != "behavioral_profile"
    }


def test_as4_rs15_rescore_rejects_non_finite_profile_without_replacement(
    tmp_path: Path,
) -> None:
    """AS4/RS15: invalid scorer JSON leaves the prior results bytes untouched."""
    experiment_dir = _create_experiment(tmp_path)
    _write_package_local_scorer(
        experiment_dir,
        _base_profile().replace('"behavioral_score": 1.0', '"behavioral_score": float("nan")')
        + "\nSCORER = CustomBehavioralScorer()\n",
    )
    results_path = experiment_dir / "results.json"
    before = results_path.read_bytes()

    with pytest.raises(ValueError, match="strict JSON"):
        rescore_experiment(experiment_dir=experiment_dir, trust_mode="trusted-local")

    assert results_path.read_bytes() == before


def test_rs15_rescore_replace_failure_preserves_prior_bytes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """RS15: filesystem replacement failure leaves the prior results bytes untouched."""
    experiment_dir = _create_experiment(tmp_path)
    _write_package_local_scorer(
        experiment_dir,
        _base_profile() + "\nSCORER = CustomBehavioralScorer()\n",
    )
    results_path = experiment_dir / "results.json"
    before = results_path.read_bytes()

    def fail_replace(_source: Path, _target: Path) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr("agentdeck.core.artifact_safety.os.replace", fail_replace)
    with pytest.raises(OSError, match="injected replace failure"):
        rescore_experiment(experiment_dir=experiment_dir, trust_mode="trusted-local")

    assert results_path.read_bytes() == before


def test_rescore_experiment_package_local_supports_false_fails(tmp_path: Path) -> None:
    experiment_dir = _create_experiment(tmp_path)
    _write_package_local_scorer(
        experiment_dir,
        _base_profile().replace("return True", "return False")
        + "\nSCORER = CustomBehavioralScorer()\n",
    )

    with pytest.raises(ValueError, match="does not support"):
        rescore_experiment(experiment_dir=experiment_dir, trust_mode="trusted-local")


def test_rescore_experiment_package_local_single_subclass_without_scorer_works(
    tmp_path: Path,
) -> None:
    experiment_dir = _create_experiment(tmp_path)
    _write_package_local_scorer(experiment_dir, _base_profile())

    result = rescore_experiment(experiment_dir=experiment_dir, trust_mode="trusted-local")

    assert result["scorer_found"] is True
    assert result["scorer_source"] == "package_local"
    payload = json.loads((experiment_dir / "results.json").read_text(encoding="utf-8"))
    assert payload["behavioral_profile"]["profile_id"] == "custom_behavioral"


def test_rescore_experiment_package_local_invalid_scorer_fails(tmp_path: Path) -> None:
    experiment_dir = _create_experiment(tmp_path)
    _write_package_local_scorer(
        experiment_dir,
        "SCORER = object()\n",
    )

    with pytest.raises(ValueError, match="not a BehavioralScorer instance"):
        rescore_experiment(experiment_dir=experiment_dir, trust_mode="trusted-local")


def test_rescore_experiment_package_local_multiple_subclasses_fail(tmp_path: Path) -> None:
    experiment_dir = _create_experiment(tmp_path)
    _write_package_local_scorer(
        experiment_dir,
        _base_profile() + """

class AnotherScorer(CustomBehavioralScorer):
    profile_id = "another"
""",
    )

    with pytest.raises(ValueError, match="multiple BehavioralScorer subclasses"):
        rescore_experiment(experiment_dir=experiment_dir, trust_mode="trusted-local")


def test_rescore_experiment_dry_run_reports_package_local_source(tmp_path: Path) -> None:
    experiment_dir = _create_experiment(tmp_path)
    _write_package_local_scorer(
        experiment_dir,
        _base_profile() + "\nSCORER = CustomBehavioralScorer()\n",
    )

    result = rescore_experiment(experiment_dir=experiment_dir, dry_run=True)

    assert result["dry_run"] is True
    assert result["scorer_found"] is True
    assert result["scorer_source"] == "package_local"
    assert result["execution_required"] is True
    assert result["profile_id"] is None


def test_as6_as7_rp18_structural_mode_does_not_import_package_scorer(
    tmp_path: Path,
) -> None:
    """RP18/AS6-AS7: structural inspection never executes package Python."""
    experiment_dir = _create_experiment(tmp_path)
    marker = tmp_path / "imported.txt"
    _write_package_local_scorer(
        experiment_dir,
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n"
        + _base_profile()
        + "\nSCORER = CustomBehavioralScorer()\n",
    )

    result = rescore_experiment(experiment_dir=experiment_dir, dry_run=True)

    assert result["execution_required"] is True
    assert not marker.exists()

    with pytest.raises(ValueError, match="executable Python"):
        rescore_experiment(experiment_dir=experiment_dir)
    assert not marker.exists()
