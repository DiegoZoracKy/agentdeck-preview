import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_node(script: str) -> None:
    result = subprocess.run(
        ["node", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"Node script failed: {script}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def test_viewer_contracts():
    """SPEC-VIEWER: loader, timeline, and registry contracts hold in Node."""
    _run_node("tests/viewer/viewer_contracts.js")


def test_viewer_smoke_check():
    """SPEC-VIEWER: shipped sample record and bundled renderers pass the smoke check."""
    _run_node("scripts/viewer_smoke_check.js")


def test_hidden_signal_reference_stage():
    """The current Match Surface reference remains factual, pinned, and watchable."""
    _run_node("tests/viewer/hidden_signal_stage.js")
