"""Structured logging utilities for AgentDeck."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .session import SessionContext
from .types import LogLevel


def _level_to_logging(level: LogLevel) -> int:
    mapping = {
        LogLevel.INFO: logging.INFO,
        LogLevel.DEBUG: logging.DEBUG,
    }
    return mapping[level]


def _format_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class LogContext:
    """Hierarchical logging context shared with handlers."""

    session_id: str
    batch_id: Optional[str] = None
    match_id: Optional[str] = None
    turn_number: Optional[int] = None
    turn_index: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "batch_id": self.batch_id,
            "match_id": self.match_id,
            "turn_number": self.turn_number,
            "turn_index": self.turn_index,
        }

    def update(self, **fields: Any) -> None:
        for key, value in fields.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise KeyError(
                    f"Invalid LogContext field: {key}. "
                    f"Valid fields: session_id, batch_id, match_id, turn_number, turn_index"
                )


@dataclass
class LoggingConfig:
    """Runtime configuration for :class:`AgentDeckLogger`."""

    console_level: Optional[LogLevel] = LogLevel.INFO
    file_levels: Sequence[LogLevel] = field(default_factory=tuple)
    log_format: str = "simple"
    turn_style: str = "summary"  # summary | full | diff | silent
    max_state_chars: int = 1200
    include_state_diff: bool = True
    extra_handlers: Sequence[logging.Handler] = field(default_factory=tuple)

    @classmethod
    def from_session(cls, session: SessionContext) -> "LoggingConfig":
        return cls(
            console_level=session.log_level,
            file_levels=session.log_file_levels,
            log_format=session.log_format,
        )


class AgentDeckLogger:
    """Session-scoped structured logger."""

    def __init__(self, session: SessionContext, config: Optional[LoggingConfig] = None) -> None:
        self.session = session
        self.config = config or LoggingConfig.from_session(session)
        self.log_dir = Path(session.log_directory)
        self.context = LogContext(session_id=session.session_id)

        self._logger = logging.getLogger(f"agentdeck.{session.session_id}")
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers.clear()
        # Prevent propagation to root logger to avoid duplicate output
        self._logger.propagate = False
        self._install_handlers()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def with_batch(self, batch_id: Optional[str]) -> None:
        self.context.update(batch_id=batch_id)

    def with_match(self, match_id: Optional[str]) -> None:
        self.context.update(match_id=match_id, turn_number=None, turn_index=None)

    def with_turn(self, turn_number: int, turn_index: int) -> None:
        self.context.update(turn_number=turn_number, turn_index=turn_index)

    # ------------------------------------------------------------------
    # Lifecycle loggers
    # ------------------------------------------------------------------
    def session_start(self, game: str, players: Sequence[str], *, seed: Optional[int]) -> None:
        lines = [
            "=" * 70,
            "🎮 AgentDeck Session",
            "=" * 70,
            f"Session ID: {self.session.session_id}",
            f"Started At: {_format_timestamp()}",
            f"Game: {game}",
            f"Players: {list(players)}",
        ]
        if seed is not None:
            lines.append(f"Seed: {seed}")
        lines.append("=" * 70)
        self._info("\n".join(lines))

    def session_end(self, total_matches: int, duration_s: float) -> None:
        lines = [
            "=" * 70,
            "🏁 Session Complete",
            "=" * 70,
            f"Total Matches: {total_matches}",
            f"Total Duration: {duration_s:.2f}s",
            f"Log Directory: {self.log_dir}",
            "=" * 70,
        ]
        self._info("\n".join(lines))

    def batch_start(self, batch_id: str, game: str, players: Sequence[str], matches: int) -> None:
        self.with_batch(batch_id)
        self._info(
            "\n".join(
                [
                    "-" * 50,
                    f"Batch {batch_id} starting",
                    f"Game: {game}",
                    f"Players: {list(players)}",
                    f"Matches Planned: {matches}",
                    "-" * 50,
                ]
            )
        )

    def batch_end(self, batch_id: str, results: Dict[str, Any]) -> None:
        self._info(
            "\n".join(
                [
                    "-" * 50,
                    f"Batch {batch_id} complete",
                    f"Matches Completed: {results.get('matches_completed', 'n/a')}",
                    f"Win Rates: {results.get('win_rates', {})}",
                ]
            )
        )
        self.with_batch(None)

    def match_start(self, match_id: str, game: str, players: Sequence[str]) -> None:
        self.with_match(match_id)
        self._info(
            "\n".join(
                [
                    f"Match {match_id} starting",
                    f"Game: {game}",
                    f"Players: {list(players)}",
                ]
            )
        )

    def match_end(self, match_id: str, winner: Optional[str], turns: int, duration: float) -> None:
        self._info(
            "\n".join(
                [
                    f"Match {match_id} complete",
                    f"Winner: {winner if winner else 'Draw'}",
                    f"Turns: {turns}",
                    f"Duration: {duration:.2f}s",
                ]
            )
        )
        self.with_match(None)

    def turn(
        self,
        *,
        turn_number: int,
        player: str,
        action: str,
        reasoning: Optional[str],
        state_before: Optional[Dict[str, Any]],
        state_after: Optional[Dict[str, Any]],
        duration: float,
        usage_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        style = self.config.turn_style
        if style == "silent":
            return

        turn_index = turn_number - 1
        self.with_turn(turn_number, turn_index)

        lines = [f"Turn {turn_number}: {player}", f"Action: {action}"]
        if reasoning:
            lines.append(f"Reasoning: {reasoning}")
        if usage_info:
            # Safe formatting - use .get() to handle incomplete usage_info from API providers
            tokens = usage_info.get("tokens", "?")
            prompt_tokens = usage_info.get("prompt_tokens", "?")
            completion_tokens = usage_info.get("completion_tokens", "?")
            lines.append(
                f"Usage: tokens={tokens} (prompt={prompt_tokens}, completion={completion_tokens})"
            )

        if style in {"full", "summary"}:
            formatted_before = self._format_state("State Before", state_before)
            formatted_after = self._format_state("State After", state_after)
            if style == "full":
                lines.extend(formatted_before)
                lines.extend(formatted_after)
            elif style == "summary":
                if formatted_after:
                    lines.extend(formatted_after[:1])
        if style in {"summary", "diff"} and self.config.include_state_diff:
            diff = self._format_state_diff(state_before, state_after)
            if diff:
                lines.append(f"Δ {diff}")

        lines.append(f"Turn Duration: {duration:.2f}s")
        self._info("\n".join(lines))

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------
    def api_request(
        self,
        *,
        player: str,
        model: str,
        messages: Iterable[Dict[str, Any]],
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> None:
        payload = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": list(messages),
        }
        self._debug(f"[{player}] API request\n{json.dumps(payload, indent=2, ensure_ascii=False)}")

    def api_response(self, *, player: str, response_text: str, truncate: bool = True) -> None:
        if truncate and len(response_text) > 500:
            snippet = response_text[:500] + "…"
        else:
            snippet = response_text
        self._debug(f"[{player}] API response: {snippet}")

    def api_call(
        self,
        *,
        player: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost: float,
        duration: float,
    ) -> None:
        self._debug(
            f"[{player}] API call model={model} tokens_in={tokens_in} tokens_out={tokens_out} "
            f"cost=${cost:.5f} duration={duration:.2f}s"
        )

    def retry(self, *, player: str, attempt: int, error: str, backoff: float) -> None:
        self._warning(
            f"[{player}] retry attempt {attempt} after error: {error}; backoff {backoff:.1f}s"
        )

    # ------------------------------------------------------------------
    # Severity helpers
    # ------------------------------------------------------------------
    def info(self, message: str) -> None:
        self._info(message)

    def debug(self, message: str) -> None:
        self._debug(message)

    def warning(self, message: str) -> None:
        self._warning(message)

    def error(self, message: str, *, error: Optional[BaseException] = None) -> None:
        exc = (type(error), error, error.__traceback__) if error else None
        self._log(logging.ERROR, message, exc_info=exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _install_handlers(self) -> None:
        handlers: List[logging.Handler] = []

        if self.config.console_level is not None:
            console = logging.StreamHandler()
            console.setLevel(_level_to_logging(self.config.console_level))
            console.setFormatter(self._make_formatter(is_file=False))
            handlers.append(console)

        if self.config.file_levels:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            for level in self.config.file_levels:
                file_path = self.log_dir / f"{level.value}.log"
                handler = logging.FileHandler(file_path, encoding="utf-8")
                handler.setLevel(_level_to_logging(level))
                handler.setFormatter(self._make_formatter(is_file=True))
                handlers.append(handler)

        for handler in self.config.extra_handlers:
            handlers.append(handler)

        if not handlers:
            # Ensure there is always at least a NullHandler to avoid warnings
            handlers.append(logging.NullHandler())

        for handler in handlers:
            self._logger.addHandler(handler)

    def _make_formatter(self, *, is_file: bool) -> logging.Formatter:
        if self.config.log_format == "detailed" or is_file:
            fmt = "[%(asctime)s] [%(levelname)s] %(message)s"
            datefmt = "%Y-%m-%d %H:%M:%S"
        else:
            fmt = "[%(asctime)s] %(message)s"
            datefmt = "%H:%M:%S"
        return logging.Formatter(fmt, datefmt=datefmt)

    def _log(self, level: int, message: str, *, exc_info: Optional[Any] = None) -> None:
        self._logger.log(
            level, message, extra={"log_context": self.context.to_dict()}, exc_info=exc_info
        )

    def _info(self, message: str) -> None:
        self._log(logging.INFO, message)

    def _debug(self, message: str) -> None:
        self._log(logging.DEBUG, message)

    def _warning(self, message: str) -> None:
        self._log(logging.WARNING, message)

    def _format_state(self, title: str, state: Optional[Dict[str, Any]]) -> List[str]:
        if state is None:
            return []
        try:
            payload = json.dumps(state, indent=2, default=str)
        except TypeError:
            payload = str(state)
        if len(payload) > self.config.max_state_chars:
            payload = payload[: self.config.max_state_chars] + "…"
        return [f"{title}:", payload]

    def _format_state_diff(
        self,
        before: Optional[Dict[str, Any]],
        after: Optional[Dict[str, Any]],
    ) -> str:
        if before is None or after is None:
            return ""
        changes: List[str] = []

        def compare(
            d1: Dict[str, Any], d2: Dict[str, Any], prefix: str = "", depth: int = 0
        ) -> None:
            # Limit recursion depth to prevent stack overflow on deeply nested states
            if depth >= 10:
                changes.append(f"{prefix}=<deeply nested>")
                return

            keys = set(d1.keys()) | set(d2.keys())
            for key in keys:
                path = f"{prefix}.{key}" if prefix else str(key)
                if key not in d1:
                    changes.append(f"{path}=new")
                elif key not in d2:
                    changes.append(f"{path}=removed")
                else:
                    v1, v2 = d1[key], d2[key]
                    if isinstance(v1, dict) and isinstance(v2, dict):
                        compare(v1, v2, path, depth + 1)
                    elif v1 != v2:
                        changes.append(f"{path}:{v1}->{v2}")

        try:
            compare(before, after)
        except Exception:
            return "state diff unavailable"

        # Show first 10 changes, indicate if more exist
        if len(changes) > 10:
            return ", ".join(changes[:10]) + f" ... and {len(changes) - 10} more"
        return ", ".join(changes) if changes else "no change"


class NullLogger:
    """No-op logger implementing the AgentDeck logger interface."""

    def __getattr__(self, _name: str):  # pragma: no cover - trivial
        return self._noop

    def _noop(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - trivial
        return None


class InMemoryLogHandler(logging.Handler):
    """Logging handler capturing log records for assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.records: List[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def create_logger(
    session: SessionContext, config: Optional[LoggingConfig] = None
) -> Optional[AgentDeckLogger]:
    cfg = config or LoggingConfig.from_session(session)
    if cfg.console_level is None and not cfg.file_levels and not cfg.extra_handlers:
        return None
    return AgentDeckLogger(session, cfg)


def create_memory_logger(session: SessionContext) -> tuple[AgentDeckLogger, InMemoryLogHandler]:
    handler = InMemoryLogHandler()
    cfg = LoggingConfig(console_level=None, file_levels=(), extra_handlers=(handler,))
    logger = AgentDeckLogger(session, cfg)
    return logger, handler


__all__ = [
    "AgentDeckLogger",
    "LoggingConfig",
    "LogContext",
    "NullLogger",
    "InMemoryLogHandler",
    "create_logger",
    "create_memory_logger",
]
