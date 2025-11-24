"""
Built-in prompt templates bundled with AgentDeck.

Provides paths to reusable template files (e.g., conclusion reflections).
"""

from pathlib import Path

# Path to the default conclusion template (SPEC-PLAYER v1.0.0)
DEFAULT_CONCLUSION_TEMPLATE_PATH = Path(__file__).with_name("default_conclusion.txt")

__all__ = ["DEFAULT_CONCLUSION_TEMPLATE_PATH"]
