"""Direct evidence for Game implementation provenance."""

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


def test_declared_closure_is_deterministic_and_portable():
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


def test_class_source_fallback_names_its_narrow_scope():
    descriptor = describe_game_version(DefaultGame())
    assert descriptor["family_id"].endswith(":DefaultGame")
    assert descriptor["declared_version"] is None
    assert descriptor["fingerprint_scope"] == "class_source"
    assert descriptor["assurance"] == "class_source_only"
    assert descriptor["implementation_sha256"]
    assert "config" not in json.dumps(descriptor)


def test_unresolved_dynamic_source_is_honest_and_non_blocking():
    dynamic_type = type("DynamicGame", (), {})
    descriptor = describe_game_version(dynamic_type())
    assert descriptor["implementation_sha256"] is None
    assert descriptor["fingerprint_scope"] == "unresolved"
    assert descriptor["assurance"] == "unresolved"


def test_declared_closure_never_hashes_partial_source():
    class MissingClosure:
        GAME_IMPLEMENTATION_MODULES = (
            "agentdeck.core.game_version",
            "agentdeck.this_module_does_not_exist",
        )

    descriptor = describe_game_version(MissingClosure())
    assert descriptor["implementation_sha256"] is None
    assert descriptor["fingerprint_scope"] == "unresolved"
    assert descriptor["sources"][1]["sha256"] is None


@pytest.mark.parametrize(
    "module_name", ["/tmp/private.py", "package/secret", "..relative", "C:\\private\\game.py"]
)
def test_rejects_non_portable_declared_module_names(module_name):
    class NonPortableClosure:
        GAME_IMPLEMENTATION_MODULES = (module_name,)

    with pytest.raises(ValueError, match="qualified module names"):
        describe_game_version(NonPortableClosure())
