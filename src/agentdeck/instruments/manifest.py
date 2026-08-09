"""Structural inspection and validation for Instrument Packages."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple

import yaml

from agentdeck.core.artifact_safety import ensure_contained_path, require_json_value

from .models import InstrumentReport

MANIFEST_NAME = "instrument.yaml"
SUPPORTED_SCHEMA_VERSIONS = ("1.0", "1.1")
CAPABILITY_TIERS = ("runnable", "evidence_ready", "presentable", "stage_ready")
ENTRY_POINT = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*:[A-Za-z_][A-Za-z0-9_]*$")
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")

ROOT_KEYS = {
    "schema_version",
    "instrument",
    "game",
    "fixture",
    "evidence",
    "presentation",
    "claims",
}
INSTRUMENT_KEYS = {"id", "version", "title", "summary"}
GAME_KEYS = {"entry_point", "config", "config_schema"}
FIXTURE_KEYS = {"entry_point", "player_count", "matches", "seed", "max_turns", "expected_winners"}
EVIDENCE_KEYS = {"scorer_entry_point", "profile"}
PRESENTATION_KEYS = {
    "redactor_entry_point",
    "viewer",
    "viewer_protocol",
    "oracle_paths",
    "oracle_values",
}
CLAIMS_KEYS = {"requested"}
SCHEMA_KEYS = {"type", "default", "enum", "minimum", "maximum", "items"}
SCHEMA_TYPES = {"string", "integer", "number", "boolean", "array"}


class InstrumentManifestError(ValueError):
    """Raised when a manifest cannot be used as declarative authority."""


def _package_root(package_root: str | Path) -> Path:
    root = Path(package_root).expanduser().resolve()
    if not root.is_dir():
        raise InstrumentManifestError(f"Instrument package is not a directory: {root}")
    return root


def _relative_root(root: Path) -> str:
    return root.name


def _read_manifest(root: Path) -> Tuple[Dict[str, Any], bytes]:
    path = ensure_contained_path(root, root / MANIFEST_NAME)
    if not path.is_file():
        raise InstrumentManifestError(f"Missing required {MANIFEST_NAME}")
    raw = path.read_bytes()
    try:
        payload = yaml.safe_load(raw.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise InstrumentManifestError(f"Invalid UTF-8 YAML manifest: {exc}") from exc
    if not isinstance(payload, dict):
        raise InstrumentManifestError("instrument.yaml must contain a mapping")
    require_json_value(payload, field="instrument manifest")
    return payload, raw


def _source_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise InstrumentManifestError(
                f"Symlinks are not allowed in Instrument Packages: {path}"
            )
        if path.is_file():
            yield path


def package_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in _source_files(root):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _unknown_keys(value: Any, allowed: set[str], field: str) -> None:
    if not isinstance(value, dict):
        raise InstrumentManifestError(f"{field} must be a mapping")
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise InstrumentManifestError(f"{field} contains unknown fields: {unknown}")


def _required_mapping(manifest: Mapping[str, Any], key: str) -> Dict[str, Any]:
    value = manifest.get(key)
    if not isinstance(value, dict):
        raise InstrumentManifestError(f"{key} must be a mapping")
    return value


def _required_string(mapping: Mapping[str, Any], key: str, field: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InstrumentManifestError(f"{field}.{key} must be a non-empty string")
    return value


def _required_positive_int(mapping: Mapping[str, Any], key: str, field: str) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise InstrumentManifestError(f"{field}.{key} must be a positive integer")
    return value


def _entry_point_path(root: Path, value: str, field: str) -> Path:
    if not ENTRY_POINT.fullmatch(value):
        raise InstrumentManifestError(f"{field} must use package.module:Symbol syntax")
    module_name, _ = value.split(":", 1)
    module_path = root.joinpath(*module_name.split("."))
    candidates = (module_path.with_suffix(".py"), module_path / "__init__.py")
    for candidate in candidates:
        resolved = ensure_contained_path(root, candidate)
        if resolved.is_file():
            return resolved
    raise InstrumentManifestError(
        f"{field} module does not exist inside the package: {module_name}"
    )


def _contained_file(root: Path, value: str, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise InstrumentManifestError(f"{field} must be a non-empty relative path")
    path = ensure_contained_path(root, root / value)
    if not path.is_file():
        raise InstrumentManifestError(f"{field} does not resolve to a file: {value}")
    return path


def _matches_schema(value: Any, declaration: Mapping[str, Any], field: str) -> None:
    declared_type = declaration.get("type")
    valid = {
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "array": isinstance(value, list),
    }.get(str(declared_type), False)
    if not valid:
        raise InstrumentManifestError(f"{field} does not match declared type {declared_type!r}")
    if "enum" in declaration and value not in declaration["enum"]:
        raise InstrumentManifestError(f"{field} is not in declared enum")
    if "minimum" in declaration and value < declaration["minimum"]:
        raise InstrumentManifestError(f"{field} is below declared minimum")
    if "maximum" in declaration and value > declaration["maximum"]:
        raise InstrumentManifestError(f"{field} is above declared maximum")
    if declared_type == "array" and "items" in declaration:
        for index, item in enumerate(value):
            _matches_schema(item, declaration["items"], f"{field}[{index}]")


def validate_manifest(root: Path, manifest: Dict[str, Any]) -> None:
    _unknown_keys(manifest, ROOT_KEYS, "manifest")
    schema_version = manifest.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise InstrumentManifestError(
            f"Unsupported schema_version {schema_version!r}; expected one of "
            f"{SUPPORTED_SCHEMA_VERSIONS!r}"
        )

    instrument = _required_mapping(manifest, "instrument")
    game = _required_mapping(manifest, "game")
    fixture = _required_mapping(manifest, "fixture")
    claims = _required_mapping(manifest, "claims")
    _unknown_keys(instrument, INSTRUMENT_KEYS, "instrument")
    _unknown_keys(game, GAME_KEYS, "game")
    _unknown_keys(fixture, FIXTURE_KEYS, "fixture")
    _unknown_keys(claims, CLAIMS_KEYS, "claims")

    from agentdeck.core.artifact_safety import validate_artifact_id

    validate_artifact_id(_required_string(instrument, "id", "instrument"), field="instrument.id")
    version = _required_string(instrument, "version", "instrument")
    if not SEMVER.fullmatch(version):
        raise InstrumentManifestError("instrument.version must use MAJOR.MINOR.PATCH")
    _required_string(instrument, "title", "instrument")
    _required_string(instrument, "summary", "instrument")

    _entry_point_path(root, _required_string(game, "entry_point", "game"), "game.entry_point")
    config = game.get("config")
    config_schema = game.get("config_schema")
    if not isinstance(config, dict) or not isinstance(config_schema, dict):
        raise InstrumentManifestError("game.config and game.config_schema must be mappings")
    if set(config) != set(config_schema):
        raise InstrumentManifestError(
            "game.config and game.config_schema must declare identical keys"
        )
    for key, declaration in config_schema.items():
        if not isinstance(key, str) or not isinstance(declaration, dict):
            raise InstrumentManifestError("game.config_schema entries must be named mappings")
        _unknown_keys(declaration, SCHEMA_KEYS, f"game.config_schema.{key}")
        if declaration.get("type") not in SCHEMA_TYPES:
            raise InstrumentManifestError(f"game.config_schema.{key}.type is unsupported")
        if "default" not in declaration or declaration["default"] != config[key]:
            raise InstrumentManifestError(
                f"game.config_schema.{key}.default must equal game.config"
            )
        _matches_schema(config[key], declaration, f"game.config.{key}")

    _entry_point_path(
        root, _required_string(fixture, "entry_point", "fixture"), "fixture.entry_point"
    )
    player_count = _required_positive_int(fixture, "player_count", "fixture")
    matches = _required_positive_int(fixture, "matches", "fixture")
    _required_positive_int(fixture, "max_turns", "fixture")
    seed = fixture.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise InstrumentManifestError("fixture.seed must be an integer")
    winners = fixture.get("expected_winners")
    if not isinstance(winners, list) or len(winners) != matches:
        raise InstrumentManifestError("fixture.expected_winners must contain one value per match")
    if player_count < 1:
        raise InstrumentManifestError("fixture.player_count must be positive")

    requested = claims.get("requested")
    if not isinstance(requested, list) or not requested:
        raise InstrumentManifestError("claims.requested must be a non-empty list")
    if any(tier not in CAPABILITY_TIERS for tier in requested):
        raise InstrumentManifestError("claims.requested contains an unknown capability tier")
    if list(requested) != sorted(set(requested), key=CAPABILITY_TIERS.index):
        raise InstrumentManifestError("claims.requested must be unique and in capability order")
    if requested[0] != "runnable":
        raise InstrumentManifestError("every capability claim must begin with runnable")

    evidence = manifest.get("evidence")
    if evidence is not None:
        _unknown_keys(evidence, EVIDENCE_KEYS, "evidence")
        _entry_point_path(
            root,
            _required_string(evidence, "scorer_entry_point", "evidence"),
            "evidence.scorer_entry_point",
        )
        profile_path = _contained_file(
            root, _required_string(evidence, "profile", "evidence"), "evidence.profile"
        )
        from .profile import load_behavioral_profile

        load_behavioral_profile(profile_path)
    if "evidence_ready" in requested and evidence is None:
        raise InstrumentManifestError("evidence_ready requires an evidence declaration")

    presentation = manifest.get("presentation")
    if presentation is not None:
        _unknown_keys(presentation, PRESENTATION_KEYS, "presentation")
        _entry_point_path(
            root,
            _required_string(presentation, "redactor_entry_point", "presentation"),
            "presentation.redactor_entry_point",
        )
        if "viewer" in presentation:
            _contained_file(root, presentation["viewer"], "presentation.viewer")
        if "viewer_protocol" in presentation:
            if schema_version != "1.1":
                raise InstrumentManifestError(
                    "presentation.viewer_protocol requires manifest schema_version '1.1'"
                )
            if presentation["viewer_protocol"] != "agentdeck-stage/1.0":
                raise InstrumentManifestError(
                    "presentation.viewer_protocol must be 'agentdeck-stage/1.0'"
                )
        oracle_values = presentation.get("oracle_values", [])
        if not isinstance(oracle_values, list) or any(
            not isinstance(value, str) or not value for value in oracle_values
        ):
            raise InstrumentManifestError("presentation.oracle_values must be a list of strings")
        oracle_paths = presentation.get("oracle_paths", {})
        if not isinstance(oracle_paths, dict):
            raise InstrumentManifestError("presentation.oracle_paths must be a mapping")
        for player, pointers in oracle_paths.items():
            if (
                not isinstance(player, str)
                or not player
                or not isinstance(pointers, list)
                or any(
                    not isinstance(pointer, str) or not pointer.startswith("/")
                    for pointer in pointers
                )
            ):
                raise InstrumentManifestError(
                    "presentation.oracle_paths must map Player names to JSON Pointer lists"
                )
    if "presentable" in requested and presentation is None:
        raise InstrumentManifestError("presentable requires a presentation declaration")
    if "stage_ready" in requested:
        if "presentable" not in requested:
            raise InstrumentManifestError("stage_ready requires the presentable tier")
        if schema_version != "1.1":
            raise InstrumentManifestError("stage_ready requires manifest schema_version '1.1'")
        if presentation is None or "viewer" not in presentation:
            raise InstrumentManifestError("stage_ready requires presentation.viewer")
        if presentation.get("viewer_protocol") != "agentdeck-stage/1.0":
            raise InstrumentManifestError(
                "stage_ready requires presentation.viewer_protocol 'agentdeck-stage/1.0'"
            )
        viewer = ensure_contained_path(root, root / presentation["viewer"])
        presentation_root = ensure_contained_path(root, root / "presentation")
        try:
            viewer.relative_to(presentation_root)
        except ValueError as exc:
            raise InstrumentManifestError(
                "stage_ready viewer must resolve under presentation/"
            ) from exc


def _report(
    operation: str, package_root: str | Path
) -> tuple[InstrumentReport, Path, Dict[str, Any]]:
    root = _package_root(package_root)
    report = InstrumentReport(operation=operation, package_root=_relative_root(root))
    manifest: Dict[str, Any] = {}
    try:
        manifest, _ = _read_manifest(root)
        report.schema_version = manifest.get("schema_version")
        if isinstance(manifest.get("instrument"), dict):
            report.instrument = dict(manifest["instrument"])
        claims = manifest.get("claims")
        if isinstance(claims, dict) and isinstance(claims.get("requested"), list):
            report.requested_tiers = list(claims["requested"])
        report.package_sha256 = package_sha256(root)
        report.checked("IP1", True, "Manifest bytes and package content were hashed")
    except (InstrumentManifestError, OSError, TypeError, ValueError) as exc:
        report.checked("IP1", False, str(exc))
    return report, root, manifest


def inspect_instrument(package_root: str | Path) -> InstrumentReport:
    report, _, manifest = _report("inspect", package_root)
    if manifest:
        report.checked(
            "IP2", True, "Structural inspection completed without importing package code"
        )
    return report


def validate_instrument(package_root: str | Path) -> InstrumentReport:
    report, root, manifest = _report("validate", package_root)
    if not manifest:
        return report
    try:
        validate_manifest(root, manifest)
        report.checked("IP2", True, "Declarative validation completed without package execution")
        report.checked("IP3", True, "All declared package paths are contained")
        report.checked("IP4", True, "Manifest validated without an instrument registry")
        report.checked("IP10", True, "Manifest values satisfy strict serialization")
    except (InstrumentManifestError, OSError, TypeError, ValueError) as exc:
        report.checked("IP3", False, str(exc))
    return report


def load_validated_manifest(
    package_root: str | Path,
) -> tuple[Path, Dict[str, Any], InstrumentReport]:
    report = validate_instrument(package_root)
    root = _package_root(package_root)
    manifest, _ = _read_manifest(root)
    return root, manifest, report
