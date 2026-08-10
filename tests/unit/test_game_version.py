"""Direct evidence for SPEC-GAME-VERSION-PROVENANCE."""

from __future__ import annotations

import json

import pytest

from agentdeck.core.game_version import describe_game_version


class VersionedGame:
    GAME_FAMILY_ID = "test.versioned-game"
    GAME_VERSION = "1.2.3"
    GAME_IMPLEMENTATION_MODULES = (
        "agentdeck.core.game_version",
        "agentdeck.core.base.game",
    )


class DefaultGame:
    pass


def test_GVP3_GVP4_GVP7_declared_closure_is_deterministic_and_portable():
    """GVP3 GVP4 GVP7: module ordering is canonical and persisted names are portable."""
    first = describe_game_version(VersionedGame())

    class ReorderedVersionedGame:
        GAME_FAMILY_ID = "test.versioned-game"
        GAME_VERSION = "1.2.3"
        GAME_IMPLEMENTATION_MODULES = tuple(reversed(VersionedGame.GAME_IMPLEMENTATION_MODULES))

    second = describe_game_version(ReorderedVersionedGame())
    assert first["implementation_sha256"] == second["implementation_sha256"]
    assert first["fingerprint_scope"] == "declared_closure"
    assert first["assurance"] == "content_addressed"
    assert all(entry["name"].startswith("module:") for entry in first["sources"])
    assert all(not entry["name"].startswith("/") for entry in first["sources"])


def test_GVP2_GVP4_class_source_fallback_names_its_narrow_scope():
    """GVP2 GVP4: default provenance covers class source, not config or an Instrument."""
    descriptor = describe_game_version(DefaultGame())
    assert descriptor["family_id"].endswith(":DefaultGame")
    assert descriptor["declared_version"] is None
    assert descriptor["fingerprint_scope"] == "class_source"
    assert descriptor["assurance"] == "class_source_only"
    assert descriptor["implementation_sha256"]
    assert "config" not in json.dumps(descriptor)
    assert "instrument" not in json.dumps(descriptor)


def test_GVP5_GVP6_unresolved_dynamic_source_is_honest_and_non_blocking():
    """GVP5 GVP6: unresolved source has no digest and still yields a usable descriptor."""
    dynamic_type = type("DynamicGame", (), {})
    descriptor = describe_game_version(dynamic_type())
    assert descriptor["implementation_sha256"] is None
    assert descriptor["fingerprint_scope"] == "unresolved"
    assert descriptor["assurance"] == "unresolved"


def test_GVP5_declared_closure_never_hashes_partial_source():
    """GVP5: one unresolved module makes the full declared closure unresolved."""

    class MissingClosure:
        GAME_IMPLEMENTATION_MODULES = (
            "agentdeck.core.game_version",
            "agentdeck.this_module_does_not_exist",
        )

    descriptor = describe_game_version(MissingClosure())
    assert descriptor["implementation_sha256"] is None
    assert descriptor["fingerprint_scope"] == "unresolved"
    assert descriptor["sources"][1]["sha256"] is None


@pytest.mark.parametrize("module_name", ["/tmp/private.py", "package/secret", "..relative", "C:\\private\\game.py"])
def test_GVP7_rejects_non_portable_declared_module_names(module_name):
    """GVP7: a closure cannot turn host filesystem paths into persisted source names."""

    class NonPortableClosure:
        GAME_IMPLEMENTATION_MODULES = (module_name,)

    with pytest.raises(ValueError, match="portable qualified module names"):
        describe_game_version(NonPortableClosure())
