"""Golden and adversarial certification tests for Instrument Package tiers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from agentdeck import certify_instrument

ROOT = Path(__file__).parents[2]
FIXED_DAMAGE = ROOT / "instruments" / "fixed_damage"
NUMBER_DUEL = Path(__file__).parents[1] / "fixtures" / "instruments" / "number_duel"


def _copy(source: Path, tmp_path: Path) -> Path:
    target = tmp_path / source.name
    shutil.copytree(source, target)
    return target


def _manifest(package: Path) -> dict:
    return yaml.safe_load((package / "instrument.yaml").read_text(encoding="utf-8"))


def _write_manifest(package: Path, manifest: dict) -> None:
    (package / "instrument.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
    )


def _check(report, check_id: str) -> dict:
    return next(check for check in report.to_dict()["checks"] if check["id"] == check_id)


def _declare_terminal_answer(package: Path, *, leak_outside_path: bool = False) -> None:
    presentation = package / "number_duel" / "presentation.py"
    caption = '\n        result["caption"] = f"Resolved: {answer}"' if leak_outside_path else ""
    presentation.write_text(
        f'''"""Terminal-answer projection used by IP13 tests."""

from typing import Any, Dict, Mapping


def visible_state(
    state: Mapping[str, Any], player: str, game_config: Mapping[str, Any]
) -> Dict[str, Any]:
    if player not in state["scores"]:
        raise ValueError("unknown Player")
    result = {{
        "scores": dict(state["scores"]),
        "turn": state["turn"],
        "seed": state["seed"],
    }}
    if max(state["scores"].values()) >= game_config["target"]:
        answer = "RÉPONSE"
        result["answer"] = answer{caption}
    return result
''',
        encoding="utf-8",
    )
    manifest = _manifest(package)
    manifest["presentation"]["terminal_oracle_paths"] = {
        "Alpha": ["/answer"],
        "Beta": ["/answer"],
    }
    manifest["presentation"]["terminal_oracle_values"] = ["RÉPONSE"]
    _write_manifest(package, manifest)


def test_ip4_fixed_damage_and_external_fixture_use_the_same_certifier(tmp_path: Path) -> None:
    """IP4: official and external instruments receive no name-based certification path."""
    fixed = certify_instrument(
        FIXED_DAMAGE, trust_mode="trusted-local", output_dir=tmp_path / "fixed"
    )
    external = certify_instrument(
        NUMBER_DUEL, trust_mode="trusted-local", output_dir=tmp_path / "external"
    )
    assert fixed.valid, fixed.to_dict()
    assert external.valid, external.to_dict()
    assert (
        fixed.awarded_tiers
        == external.awarded_tiers
        == [
            "runnable",
            "evidence_ready",
            "presentable",
        ]
    )


def test_ip12_rejects_unresolved_record_evidence_pointer(tmp_path: Path) -> None:
    """IP12: every metric evidence pointer must resolve into generated records."""
    package = _copy(NUMBER_DUEL, tmp_path)
    profile_path = package / "behavioral-profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile["metrics"][0]["record_pointers"] = ["/0/not-recorded"]
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    report = certify_instrument(package, trust_mode="trusted-local")
    assert not report.valid
    assert "does not resolve" in _check(report, "IP12")["message"]


def test_ip12_rejects_calibration_drift(tmp_path: Path) -> None:
    """IP12: scorer output must equal the profile's exact calibration expectation."""
    package = _copy(NUMBER_DUEL, tmp_path)
    profile_path = package / "behavioral-profile.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile["calibration"]["expected"]["/coverage/matches_total"] = 99
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    report = certify_instrument(package, trust_mode="trusted-local")
    assert not report.valid
    assert "calibration mismatch" in _check(report, "IP12")["message"]


def test_ip13_rejects_declared_oracle_path_leak(tmp_path: Path) -> None:
    """IP13: a redactor exposing a declared private path cannot be presentable."""
    package = _copy(FIXED_DAMAGE, tmp_path)
    entrypoints = package / "fixed_damage_instrument" / "entrypoints.py"
    content = entrypoints.read_text(encoding="utf-8")
    content = content.replace("return game.get_view(dict(state), player)", "return dict(state)")
    entrypoints.write_text(content, encoding="utf-8")
    report = certify_instrument(package, trust_mode="trusted-local")
    assert not report.valid
    assert "oracle path is visible" in _check(report, "IP13")["message"]


def test_ip13_presentation_artifact_excludes_opponent_private_state(tmp_path: Path) -> None:
    """IP13: generated surfaces contain visible views and no canonical final state."""
    output = tmp_path / "output"
    report = certify_instrument(FIXED_DAMAGE, trust_mode="trusted-local", output_dir=output)
    assert report.valid, report.to_dict()
    surfaces = json.loads(
        (output / "presentation" / "match-surfaces.json").read_text(encoding="utf-8")
    )
    for surface in surfaces:
        assert "final_state" not in surface["match"]
        for frame in surface["frames"]:
            opponent = "Beta" if frame["player"] == "Alpha" else "Alpha"
            assert opponent not in frame["state_before"]["health"]
            assert opponent not in frame["state_after"]["potions"]


def test_ip13_allows_declared_oracle_only_after_final_gameplay_action(tmp_path: Path) -> None:
    """IP13: a terminal oracle may appear only after the last gameplay action."""
    package = _copy(NUMBER_DUEL, tmp_path)
    _declare_terminal_answer(package)
    output = tmp_path / "output"
    report = certify_instrument(package, trust_mode="trusted-local", output_dir=output)
    assert report.valid, report.to_dict()
    surfaces = json.loads(
        (output / "presentation" / "match-surfaces.json").read_text(encoding="utf-8")
    )
    for surface in surfaces:
        for frame in surface["frames"]:
            assert "answer" not in frame["state_before"]
        for frame in surface["frames"][:-1]:
            assert "answer" not in frame["state_after"]
        assert surface["frames"][-1]["state_after"]["answer"] == "RÉPONSE"
        assert all(
            view["answer"] == "RÉPONSE" for view in surface["match"]["final_state_views"].values()
        )


def test_ip13_rejects_terminal_oracle_before_final_gameplay_action(tmp_path: Path) -> None:
    """IP13: terminal scope does not permit disclosure in an earlier view."""
    package = _copy(NUMBER_DUEL, tmp_path)
    _declare_terminal_answer(package)
    presentation = package / "number_duel" / "presentation.py"
    content = presentation.read_text(encoding="utf-8").replace(
        'if max(state["scores"].values()) >= game_config["target"]:', "if True:"
    )
    presentation.write_text(content, encoding="utf-8")
    report = certify_instrument(package, trust_mode="trusted-local")
    assert not report.valid
    assert "oracle path is visible" in _check(report, "IP13")["message"]


def test_ip13_rejects_terminal_oracle_value_outside_declared_path(tmp_path: Path) -> None:
    """IP13: terminal values remain forbidden outside their authorized paths."""
    package = _copy(NUMBER_DUEL, tmp_path)
    _declare_terminal_answer(package, leak_outside_path=True)
    report = certify_instrument(package, trust_mode="trusted-local")
    assert not report.valid
    assert "terminal oracle value leaked" in _check(report, "IP13")["message"]


def test_ip15_fixed_damage_report_is_canonical(tmp_path: Path) -> None:
    """IP15: complete-tier golden certification reports are byte-identical."""
    first = certify_instrument(
        FIXED_DAMAGE, trust_mode="trusted-local", output_dir=tmp_path / "one"
    )
    second = certify_instrument(
        FIXED_DAMAGE, trust_mode="trusted-local", output_dir=tmp_path / "two"
    )
    assert first.canonical_json() == second.canonical_json()
