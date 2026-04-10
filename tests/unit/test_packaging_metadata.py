from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_pyproject_declares_research_cli_entry_points() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    expected = [
        'agentdeck-research-export = "agentdeck.research.export:main"',
        'agentdeck-research-index = "agentdeck.research.index:main"',
        'agentdeck-research-package = "agentdeck.research.packager:main"',
        'agentdeck-research-score = "agentdeck.research.score:main"',
        'agentdeck-research-validate = "agentdeck.research.validate:main"',
    ]

    for entry in expected:
        assert entry in pyproject
