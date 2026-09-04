"""Game Research Profiles for capability discovery without execution authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping

import yaml

from ._canonical import sha256_file, sha256_json
from .measure import PreparedMeasure, load_measure, prepare_measure


@dataclass(frozen=True)
class ResearchOpportunity:
    id: str
    question: str
    mechanism: str
    observables: tuple[str, ...]
    boundaries: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "observables", tuple(self.observables))
        object.__setattr__(self, "boundaries", tuple(self.boundaries))

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "mechanism": self.mechanism,
            "observables": list(self.observables),
            "boundaries": list(self.boundaries),
        }


@dataclass(frozen=True)
class MeasureReference:
    source: str
    id: str

    def as_dict(self) -> dict[str, str]:
        return {"source": self.source, "id": self.id}


@dataclass(frozen=True)
class ResearchOperationalization:
    id: str
    opportunity: str
    measure: MeasureReference
    required_observables: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_observables", tuple(self.required_observables))
        object.__setattr__(self, "limitations", tuple(self.limitations))

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "opportunity": self.opportunity,
            "measure": self.measure.as_dict(),
            "required_observables": list(self.required_observables),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True)
class GameResearchProfile:
    schema_version: int
    id: str
    version: int
    game_name: str
    game_implementation_sha256: str | None
    summary: str
    opportunities: tuple[ResearchOpportunity, ...]
    operationalizations: tuple[ResearchOperationalization, ...]
    boundaries: tuple[str, ...]
    source_path: Path = field(compare=False, repr=False)
    package_root: Path = field(compare=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "opportunities", tuple(self.opportunities))
        object.__setattr__(self, "operationalizations", tuple(self.operationalizations))
        object.__setattr__(self, "boundaries", tuple(self.boundaries))

    def as_dict(self) -> dict[str, Any]:
        game: dict[str, str] = {"name": self.game_name}
        if self.game_implementation_sha256 is not None:
            game["implementation_sha256"] = self.game_implementation_sha256
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "profile": {
                "id": self.id,
                "version": self.version,
                "game": game,
                "summary": self.summary,
            },
            "opportunities": [item.as_dict() for item in self.opportunities],
            "operationalizations": [item.as_dict() for item in self.operationalizations],
        }
        if self.boundaries:
            result["boundaries"] = list(self.boundaries)
        return result


@dataclass(frozen=True)
class PreparedGameResearchProfile:
    profile: GameResearchProfile
    source_sha256: str
    prepared_measures: Mapping[str, PreparedMeasure]
    profile_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "prepared_measures",
            MappingProxyType(dict(self.prepared_measures)),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "profile": self.profile.as_dict(),
            "source_sha256": self.source_sha256,
            "operationalizations": [
                {
                    "id": item.id,
                    "assurance": "prepared",
                    "measure_sha256": self.prepared_measures[item.id].measure_sha256,
                }
                for item in self.profile.operationalizations
            ],
            "profile_sha256": self.profile_sha256,
        }


def load_game_research_profile(path: str | Path) -> GameResearchProfile:
    """Load profile metadata without loading Game or Measure implementations."""

    source = Path(path).expanduser().resolve()
    if source.is_dir():
        source = source / "research-profile.yaml"
    if not source.is_file():
        raise ValueError(f"Game Research Profile is missing: {source}")
    try:
        payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Game Research Profile could not be read: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("Game Research Profile root must be a mapping")
    allowed = {"schema_version", "profile", "opportunities", "operationalizations", "boundaries"}
    if set(payload) - allowed or not {"schema_version", "profile", "opportunities"} <= set(payload):
        raise ValueError("Game Research Profile contains unsupported or missing fields")
    if payload.get("schema_version") != 1:
        raise ValueError("Game Research Profile schema_version must equal 1")
    metadata = payload.get("profile")
    if not isinstance(metadata, Mapping) or set(metadata) != {"id", "version", "game", "summary"}:
        raise ValueError("profile must contain id, version, game, and summary")
    profile_id = _identifier(metadata.get("id"), "profile.id")
    version = metadata.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError("profile.version must be an integer >= 1")
    game = metadata.get("game")
    if (
        not isinstance(game, Mapping)
        or set(game) - {"name", "implementation_sha256"}
        or "name" not in game
    ):
        raise ValueError("profile.game requires name and optional implementation_sha256")
    game_name = _text(game.get("name"), "profile.game.name")
    implementation_sha = game.get("implementation_sha256")
    if implementation_sha is not None:
        implementation_sha = _sha256(implementation_sha, "profile.game.implementation_sha256")
    summary = _text(metadata.get("summary"), "profile.summary")
    raw_opportunities = payload.get("opportunities")
    if not isinstance(raw_opportunities, list) or not raw_opportunities:
        raise ValueError("opportunities must be a non-empty list")
    opportunities = tuple(
        _parse_opportunity(item, index) for index, item in enumerate(raw_opportunities)
    )
    _unique([item.id for item in opportunities], "Opportunity")
    raw_operationalizations = payload.get("operationalizations", [])
    if not isinstance(raw_operationalizations, list):
        raise ValueError("operationalizations must be a list")
    operationalizations = tuple(
        _parse_operationalization(item, index) for index, item in enumerate(raw_operationalizations)
    )
    _unique([item.id for item in operationalizations], "Operationalization")
    opportunity_ids = {item.id for item in opportunities}
    for item in operationalizations:
        if item.opportunity not in opportunity_ids:
            raise ValueError(
                f"Operationalization {item.id!r} references unknown Opportunity {item.opportunity!r}"
            )
    boundaries = _text_list(payload.get("boundaries", []), "boundaries", non_empty=False)
    return GameResearchProfile(
        schema_version=1,
        id=profile_id,
        version=version,
        game_name=game_name,
        game_implementation_sha256=implementation_sha,
        summary=summary,
        opportunities=opportunities,
        operationalizations=operationalizations,
        boundaries=boundaries,
        source_path=source,
        package_root=source.parent,
    )


def prepare_game_research_profile(path: str | Path) -> PreparedGameResearchProfile:
    """Resolve all declared Operationalizations without selecting or running them."""

    profile = load_game_research_profile(path)
    prepared: dict[str, PreparedMeasure] = {}
    for operationalization in profile.operationalizations:
        source = _resolve_inside(profile.package_root, operationalization.measure.source)
        declaration = load_measure(source, operationalization.measure.id)
        prepared[operationalization.id] = prepare_measure(declaration)
    source_hash = sha256_file(profile.source_path)
    identity = {
        "schema_version": 1,
        "profile": profile.as_dict(),
        "source_sha256": source_hash,
        "operationalizations": [
            {
                "id": item.id,
                "measure_sha256": prepared[item.id].measure_sha256,
            }
            for item in profile.operationalizations
        ],
    }
    return PreparedGameResearchProfile(
        profile=profile,
        source_sha256=source_hash,
        prepared_measures=prepared,
        profile_sha256=sha256_json(identity),
    )


def _parse_opportunity(value: Any, index: int) -> ResearchOpportunity:
    location = f"opportunities[{index}]"
    required = {"id", "question", "mechanism", "observables", "boundaries"}
    if not isinstance(value, Mapping) or set(value) != required:
        raise ValueError(f"{location} must contain exactly {', '.join(sorted(required))}")
    return ResearchOpportunity(
        id=_identifier(value.get("id"), f"{location}.id"),
        question=_text(value.get("question"), f"{location}.question"),
        mechanism=_text(value.get("mechanism"), f"{location}.mechanism"),
        observables=_text_list(value.get("observables"), f"{location}.observables"),
        boundaries=_text_list(value.get("boundaries"), f"{location}.boundaries"),
    )


def _parse_operationalization(value: Any, index: int) -> ResearchOperationalization:
    location = f"operationalizations[{index}]"
    required = {"id", "opportunity", "measure", "required_observables", "limitations"}
    if not isinstance(value, Mapping) or set(value) != required:
        raise ValueError(f"{location} must contain exactly {', '.join(sorted(required))}")
    measure = value.get("measure")
    if not isinstance(measure, Mapping) or set(measure) != {"source", "id"}:
        raise ValueError(f"{location}.measure must contain source and id")
    return ResearchOperationalization(
        id=_identifier(value.get("id"), f"{location}.id"),
        opportunity=_identifier(value.get("opportunity"), f"{location}.opportunity"),
        measure=MeasureReference(
            _portable_path(measure.get("source"), f"{location}.measure.source"),
            _identifier(measure.get("id"), f"{location}.measure.id"),
        ),
        required_observables=_text_list(
            value.get("required_observables"), f"{location}.required_observables"
        ),
        limitations=_text_list(
            value.get("limitations"), f"{location}.limitations", non_empty=False
        ),
    )


def _text_list(value: Any, location: str, *, non_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list) or (non_empty and not value):
        raise ValueError(f"{location} must be {'a non-empty' if non_empty else 'a'} list")
    result = tuple(_text(item, location) for item in value)
    if len(set(result)) != len(result):
        raise ValueError(f"{location} contains duplicate values")
    return result


def _text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location} must be a non-empty string")
    return value.strip()


def _identifier(value: Any, location: str) -> str:
    text = _text(value, location)
    if not text[0].isalnum() or any(
        not (character.islower() or character.isdigit() or character in "._-") for character in text
    ):
        raise ValueError(f"{location} must be a portable lowercase identifier")
    return text


def _sha256(value: Any, location: str) -> str:
    text = _text(value, location)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"{location} must be a lowercase SHA-256")
    return text


def _portable_path(value: Any, location: str) -> str:
    text = _text(value, location)
    if "\\" in text:
        raise ValueError(f"{location} must use POSIX separators")
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts or text == ".":
        raise ValueError(f"{location} must remain inside the profile package")
    return path.as_posix()


def _resolve_inside(root: Path, relative: str) -> Path:
    path = (root / PurePosixPath(relative)).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"Profile Measure reference is missing or outside package: {relative}")
    return path


def _unique(values: list[str], label: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"Game Research Profile contains duplicate {label} ids")


__all__ = [
    "GameResearchProfile",
    "MeasureReference",
    "PreparedGameResearchProfile",
    "ResearchOperationalization",
    "ResearchOpportunity",
    "load_game_research_profile",
    "prepare_game_research_profile",
]
