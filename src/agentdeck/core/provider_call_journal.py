"""Provider-call custody before downstream execution consumes a response."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Mapping, Protocol


class ProviderCallCustodyError(RuntimeError):
    """Raised when the declared provider-call custody boundary cannot be met."""


class ProviderCallJournal(Protocol):
    """Narrow custody contract for identified provider attempts."""

    mode: str
    backend: str

    def describe(self) -> dict[str, Any]: ...

    def begin_attempt(
        self,
        *,
        call_id: str,
        attempt_index: int,
        intent: Mapping[str, Any],
    ) -> None: ...

    def mark_dispatch_started(
        self,
        *,
        call_id: str,
        attempt_index: int,
        sdk_request: Mapping[str, Any],
    ) -> None: ...

    def commit_response(
        self,
        *,
        call_id: str,
        attempt_index: int,
        provider_call: Mapping[str, Any],
        usage_info: Mapping[str, Any],
    ) -> None: ...

    def commit_error(
        self,
        *,
        call_id: str,
        attempt_index: int,
        error: Mapping[str, Any],
    ) -> None: ...

    def entries(self) -> tuple[dict[str, Any], ...]: ...


class _ProviderCallJournalBase:
    mode: str
    backend: str
    process_restart_recovery: bool

    def describe(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "backend": self.backend,
            "process_restart_recovery": self.process_restart_recovery,
        }

    def begin_attempt(
        self,
        *,
        call_id: str,
        attempt_index: int,
        intent: Mapping[str, Any],
    ) -> None:
        key = _attempt_key(call_id, attempt_index)
        if self._read(key) is not None:
            raise ProviderCallCustodyError(
                f"Provider attempt already exists in custody: {call_id}/{attempt_index}"
            )
        self._write(
            key,
            {
                "schema_version": "0.1",
                "call_id": call_id,
                "attempt_index": attempt_index,
                "state": "intent_committed",
                "intent": _json_copy(intent),
            },
        )

    def mark_dispatch_started(
        self,
        *,
        call_id: str,
        attempt_index: int,
        sdk_request: Mapping[str, Any],
    ) -> None:
        key, entry = self._require(call_id, attempt_index, "intent_committed")
        entry["state"] = "dispatch_started"
        entry["dispatch"] = {"sdk_request": _json_copy(sdk_request)}
        self._write(key, entry)

    def commit_response(
        self,
        *,
        call_id: str,
        attempt_index: int,
        provider_call: Mapping[str, Any],
        usage_info: Mapping[str, Any],
    ) -> None:
        key, entry = self._require(call_id, attempt_index, "dispatch_started")
        entry["state"] = "response_committed"
        entry["result"] = {
            "provider_call": _json_copy(provider_call),
            "usage_info": _json_copy(usage_info),
        }
        self._write(key, entry)

    def commit_error(
        self,
        *,
        call_id: str,
        attempt_index: int,
        error: Mapping[str, Any],
    ) -> None:
        key = _attempt_key(call_id, attempt_index)
        entry = self._read(key)
        if entry is None:
            raise ProviderCallCustodyError(
                f"Provider attempt is missing from custody: {call_id}/{attempt_index}"
            )
        state = str(entry.get("state"))
        if state not in {"intent_committed", "dispatch_started"}:
            raise ProviderCallCustodyError(
                f"Cannot record an error after provider attempt state {state!r}"
            )
        entry["state"] = "attempt_failed"
        entry["provider_outcome"] = "not_dispatched" if state == "intent_committed" else "unknown"
        entry["error"] = _json_copy(error)
        self._write(key, entry)

    def _require(
        self, call_id: str, attempt_index: int, expected_state: str
    ) -> tuple[str, dict[str, Any]]:
        key = _attempt_key(call_id, attempt_index)
        entry = self._read(key)
        if entry is None:
            raise ProviderCallCustodyError(
                f"Provider attempt is missing from custody: {call_id}/{attempt_index}"
            )
        observed = str(entry.get("state"))
        if observed != expected_state:
            raise ProviderCallCustodyError(
                f"Provider attempt {call_id}/{attempt_index} expected custody state "
                f"{expected_state!r}, observed {observed!r}"
            )
        return key, entry

    def _read(self, key: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def _write(self, key: str, entry: Mapping[str, Any]) -> None:
        raise NotImplementedError


class MemoryProviderCallJournal(_ProviderCallJournalBase):
    """Volatile custody for embedded and storage-free provider execution."""

    mode = "volatile"
    backend = "memory"
    process_restart_recovery = False

    def __init__(self) -> None:
        self._entries: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def _read(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            value = self._entries.get(key)
            return copy.deepcopy(value) if value is not None else None

    def _write(self, key: str, entry: Mapping[str, Any]) -> None:
        value = _json_copy(entry)
        with self._lock:
            self._entries[key] = value

    def entries(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            values = [copy.deepcopy(value) for value in self._entries.values()]
        return tuple(sorted(values, key=_entry_sort_key))


class FilesystemProviderCallJournal(_ProviderCallJournalBase):
    """Process-restart-recoverable custody on caller-selected filesystem storage."""

    mode = "durable"
    backend = "filesystem"
    process_restart_recovery = True

    def __init__(self, directory: str | os.PathLike[str]) -> None:
        self.directory = Path(directory).resolve()
        self._lock = threading.RLock()
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ProviderCallCustodyError(
                f"Cannot initialize durable provider-call custody: {exc}"
            ) from exc

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.directory / f"attempt_{digest}.json"

    def _read(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        with self._lock:
            if not path.is_file():
                return None
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ProviderCallCustodyError(
                    f"Cannot read durable provider-call custody entry: {exc}"
                ) from exc

    def _write(self, key: str, entry: Mapping[str, Any]) -> None:
        path = self._path(key)
        value = _json_copy(entry)
        temp_path: Path | None = None
        with self._lock:
            try:
                with tempfile.NamedTemporaryFile(
                    "w",
                    encoding="utf-8",
                    delete=False,
                    dir=self.directory,
                ) as handle:
                    json.dump(
                        value,
                        handle,
                        ensure_ascii=False,
                        allow_nan=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    handle.flush()
                    os.fsync(handle.fileno())
                    temp_path = Path(handle.name)
                os.replace(temp_path, path)
                temp_path = None
                _sync_directory(self.directory)
            except (OSError, TypeError, ValueError) as exc:
                raise ProviderCallCustodyError(
                    f"Cannot commit durable provider-call custody: {exc}"
                ) from exc
            finally:
                if temp_path is not None:
                    try:
                        temp_path.unlink(missing_ok=True)
                    except OSError:
                        pass

    def entries(self) -> tuple[dict[str, Any], ...]:
        values: list[dict[str, Any]] = []
        with self._lock:
            for path in sorted(self.directory.glob("attempt_*.json")):
                try:
                    values.append(json.loads(path.read_text(encoding="utf-8")))
                except (OSError, json.JSONDecodeError) as exc:
                    raise ProviderCallCustodyError(
                        f"Cannot inspect durable provider-call custody: {exc}"
                    ) from exc
        return tuple(sorted(values, key=_entry_sort_key))


def create_provider_call_journal(
    mode: str,
    *,
    directory: str | os.PathLike[str] | None = None,
) -> ProviderCallJournal:
    """Create the built-in journal for one declared custody mode."""

    if mode == "volatile":
        return MemoryProviderCallJournal()
    if mode == "durable":
        if directory is None:
            raise ProviderCallCustodyError(
                "Durable provider-call custody requires a persistent directory"
            )
        return FilesystemProviderCallJournal(directory)
    raise ValueError("provider_call_custody must be 'volatile' or 'durable'")


def validate_provider_call_journal(
    journal: ProviderCallJournal,
    *,
    required_mode: str,
) -> None:
    """Fail before provider work when a host backend violates declared policy."""

    observed = getattr(journal, "mode", None)
    if observed != required_mode:
        raise ProviderCallCustodyError(
            "Provider-call custody mismatch: "
            f"execution requires {required_mode!r}, host supplied {observed!r}"
        )


def _attempt_key(call_id: str, attempt_index: int) -> str:
    if not isinstance(call_id, str) or not call_id:
        raise ProviderCallCustodyError("Provider attempt requires a non-empty call_id")
    if isinstance(attempt_index, bool) or not isinstance(attempt_index, int):
        raise ProviderCallCustodyError("Provider attempt index must be a positive integer")
    if attempt_index < 1:
        raise ProviderCallCustodyError("Provider attempt index must be a positive integer")
    return f"{call_id}:{attempt_index}"


def _json_copy(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        encoded = json.dumps(
            dict(value),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        decoded = json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise ProviderCallCustodyError(
            f"Provider-call custody payload is not strict JSON: {exc}"
        ) from exc
    if not isinstance(decoded, dict):  # pragma: no cover - mapping always decodes to object
        raise ProviderCallCustodyError("Provider-call custody payload must be an object")
    return decoded


def _entry_sort_key(entry: Mapping[str, Any]) -> tuple[str, int]:
    return str(entry.get("call_id") or ""), int(entry.get("attempt_index") or 0)


def _sync_directory(directory: Path) -> None:
    """Make a completed rename durable where directory fsync is supported."""

    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(directory, flags)
    except OSError:
        if os.name == "nt":
            return
        raise
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


__all__ = [
    "FilesystemProviderCallJournal",
    "MemoryProviderCallJournal",
    "ProviderCallCustodyError",
    "ProviderCallJournal",
    "create_provider_call_journal",
    "validate_provider_call_journal",
]
