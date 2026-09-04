"""Reference acceptance tolerates Python changes without weakening Research identity."""

import importlib
from collections import namedtuple
from dataclasses import replace
from pathlib import Path

import pytest

from agentdeck import prepare_game_research_profile
from scripts.reference_sources import verify_sources

ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "research/references/hidden-signal/probe-v3.yaml"
PROFILE = ROOT / "research/2026-08-29-hidden-signal-information-acquisition/research-profile.yaml"


def verify(profile):
    measures = {item.id: item for item in profile.prepared_measures.values()}
    return verify_sources(PROBE, {profile.profile.id: profile}, measures)


def test_python_change_preserves_reference_sources_but_changes_research_identity(monkeypatch):
    original = prepare_game_research_profile(PROFILE)
    original_verification = verify(original)
    module = importlib.import_module("agentdeck.research.measure")
    actual = module.sys.version_info
    version = namedtuple("Version", "major minor micro releaselevel serial")
    monkeypatch.setattr(
        module.sys,
        "version_info",
        version(actual.major, actual.minor, actual.micro + 1, actual.releaselevel, actual.serial),
    )
    updated = prepare_game_research_profile(PROFILE)
    updated_verification = verify(updated)

    assert original.profile_sha256 != updated.profile_sha256
    assert original_verification["source_lock_sha256"] == updated_verification["source_lock_sha256"]
    before = original_verification["measures"]["hidden-signal-inspection"]
    after = updated_verification["measures"]["hidden-signal-inspection"]
    assert before["measure_sha256"] != after["measure_sha256"]
    assert before["material_environment_sha256"] != after["material_environment_sha256"]
    assert before["material_environment"]["python"] != after["material_environment"]["python"]


@pytest.mark.parametrize("change", ["implementation", "parameters", "agentdeck", "distribution"])
def test_reference_lock_rejects_material_changes_other_than_python(change):
    profile = prepare_game_research_profile(PROFILE)
    operation, measure = next(iter(profile.prepared_measures.items()))
    if change == "implementation":
        measure = replace(measure, implementation_sha256="f" * 64)
    elif change == "parameters":
        measure = replace(
            measure, declaration=replace(measure.declaration, parameters={"new": True})
        )
    else:
        environment = dict(measure.material_environment)
        environment["agentdeck" if change == "agentdeck" else "distribution:example"] = "999.0"
        measure = replace(measure, material_environment=environment)
    updated = replace(profile, prepared_measures={operation: measure})

    with pytest.raises(ValueError, match="sources changed"):
        verify(updated)


def test_reference_lock_rejects_profile_source_changes():
    profile = prepare_game_research_profile(PROFILE)
    with pytest.raises(ValueError, match="profiles sources changed"):
        verify(replace(profile, source_sha256="f" * 64))


def test_reference_lock_rejects_different_probe(tmp_path):
    probe = tmp_path / "probe.yaml"
    probe.write_bytes(PROBE.read_bytes() + b"\n# changed\n")
    (tmp_path / "source-lock.json").write_bytes((PROBE.parent / "source-lock.json").read_bytes())
    with pytest.raises(ValueError, match="different frozen probe"):
        verify_sources(probe, {}, {})
