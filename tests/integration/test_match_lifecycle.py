"""
Integration tests for full match lifecycle.

Validates complete execution: AgentDeck setup → handshake → match → recording → spectators.
Uses real components (FixedDamageGame, MockPlayer) per TEST-PLAN §4.1.
"""

import copy
import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from agentdeck import (
    ActionResult,
    AgentDeck,
    AgentDeckConfig,
    FixedDamageGame,
    Game,
    GameStatus,
    MockPlayer,
    RandomGenerator,
    TurnContext,
    TurnResult,
)
from agentdeck.core.types import Event


class SimultaneousDecisionGame(Game):
    """Minimal custom mechanic that records two decisions without internal counters."""

    @property
    def instructions(self) -> str:
        return "Both Players choose once, simultaneously."

    @property
    def allowed_actions(self) -> list[str]:
        return ["WAIT"]

    @property
    def default_handshake_template(self) -> str:
        return "{game_instructions}\n\n{controller_format}\n\n{handshake_controller_format}"

    def setup(self, players: list[str], seed: int) -> dict[str, Any]:
        return {"players": list(players), "seed": seed, "resolved": False, "winner": None}

    def update(
        self,
        game_state: dict[str, Any],
        player: str,
        action: ActionResult,
        *,
        rng: RandomGenerator,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def status(self, game_state: dict[str, Any]) -> GameStatus:
        return GameStatus(is_over=game_state["resolved"], winner=game_state["winner"])

    def get_view(self, game_state: dict[str, Any], player: str) -> dict[str, Any]:
        return {"resolved": game_state["resolved"], "player": player}

    def run(self, runtime, players) -> TurnResult:
        before = copy.deepcopy(runtime.initial_state)
        after = copy.deepcopy(before)
        after["resolved"] = True
        for index, player in enumerate(players):
            runtime.record_turn(
                player=player.name,
                state_before=before,
                state_after=after,
                action=ActionResult(action="WAIT", raw_response="WAIT"),
                turn_context=TurnContext(
                    match_id=runtime.match_id,
                    turn_number=1,
                    turn_index=index,
                    player=player.name,
                    started_at=0.0,
                    duration=0.0,
                    rng_seed=runtime.seed,
                    rng_label=f"simultaneous-{player.name}",
                ),
            )
        return TurnResult(final_state=after, events=[], truncated_by_max_turns=False)


@pytest.fixture
def temp_record_dir():
    """Temporary directory for recording files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def players():
    """Two mock players."""
    return [MockPlayer(name="Alice"), MockPlayer(name="Bob")]


@pytest.fixture
def tracking_spectator():
    """Spectator that tracks all received events."""

    class TrackingSpectator:
        def __init__(self):
            self.events = []
            self.event_types = []

        def on_event(self, event: Event):
            self.events.append(event)
            self.event_types.append(event.type)

    return TrackingSpectator()


def test_full_match_lifecycle(players, temp_record_dir, tracking_spectator):
    """
    Integration: Full match from setup to conclusion.

    Validates Console orchestration, turn execution, event ordering, recording persistence.
    """
    game = FixedDamageGame()
    config = AgentDeckConfig(run_dir=str(temp_record_dir), seed=42)

    deck = AgentDeck(game=game, session=config, spectators=[tracking_spectator])
    results = deck.play(players=players, matches=1)

    # Match completed
    assert len(results) == 1
    assert results[0].winner is not None
    assert results[0].final_state is not None

    # Event ordering
    event_types = tracking_spectator.event_types
    assert "session_start" in event_types
    assert "batch_start" in event_types
    assert "match_start" in event_types
    assert "match_end" in event_types
    assert "batch_end" in event_types

    # Proper nesting
    assert event_types.index("session_start") < event_types.index("batch_start")
    assert event_types.index("batch_start") < event_types.index("match_start")
    assert event_types.index("match_start") < event_types.index("match_end")
    assert event_types.index("match_end") < event_types.index("batch_end")

    # Recording exists (in session subdirectory)
    recordings = list(temp_record_dir.glob("**/*.json"))
    assert len(recordings) >= 1, f"Expected recordings in {temp_record_dir}"

    # Find the batch recording
    batch_recording = [r for r in recordings if "batch" in r.name][0]

    with open(batch_recording) as f:
        batch_data = json.load(f)

    # New schema v1.1: batch has match_refs, not inline matches
    assert "match_refs" in batch_data
    assert len(batch_data["match_refs"]) == 1
    assert batch_data["match_refs"][0]["winner"] is not None

    # Batch ID must be consistent between logger output and persisted artifacts.
    batch_id = batch_data["batch_id"]
    info_log = batch_recording.parent.parent / "logs" / "info.log"
    assert info_log.exists(), f"Missing info log at {info_log}"
    info_text = info_log.read_text(encoding="utf-8")
    assert f"Batch {batch_id} starting" in info_text
    assert f"Batch {batch_id} complete" in info_text

    # Match artifact should also expose the same batch_id at top-level.
    match_filename = batch_data["match_refs"][0]["filename"]
    match_recording = batch_recording.parent / match_filename
    with open(match_recording) as f:
        match_data = json.load(f)
    assert match_data["batch_id"] == batch_id


def test_custom_mechanic_turn_metadata_counts_recorded_gameplay_events(players, temp_record_dir):
    """SPEC-CONSOLE M1: custom mechanics cannot leave turn metadata stale."""
    config = AgentDeckConfig(run_dir=str(temp_record_dir), seed=42)

    with AgentDeck(game=SimultaneousDecisionGame(), session=config) as deck:
        results = deck.play(players=players, matches=1)
        record_path = next(Path(deck.session.record_directory).glob("match_*.json"))

    result = results[0]
    gameplay_events = [event for event in result.events if event.type == "gameplay"]
    assert len(gameplay_events) == 2
    assert result.final_state["_turn_count"] == 1
    assert result.metadata["turns"] == 2

    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["metadata"]["match"]["turns"] == 2


def test_spectator_isolation(players, temp_record_dir):
    """
    Integration: Spectators receive isolated event copies (EP1-EP2).
    """

    class MutatingSpectator:
        def __init__(self, name):
            self.name = name
            self.match_start = None

        def on_match_start(self, event: Event):
            self.match_start = event
            event.data["game"] = f"MUTATED_{self.name}"

    spec1 = MutatingSpectator("S1")
    spec2 = MutatingSpectator("S2")

    config = AgentDeckConfig(run_dir=str(temp_record_dir), seed=42)
    deck = AgentDeck(game=FixedDamageGame(), session=config, spectators=[spec1, spec2])
    deck.play(players=players, matches=1)

    # Both received events
    assert spec1.match_start is not None
    assert spec2.match_start is not None

    # Mutations isolated
    assert spec1.match_start.data["game"] == "MUTATED_S1"
    assert spec2.match_start.data["game"] == "MUTATED_S2"


def test_deterministic_with_seed(players, temp_record_dir):
    """
    Integration: Same seed produces identical outcomes (DT2).
    """
    config1 = AgentDeckConfig(run_dir=str(temp_record_dir / "r1"), seed=12345)
    deck1 = AgentDeck(game=FixedDamageGame(), session=config1)
    results1 = deck1.play(players=[MockPlayer(name="Alice"), MockPlayer(name="Bob")], matches=1)

    config2 = AgentDeckConfig(run_dir=str(temp_record_dir / "r2"), seed=12345)
    deck2 = AgentDeck(game=FixedDamageGame(), session=config2)
    results2 = deck2.play(players=[MockPlayer(name="Alice"), MockPlayer(name="Bob")], matches=1)

    # Identical outcomes
    assert results1[0].winner == results2[0].winner
    assert results1[0].final_state == results2[0].final_state


def test_spectator_exception_isolation(players, temp_record_dir):
    """
    Integration: Spectator crashes don't stop match execution (EI1-EI3).
    """

    class CrashingSpectator:
        def on_match_start(self, event):
            raise RuntimeError("Intentional crash")

    class HealthySpectator:
        def __init__(self):
            self.event_count = 0

        def on_event(self, event):
            self.event_count += 1

    crashing = CrashingSpectator()
    healthy = HealthySpectator()

    config = AgentDeckConfig(run_dir=str(temp_record_dir), seed=42)
    deck = AgentDeck(game=FixedDamageGame(), session=config, spectators=[crashing, healthy])
    results = deck.play(players=players, matches=1)

    # Match completed despite crash
    assert len(results) == 1
    assert results[0].winner is not None

    # Healthy spectator still received events
    assert healthy.event_count > 0


def test_multi_match_session(players, temp_record_dir):
    """
    Integration: Multiple matches in one session.
    """
    config = AgentDeckConfig(run_dir=str(temp_record_dir), seed=42)
    deck = AgentDeck(game=FixedDamageGame(), session=config)
    results = deck.play(players=players, matches=3)

    # All matches completed
    assert len(results) == 3
    for result in results:
        assert result.winner is not None

    # Recording has all matches
    recordings = list(temp_record_dir.glob("**/*.json"))
    batch_recording = [r for r in recordings if "batch" in r.name][0]
    with open(batch_recording) as f:
        batch_data = json.load(f)

    # New schema v1.1: batch has match_refs
    assert len(batch_data["match_refs"]) == 3


def test_parallel_match_recordings_include_gameplay_events(players, temp_record_dir):
    """
    Integration: Parallel execution still records gameplay turn events per match.

    Regression guard:
    In parallel mode, worker gameplay events must be replayed to the main EventBus
    so Recorder persists turn-level events (not only handshake/conclusion).
    """
    config = AgentDeckConfig(run_dir=str(temp_record_dir), seed=42, concurrency=4)
    deck = AgentDeck(game=FixedDamageGame(), session=config)
    results = deck.play(players=players, matches=4)

    assert len(results) == 4

    recordings = list(temp_record_dir.glob("**/*.json"))
    batch_recording = [r for r in recordings if "batch" in r.name][0]
    with open(batch_recording) as f:
        batch_data = json.load(f)

    assert len(batch_data["match_refs"]) == 4

    for ref in batch_data["match_refs"]:
        match_path = batch_recording.parent / ref["filename"]
        with open(match_path) as f:
            match_data = json.load(f)

        gameplay_events = [e for e in match_data.get("events", []) if e.get("type") == "gameplay"]
        assert gameplay_events, f"Expected gameplay events in {match_path.name}"
