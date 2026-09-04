"""The documented user journey must reach Research through installed public APIs."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

EXAMPLE = Path(__file__).resolve().parents[2] / "examples/reserve_courier/journey.py"


@pytest.mark.parametrize("mode", ["basic", "extended", "local"])
def test_reserve_courier_user_journey(tmp_path, mode):
    example = tmp_path / "example"
    shutil.copytree(EXAMPLE.parent, example, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    env = dict(os.environ)
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    env.pop("PYTHONPYCACHEPREFIX", None)
    output = tmp_path / mode
    result = subprocess.run(
        [sys.executable, str(example / "journey.py"), mode, "--output-root", str(output)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not list((example / "study").rglob("__pycache__"))
    summary = json.loads((output / "summary.json").read_text())
    assert summary["oracle"]["worlds"] == 18
    if mode == "local":
        assert summary["record_count"] == 16
        assert summary["local"]["evidence_bytes_equal"]
        assert summary["local"]["report_bytes_equal"]
        assert summary["local"]["offline"]
        assert summary["local"]["invalid_citation_rejected"]
    else:
        assert set(summary["scores"]) == {15}
        if mode == "extended":
            assert summary["spectator_turns"] == summary["monitor_turns"] == 6

    again = subprocess.run(
        [sys.executable, str(example / "journey.py"), mode, "--output-root", str(output)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert again.returncode != 0
    assert "FileExistsError" in again.stderr
