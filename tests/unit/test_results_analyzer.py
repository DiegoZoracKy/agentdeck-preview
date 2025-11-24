import csv

from agentdeck.core.types import Event, MatchResult, MatchResults
from agentdeck.research.analysis import ResultsAnalyzer


def _match_result(gameplay_count: int, extra_turn_events: int = 0, seed: int = 1) -> MatchResult:
    events = []
    for _ in range(gameplay_count):
        events.append(Event(type="gameplay", data={}, context={}))
    for _ in range(extra_turn_events):
        events.append(Event(type="turn", data={}, context={}))

    return MatchResult(
        winner="Alice",
        final_state={},
        events=events,
        seed=seed,
        metadata={"duration": 1.0, "players": ["Alice", "Bob"]},
    )


def test_export_csv_counts_gameplay_events(tmp_path):
    results = MatchResults(
        matches=[
            _match_result(gameplay_count=2, extra_turn_events=1, seed=10),
            _match_result(gameplay_count=1, extra_turn_events=2, seed=11),
        ]
    )

    analyzer = ResultsAnalyzer(results)
    output_path = tmp_path / "results.csv"
    analyzer.export_csv(output_path)

    with output_path.open() as f:
        rows = list(csv.DictReader(f))

    assert rows[0]["turns"] == "2"
    assert rows[1]["turns"] == "1"
