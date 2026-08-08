"""Deterministic report models for Instrument Package operations."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agentdeck.core.artifact_safety import require_json_value


@dataclass(frozen=True)
class InstrumentCheck:
    """One mechanically evaluated Instrument Package requirement."""

    check_id: str
    status: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.check_id,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class InstrumentReport:
    """Canonical output shared by inspect, validate, and certify."""

    operation: str
    package_root: str
    trust_mode: str = "structural"
    schema_version: Optional[str] = None
    instrument: Dict[str, Any] = field(default_factory=dict)
    package_sha256: Optional[str] = None
    requested_tiers: List[str] = field(default_factory=list)
    awarded_tiers: List[str] = field(default_factory=list)
    checks: List[InstrumentCheck] = field(default_factory=list)
    errors: List[Dict[str, str]] = field(default_factory=list)
    warnings: List[Dict[str, str]] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors and all(check.status != "failed" for check in self.checks)

    def checked(
        self,
        check_id: str,
        passed: bool,
        message: str,
        *,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.checks.append(
            InstrumentCheck(
                check_id=check_id,
                status="passed" if passed else "failed",
                message=message,
                details=details or {},
            )
        )
        if not passed:
            self.errors.append({"check_id": check_id, "message": message})

    def error(self, check_id: str, message: str) -> None:
        self.errors.append({"check_id": check_id, "message": message})

    def warn(self, check_id: str, message: str) -> None:
        self.warnings.append({"check_id": check_id, "message": message})

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "report_schema_version": "1.0",
            "operation": self.operation,
            "package_root": self.package_root,
            "trust_mode": self.trust_mode,
            "valid": self.valid,
            "schema_version": self.schema_version,
            "instrument": self.instrument,
            "package_sha256": self.package_sha256,
            "requested_tiers": self.requested_tiers,
            "awarded_tiers": self.awarded_tiers,
            "checks": [check.to_dict() for check in self.checks],
            "errors": self.errors,
            "warnings": self.warnings,
            "artifacts": self.artifacts,
        }
        require_json_value(payload, field="instrument report")
        return payload

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
