"""Session and configuration data structures for AgentDeck."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from .types import LogLevel

if TYPE_CHECKING:
    from ..monitors import Monitor


@dataclass
class AgentDeckConfig:
    """User-facing configuration for an AgentDeck session."""

    seed: Optional[int] = None
    run_dir: str = "agentdeck_runs"  # Base directory for all session runs
    max_turns: int = 1000
    log_level: Optional[LogLevel] = LogLevel.INFO
    log_file_levels: Optional[List[LogLevel]] = None
    log_format: str = "simple"
    concurrency: int = 1  # Number of parallel workers (1 = sequential)
    monitors: Optional[List["Monitor"]] = None  # Console-level observers (progress, hardware, etc.)

    def __post_init__(self):
        """Validate configuration fields."""
        if self.concurrency < 1:
            raise ValueError(
                f"concurrency must be >= 1, got {self.concurrency}. "
                f"Use concurrency=1 for sequential execution."
            )


@dataclass
class SessionContext:
    """Resolved session metadata derived from :class:`AgentDeckConfig`."""

    config: AgentDeckConfig
    session_id: str
    started_at: float
    log_directory: str
    record_directory: str
    log_file_levels: List[LogLevel] = field(default_factory=list)

    @classmethod
    def create(cls, config: AgentDeckConfig) -> "SessionContext":
        """
        Create a new session context from configuration.

        Per SPEC-AGENTDECK §4: Creates unified directory structure:
        {run_dir}/{session_id}/logs/
        {run_dir}/{session_id}/records/
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        random_suffix = str(uuid.uuid4())[:6]
        session_id = f"session_{timestamp}_{random_suffix}"

        # Unified directory structure: all session artifacts under one root
        session_base = os.path.join(config.run_dir, session_id)
        log_directory = os.path.join(session_base, "logs")
        record_directory = os.path.join(session_base, "records")

        # Default file logging mirrors previous behaviour unless explicitly disabled.
        if config.log_file_levels is None:
            effective_levels = [LogLevel.INFO, LogLevel.DEBUG]
        else:
            effective_levels = list(config.log_file_levels)

        return cls(
            config=config,
            session_id=session_id,
            started_at=time.time(),
            log_directory=log_directory,
            record_directory=record_directory,
            log_file_levels=effective_levels,
        )

    @property
    def seed(self) -> Optional[int]:
        """Expose the configured seed directly."""
        return self.config.seed

    @property
    def max_turns(self) -> int:
        """Expose the configured max turns."""
        return self.config.max_turns

    @property
    def log_level(self) -> Optional[LogLevel]:
        """Expose the configured console log level."""
        return self.config.log_level

    @property
    def log_format(self) -> str:
        """Expose the configured log format."""
        return self.config.log_format

    def ensure_directories(self) -> None:
        """Create log and recording directories if they do not exist."""
        Path(self.log_directory).mkdir(parents=True, exist_ok=True)
        Path(self.record_directory).mkdir(parents=True, exist_ok=True)

    def metadata(self) -> Dict[str, Optional[int]]:
        """Provide a lightweight metadata snapshot for recordings/logs."""
        return {
            "session_id": self.session_id,
            "seed": self.config.seed,
            "started_at": self.started_at,
        }


__all__ = ["AgentDeckConfig", "SessionContext"]

# Backwards compatibility for older spec references
SessionConfig = AgentDeckConfig
__all__.append("SessionConfig")
