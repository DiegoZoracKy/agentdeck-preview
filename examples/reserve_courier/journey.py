"""Run this example with an installed AgentDeck; outputs never enter its Study source."""

from __future__ import annotations

import argparse
import copy
import itertools
import json
import os
from pathlib import Path
import random
import subprocess
import sys

import yaml

SOURCE = Path(__file__).resolve().parent / "study"
sys.path.insert(0, str(SOURCE))
previous_bytecode_policy = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    from courier_game import ReserveCourierGame
    from components import (
        CalibrationPlayer,
        DecisionTrail,
        JsonActionController,
        JsonViewRenderer,
        ProgressProbe,
    )
finally:
    sys.dont_write_bytecode = previous_bytecode_policy
from agentdeck import (
    ActionOnlyController,
    ActionResult,
    AgentDeck,
    AgentDeckConfig,
    ConclusionPolicy,
    ReplayEngine,
    load_evidence,
    prepare_game_research_profile,
)

OFFLINE = """
import runpy, socket
def blocked(*args, **kwargs):
    raise RuntimeError('Network disabled for offline verification')
socket.socket.connect = socket.socket.connect_ex = socket.create_connection = blocked
runpy.run_module('agentdeck.cli', run_name='__main__')
"""


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def cli(root, label, *args, online=False, allow_failure=False):
    command = [sys.executable, "-m", "agentdeck.cli"] if online else [sys.executable, "-c", OFFLINE]
    result = subprocess.run(
        command + ["study", *map(str, args), "--json"],
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    (root / f"{label}.stderr.log").write_text(result.stderr, encoding="utf-8")
    if not result.stdout.strip():
        raise RuntimeError(f"{label} did not return JSON; see {root / (label + '.stderr.log')}")
    envelope = json.loads(result.stdout)
    write(root / f"{label}.json", envelope)
    if not allow_failure and (result.returncode or not envelope["ok"]):
        raise RuntimeError(
            f"{label} failed; retained diagnostic and partial receipt: {root / (label + '.json')}"
        )
    return envelope


def artifact(envelope, field):
    data = envelope["data"]
    return Path(data["output_root"]) / data[field]


def oracle():
    """Check every schedule in all 18 distinct worlds, independent of the Player."""
    game = ReserveCourierGame()
    worlds = {}
    for seed in range(1000):
        state = game.setup(["Courier"], seed)
        worlds[(state["reserve"], tuple(state["express_rewards"]))] = state
    assert len(worlds) == 18
    for initial in worlds.values():
        scores = []
        for actions in itertools.product(game.allowed_actions, repeat=3):
            state = copy.deepcopy(initial)
            for action in actions:
                if state["done"]:
                    break
                before = copy.deepcopy(state)
                state = game.update(
                    state, "Courier", ActionResult(action=action), rng=random.Random(1)
                )
                assert before != state
            scores.append(state["score"])
        assert max(scores) == 15 and min(scores) == 0
        view = game.get_view(initial, "Courier")
        view["express_rewards"].clear()
        assert len(initial["express_rewards"]) == 3
    controller = JsonActionController()
    controller.bind_game(game)
    for response in (
        "SAFE",
        '{"action":"SAFE","action":"EXPRESS"}',
        '{"action":"UNKNOWN"}',
        '{"action":"SAFE","extra":1}',
    ):
        assert not controller.parse(response).success
    assert controller.parse('{"action":"SAFE"}').success
    return {"worlds": len(worlds), "schedules_per_world": 8, "optimal_score": 15}


def showcase(root, extended):
    trail, monitor = DecisionTrail(), ProgressProbe()
    player = CalibrationPlayer(
        "Courier",
        controller=JsonActionController() if extended else ActionOnlyController(),
        renderer=JsonViewRenderer() if extended else None,
        conclusion_template=None,
    )
    session = AgentDeckConfig(
        run_dir=str(root / "play"),
        seed=73,
        concurrency=2 if extended else 1,
        monitors=[],
        max_turns=3,
        log_level=None,
        log_file_levels=[],
        conclusion=ConclusionPolicy(enabled=False),
    )
    with AgentDeck(
        game=ReserveCourierGame(),
        session=session,
        spectators=[trail] if extended else None,
        runtime_monitors=[monitor] if extended else None,
    ) as deck:
        batch = deck.play([player], matches=2 if extended else 1)
    assert all(match.final_state["score"] == 15 for match in batch.matches)
    if extended:
        assert len(trail.rows) == len(monitor.turns) == 6
    return {
        "scores": [m.final_state["score"] for m in batch.matches],
        "spectator_turns": len(trail.rows),
        "monitor_turns": len(monitor.turns),
    }


def research(root, label, execution):
    receipt = artifact(execution, "receipt_path")
    cells = [
        run["cell_id"]
        for group in execution["data"]["execution"]["groups"]
        for run in group["runs"]
    ]
    args = ["analyze", SOURCE, "--execution", receipt, "--measure", "courier-behavior"]
    for cell in cells:
        args.extend(["--cell", cell])
    first = cli(root, f"{label}-analysis", *args, "--output-root", root / "analysis")
    second = cli(root, f"{label}-reproduced", *args, "--output-root", root / "reproduced")
    assert first["data"]["analysis"] == second["data"]["analysis"]
    evidence_path = Path(first["data"]["output_root"]) / "evidence/courier-behavior.json"
    repeated_path = Path(second["data"]["output_root"]) / "evidence/courier-behavior.json"
    assert evidence_path.read_bytes() == repeated_path.read_bytes()
    evidence = json.loads(evidence_path.read_text())
    assert evidence["derivation_status"] == "complete"
    citations = [
        {
            "relation": "supports",
            "evidence": "sha256:" + evidence["evidence_sha256"],
            "result": "sha256:" + r["result_sha256"],
        }
        for r in evidence["results"]
        if r["metric"] == "terminal-observation-rate"
    ]
    finding = {
        "id": f"courier-{label}-qa",
        "claim": "These results document the terminal observation coverage of this bounded product journey. They do not establish the proposed advice or rationale hypotheses.",
        "author": {"name": "Reserve Courier example authors", "kind": "ai"},
        "citations": citations,
        "limitations": [
            "Calibration policies are authored software, not AI evidence.",
            "The smoke has one match per cell; repeated worlds are not independent scenarios.",
            "Rationale is stated text, not hidden internal reasoning. The 384-token cap is part of the treatment.",
            "Extensions vary multiple settings together and serve only integration QA.",
            "Hashes establish artifact identity; they do not certify scientific validity.",
        ],
    }
    manifest = root / f"{label}-findings.yaml"
    manifest.write_text(
        yaml.safe_dump({"schema_version": 1, "findings": [finding]}, sort_keys=False)
    )
    args = ("report", manifest, "--finding", finding["id"], "--evidence", evidence_path)
    report = cli(root, f"{label}-report", *args, "--output", root / f"{label}-report")
    reproduced = cli(
        root, f"{label}-report-reproduced", *args, "--output", root / f"{label}-report-reproduced"
    )
    assert (
        artifact(report, "report_path").read_bytes()
        == artifact(reproduced, "report_path").read_bytes()
    )
    bad = copy.deepcopy(finding)
    bad["citations"][0]["result"] = "sha256:" + "0" * 64
    invalid = root / f"{label}-invalid-citation.yaml"
    invalid.write_text(yaml.safe_dump({"schema_version": 1, "findings": [bad]}, sort_keys=False))
    rejected = cli(
        root,
        f"{label}-invalid-citation",
        "report",
        invalid,
        "--finding",
        bad["id"],
        "--evidence",
        evidence_path,
        "--output",
        root / f"{label}-invalid-report",
        allow_failure=True,
    )
    assert not rejected["ok"]
    tampered = copy.deepcopy(evidence)
    tampered["results"][0]["value"] = 999
    tamper_path = root / f"{label}-tampered-evidence.json"
    write(tamper_path, tampered)
    try:
        load_evidence(tamper_path)
    except ValueError:
        pass
    else:
        raise AssertionError("Changed Evidence was accepted")
    return evidence, {
        "evidence_bytes_equal": True,
        "report_bytes_equal": True,
        "invalid_citation_rejected": True,
        "tampered_evidence_rejected": True,
        "offline": True,
        "evidence_sha256": evidence["evidence_sha256"],
        "report": str(artifact(report, "report_path").relative_to(root)),
    }


def run(root, live, approved):
    profile = prepare_game_research_profile(SOURCE / "research-profile.yaml")
    inspected = cli(root, "inspect", "inspect", SOURCE)
    plan = inspected["plan_sha256"]
    if live and approved != plan:
        raise ValueError(
            f"Inspect the Study and pass --approve {plan} to select the bounded provider smoke"
        )
    cli(root, "validate", "validate", SOURCE)
    local = cli(
        root,
        "local-execution",
        "run",
        SOURCE,
        "--group",
        "calibration",
        "--group",
        "extensions",
        "--approve",
        plan,
        "--output-root",
        root / "runs",
    )
    evidence, checks = research(root, "local", local)
    means = {
        r["dimensions"]["cell"]: r["value"]
        for r in evidence["results"]
        if r["metric"] == "mean-score"
    }
    assert means == {
        "calibration-optimal": 15,
        "calibration-greedy": 0,
        "calibration-conservative": 6,
        "extension-json": 15,
        "extension-rationale": 15,
    }
    results = {
        "plan_sha256": plan,
        "profile_sha256": profile.profile_sha256,
        "calibration_means": means,
        "local": checks,
    }
    if live:
        smoke = cli(
            root,
            "smoke-execution",
            "run",
            SOURCE,
            "--group",
            "smoke",
            "--approve",
            plan,
            "--output-root",
            root / "runs",
            online=True,
        )
        _, results["smoke"] = research(root, "smoke", smoke)
        results["usage"] = smoke["data"]["execution"]["usage"]
    records = sorted((root / "runs").rglob("match_*.json"))
    replayed = 0
    for path in records:
        payload = json.loads(path.read_text())
        spectator = DecisionTrail()
        ReplayEngine(payload).replay([spectator], speed=0)
        assert len(spectator.rows) == sum(e["type"] == "gameplay" for e in payload["events"])
        replayed += len(spectator.rows)
    results.update(record_count=len(records), replayed_turns=replayed)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["basic", "extended", "local", "smoke"])
    parser.add_argument(
        "--output-root", type=Path, required=True, help="New directory outside the authored Study"
    )
    parser.add_argument("--approve", help="Exact inspected Study plan hash; required for smoke")
    args = parser.parse_args()
    root = args.output_root.resolve()
    if root == SOURCE or SOURCE in root.parents:
        parser.error("Outputs must be outside the authored Study source")
    root.mkdir(parents=True, exist_ok=False)
    summary = {"oracle": oracle(), "mode": args.mode}
    summary.update(
        showcase(root, args.mode == "extended")
        if args.mode in {"basic", "extended"}
        else run(root, args.mode == "smoke", args.approve)
    )
    write(root / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
