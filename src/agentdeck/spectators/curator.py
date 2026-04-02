"""Match metadata curation spectator for replay and showcase pipelines."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from ..core.base.spectator import Spectator
from ..core.types import Event, EventContext, MatchResult

_SIDECAR_VERSION = 1
_MAX_HIGHLIGHT_LABEL = 50
_HIGHLIGHT_KINDS = {"mistake", "smart_move", "surprise", "turning_point"}


@dataclass(frozen=True)
class MatchHighlight:
    """Single highlighted turn for viewer metadata."""

    turn: int
    label: str
    kind: str | None = None


@dataclass(frozen=True)
class MatchTranscriptEntry:
    """Optional commentary transcript entry for a turn."""

    turn: int
    text: str


@dataclass(frozen=True)
class MatchCuratorPayload:
    """Portable sidecar payload written by MatchCurator."""

    version: int
    subtitle: str
    synopsis: str
    highlights: List[MatchHighlight]
    transcript: Optional[List[MatchTranscriptEntry]] = None

    def to_json_dict(self) -> Dict[str, Any]:
        """Serialize payload using plain JSON-compatible types."""
        payload = {
            "version": self.version,
            "subtitle": self.subtitle,
            "synopsis": self.synopsis,
            "highlights": [
                {
                    "turn": item.turn,
                    "label": item.label,
                    **({"kind": item.kind} if item.kind else {}),
                }
                for item in self.highlights
            ],
        }
        if self.transcript:
            payload["transcript"] = [asdict(item) for item in self.transcript]
        return payload


@dataclass(frozen=True)
class CuratorFrame:
    """Normalized per-turn snapshot used by curators."""

    turn: int
    player: str
    action: str
    reasoning: Optional[str]
    state_before: Dict[str, Any]
    state_after: Dict[str, Any]
    timestamp: Optional[float] = None
    prompt_text: Optional[str] = None
    response_text: Optional[str] = None


@dataclass(frozen=True)
class CuratorMatchSnapshot:
    """Full match snapshot passed into curation generators."""

    match_id: Optional[str]
    game: str
    players: List[str]
    winner: Optional[str]
    turns: int
    final_state: Dict[str, Any]
    frames: List[CuratorFrame]
    handshakes: List[Dict[str, Any]]
    conclusions: List[Dict[str, Any]]


CuratorGenerator = Callable[[CuratorMatchSnapshot], MatchCuratorPayload | Dict[str, Any]]


class MatchCurator(Spectator):
    """
    Generate viewer-ready curation sidecars from live or replayed match events.

    MatchCurator is intentionally sidecar-driven. The output contract is stable,
    while the generation strategy is pluggable via the `generator` callable.
    """

    def __init__(
        self,
        *,
        source_path: str | Path | None = None,
        output_path: str | Path | None = None,
        output_dir: str | Path | None = None,
        generator: CuratorGenerator | None = None,
        include_transcript: bool = False,
        logger: Any = None,
    ) -> None:
        super().__init__(logger=logger)
        self.source_path = Path(source_path) if source_path else None
        self.output_path = Path(output_path) if output_path else None
        self.output_dir = Path(output_dir) if output_dir else None
        self.generator = generator or self._default_generate
        self.include_transcript = include_transcript

        self.last_metadata: MatchCuratorPayload | None = None
        self.last_output_path: Path | None = None
        self._reset_match_state()

    def _reset_match_state(self) -> None:
        self.match_id: Optional[str] = None
        self.game_name = "UnknownGame"
        self.player_names: List[str] = []
        self.frames: List[CuratorFrame] = []
        self.handshakes: List[Dict[str, Any]] = []
        self.conclusions: List[Dict[str, Any]] = []

    def on_match_start(
        self,
        game: Any,
        players: List[Any],
        match_id: Optional[str] = None,
        context: Optional[EventContext] = None,
        **kwargs: Any,
    ) -> None:
        """Capture the live match identity and reset state between matches."""
        self._reset_match_state()
        self.match_id = match_id
        self.game_name = game.__class__.__name__ if game else "UnknownGame"
        self.player_names = [p.name for p in players] if players else []

    def on_gameplay(self, event: Event) -> None:
        """Store normalized gameplay frames for later curation."""
        data = event.data or {}
        mechanic = data.get("mechanic")
        if mechanic and mechanic != "turn_based":
            return

        player = data.get("player", "Unknown")
        action = self._normalize_action_text(data.get("action"))
        context = event.context or {}
        turn = self._turn_number(data, context, fallback=len(self.frames) + 1)
        prompt_payload = data.get("prompt") or {}
        frame = CuratorFrame(
            turn=turn,
            player=player,
            action=action,
            reasoning=data.get("reasoning"),
            state_before=self._copy_mapping(data.get("state_before")),
            state_after=self._copy_mapping(data.get("state_after")),
            timestamp=event.timestamp,
            prompt_text=prompt_payload.get("prompt_text") or prompt_payload.get("raw_prompt"),
            response_text=prompt_payload.get("response_text") or prompt_payload.get("raw_response"),
        )
        self.frames.append(frame)

    def on_player_handshake_complete(self, event: Event) -> None:
        """Capture successful handshake metadata."""
        data = event.data or {}
        self.handshakes.append(
            {
                "player": data.get("player", "Unknown"),
                "status": "complete",
                "prompt_text": data.get("prompt_text"),
                "response_text": data.get("response_text"),
                "normalized_response": data.get("normalized_response"),
                "reason": None,
            }
        )

    def on_player_handshake_abort(self, event: Event) -> None:
        """Capture rejected handshake metadata."""
        data = event.data or {}
        self.handshakes.append(
            {
                "player": data.get("player", "Unknown"),
                "status": "abort",
                "prompt_text": data.get("prompt_text"),
                "response_text": data.get("response_text"),
                "normalized_response": data.get("normalized_response"),
                "reason": data.get("reason"),
            }
        )

    def on_player_conclusion(self, event: Event) -> None:
        """Capture player conclusion text for optional transcript use."""
        data = event.data or {}
        self.conclusions.append(
            {
                "player": data.get("player", "Unknown"),
                "reflection_text": data.get("reflection_text"),
                "response_text": data.get("response_text"),
            }
        )

    def on_match_end(self, result: MatchResult, context: Optional[EventContext] = None) -> None:
        """Generate curation metadata and optionally write a sidecar."""
        snapshot = CuratorMatchSnapshot(
            match_id=self.match_id,
            game=self.game_name,
            players=list(self.player_names),
            winner=result.winner,
            turns=int(result.metadata.get("turns", len(self.frames) or 0)),
            final_state=self._copy_mapping(result.final_state),
            frames=list(self.frames),
            handshakes=list(self.handshakes),
            conclusions=list(self.conclusions),
        )

        payload = self._normalize_payload(self.generator(snapshot))
        self.last_metadata = payload

        target = self._resolve_output_path()
        self.last_output_path = target
        if target is not None:
            self._write_sidecar(target, payload)
            if self.logger:
                self.logger.info(f"MatchCurator wrote sidecar: {target}")

    def _resolve_output_path(self) -> Path | None:
        if self.output_path is not None:
            return self.output_path
        if self.source_path is not None:
            return self.source_path.with_suffix(".meta.json")
        if self.output_dir is not None and self.match_id:
            return self.output_dir / f"{self.match_id}.meta.json"
        return None

    def _write_sidecar(self, target: Path, payload: MatchCuratorPayload) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload.to_json_dict(), indent=2) + "\n",
            encoding="utf-8",
        )

    def _normalize_payload(self, payload: MatchCuratorPayload | Dict[str, Any]) -> MatchCuratorPayload:
        if isinstance(payload, MatchCuratorPayload):
            self._validate_payload(payload)
            return payload

        subtitle = self._require_string(payload, "subtitle")
        synopsis = self._require_string(payload, "synopsis")
        highlights_raw = payload.get("highlights")
        if not isinstance(highlights_raw, Sequence):
            raise ValueError("MatchCurator payload must include highlights as an array")

        highlights = [
            MatchHighlight(
                turn=int(item["turn"]),
                label=self._normalize_highlight_label(item["label"]),
                kind=self._normalize_highlight_kind(item.get("kind")),
            )
            for item in highlights_raw
        ]
        transcript_raw = payload.get("transcript")
        transcript = None
        if transcript_raw is not None:
            if not isinstance(transcript_raw, Sequence):
                raise ValueError("MatchCurator transcript must be an array when provided")
            transcript = [
                MatchTranscriptEntry(turn=int(item["turn"]), text=self._require_string(item, "text"))
                for item in transcript_raw
            ]

        normalized = MatchCuratorPayload(
            version=int(payload.get("version", _SIDECAR_VERSION)),
            subtitle=subtitle,
            synopsis=synopsis,
            highlights=highlights,
            transcript=transcript,
        )
        self._validate_payload(normalized)
        return normalized

    def _validate_payload(self, payload: MatchCuratorPayload) -> None:
        if payload.version < 1:
            raise ValueError("MatchCurator payload version must be >= 1")
        if not payload.subtitle.strip():
            raise ValueError("MatchCurator subtitle must be non-empty")
        if not payload.synopsis.strip():
            raise ValueError("MatchCurator synopsis must be non-empty")
        if not payload.highlights:
            raise ValueError("MatchCurator must produce at least one highlight")

        for highlight in payload.highlights:
            if highlight.turn < 1:
                raise ValueError("MatchCurator highlights must use 1-based turn numbers")
            self._normalize_highlight_label(highlight.label)
            self._normalize_highlight_kind(highlight.kind)

    def _default_generate(self, snapshot: CuratorMatchSnapshot) -> MatchCuratorPayload:
        turns = snapshot.turns or len(snapshot.frames)
        decisive = self._select_decisive_frame(snapshot.frames)
        subtitle = self._build_subtitle(snapshot, decisive, turns)
        synopsis = self._build_synopsis(snapshot, decisive, turns)
        highlights = self._build_highlights(snapshot.frames, decisive, turns)
        transcript = self._build_transcript(snapshot.frames) if self.include_transcript else None

        return MatchCuratorPayload(
            version=_SIDECAR_VERSION,
            subtitle=subtitle,
            synopsis=synopsis,
            highlights=highlights,
            transcript=transcript,
        )

    def _build_subtitle(
        self,
        snapshot: CuratorMatchSnapshot,
        decisive: CuratorFrame | None,
        turns: int,
    ) -> str:
        winner = snapshot.winner or "No one"
        if decisive and decisive.action == "POTION":
            return f"{winner} survives the swing and closes"
        if decisive:
            return f"{winner} takes control on turn {decisive.turn}"
        return f"{winner} closes out a {turns}-turn fight"

    def _build_synopsis(
        self,
        snapshot: CuratorMatchSnapshot,
        decisive: CuratorFrame | None,
        turns: int,
    ) -> str:
        winner = snapshot.winner or "No one"
        if decisive:
            state_after = decisive.state_after.get("health", {})
            target, hp = self._lowest_health_target(state_after, exclude=decisive.player)
            if target and hp is not None:
                return (
                    f"{winner} wins after {turns} turns. The decisive moment lands on turn "
                    f"{decisive.turn}, when {target} drops to {hp} HP after {decisive.player}'s "
                    f"{decisive.action.lower()}."
                )
        return f"{winner} wins after {turns} turns in a controlled replayed match."

    def _build_highlights(
        self,
        frames: Sequence[CuratorFrame],
        decisive: CuratorFrame | None,
        turns: int,
    ) -> List[MatchHighlight]:
        highlights: List[MatchHighlight] = []
        seen_turns: set[int] = set()

        def add(turn: int, label: str, *, kind: str | None = None) -> None:
            if turn in seen_turns:
                return
            seen_turns.add(turn)
            highlights.append(
                MatchHighlight(
                    turn=turn,
                    label=self._normalize_highlight_label(label),
                    kind=self._normalize_highlight_kind(kind),
                )
            )

        potion_frame = next((frame for frame in frames if frame.action == "POTION"), None)
        if potion_frame is not None:
            add(potion_frame.turn, f"{potion_frame.player} uses recovery", kind="smart_move")

        if decisive is not None:
            target, hp = self._lowest_health_target(decisive.state_after.get("health", {}), exclude=decisive.player)
            if target and hp is not None:
                add(decisive.turn, f"{target} falls to {hp} HP", kind="turning_point")
            else:
                add(decisive.turn, f"{decisive.player} lands the swing", kind="turning_point")

        add(turns, "Match closes out", kind="turning_point")
        return highlights[:3]

    def _build_transcript(self, frames: Sequence[CuratorFrame]) -> List[MatchTranscriptEntry]:
        transcript: List[MatchTranscriptEntry] = []
        for frame in frames:
            target, hp = self._lowest_health_target(frame.state_after.get("health", {}), exclude=frame.player)
            if target and hp is not None:
                text = f"Turn {frame.turn}: {frame.player} uses {frame.action} and leaves {target} at {hp} HP."
            else:
                text = f"Turn {frame.turn}: {frame.player} uses {frame.action}."
            transcript.append(MatchTranscriptEntry(turn=frame.turn, text=text))
        return transcript

    def _select_decisive_frame(self, frames: Sequence[CuratorFrame]) -> CuratorFrame | None:
        best: CuratorFrame | None = None
        best_score = float("-inf")
        for frame in frames:
            score = 0.0
            before = frame.state_before.get("health", {})
            after = frame.state_after.get("health", {})
            for player, before_hp in before.items():
                after_hp = after.get(player, before_hp)
                score = max(score, float(before_hp) - float(after_hp))
                if after_hp <= 0 < before_hp:
                    score += 1000
            if frame.action == "POTION":
                for player, before_hp in before.items():
                    after_hp = after.get(player, before_hp)
                    if after_hp > before_hp:
                        score = max(score, float(after_hp) - float(before_hp) + 100)
            if score > best_score:
                best = frame
                best_score = score
        return best

    def _lowest_health_target(
        self,
        health_state: Dict[str, Any],
        *,
        exclude: str | None = None,
    ) -> tuple[str | None, int | None]:
        candidates = [
            (name, int(hp))
            for name, hp in (health_state or {}).items()
            if name != exclude
        ]
        if not candidates:
            return None, None
        target, hp = min(candidates, key=lambda item: item[1])
        return target, hp

    def _turn_number(self, data: Dict[str, Any], context: Dict[str, Any], *, fallback: int) -> int:
        turn_context = data.get("turn_context") or {}
        turn = (
            turn_context.get("turn_number")
            or context.get("turn_index")
            or context.get("phase_index")
            or data.get("turn")
        )
        if isinstance(turn, int) and turn > 0:
            if "turn_index" in context or "phase_index" in context:
                return turn if turn_context.get("turn_number") else turn + 1
            return turn
        return fallback

    def _normalize_action_text(self, action: Any) -> str:
        if isinstance(action, dict):
            return str(action.get("action", "UNKNOWN"))
        if hasattr(action, "action"):
            return str(getattr(action, "action", "UNKNOWN"))
        if action is None:
            return "UNKNOWN"
        return str(action)

    def _copy_mapping(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return json.loads(json.dumps(value))
        return {}

    def _normalize_highlight_label(self, label: str) -> str:
        text = str(label).strip()
        if not text:
            raise ValueError("MatchCurator highlight labels must be non-empty")
        if len(text) > _MAX_HIGHLIGHT_LABEL:
            raise ValueError(
                f"MatchCurator highlight labels must be <= {_MAX_HIGHLIGHT_LABEL} characters"
            )
        return text

    def _normalize_highlight_kind(self, kind: Any) -> str | None:
        if kind is None:
            return None
        text = str(kind).strip()
        if not text:
            return None
        if text not in _HIGHLIGHT_KINDS:
            allowed = ", ".join(sorted(_HIGHLIGHT_KINDS))
            raise ValueError(f"MatchCurator highlight kind must be one of: {allowed}")
        return text

    def _require_string(self, payload: Dict[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"MatchCurator payload must include non-empty {key}")
        return value.strip()


def curate_match_file(
    match_path: str | Path,
    *,
    curator: MatchCurator | None = None,
    speed: float = 0.0,
) -> MatchCurator:
    """
    Replay a recorded match through MatchCurator and return the populated spectator.

    This is a thin convenience wrapper for sidecar generation workflows.
    """
    from ..core.replay import ReplayEngine

    source_path = Path(match_path)
    with source_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    active_curator = curator or MatchCurator(source_path=source_path)
    ReplayEngine(payload).replay(spectators=[active_curator], speed=speed)
    return active_curator
