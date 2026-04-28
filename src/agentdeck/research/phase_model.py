"""Phase-scope helpers for matrix research packages."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import yaml

PHASE_MODEL_FIELDS = (
    "study_phases",
    "preflight_phases",
    "main_phases",
    "excluded_phases",
)

EXPLICIT_PACKAGE_SCOPES = {"explicit_phase", "explicit_cells"}


def _as_string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def load_phase_model(
    manifest: Mapping[str, Any], matrix: Mapping[str, Any]
) -> Dict[str, List[str]]:
    """Return normalized phase model fields, preferring matrix-owned values."""
    manifest_model = manifest.get("phase_model")
    if not isinstance(manifest_model, dict):
        workflow = manifest.get("research_workflow")
        manifest_model = workflow.get("phase_model") if isinstance(workflow, dict) else {}
    if not isinstance(manifest_model, dict):
        manifest_model = {}

    matrix_model = matrix.get("phase_model")
    if not isinstance(matrix_model, dict):
        matrix_model = {}

    merged = dict(manifest_model)
    merged.update(matrix_model)
    return {field: _as_string_list(merged.get(field)) for field in PHASE_MODEL_FIELDS}


def phase_to_cell_ids(matrix: Mapping[str, Any]) -> Dict[str, List[str]]:
    """Return phase -> cell ids from execution_plan plus cell phase metadata."""
    phases: Dict[str, List[str]] = {}
    execution_plan = matrix.get("execution_plan")
    if isinstance(execution_plan, dict):
        preflight = execution_plan.get("preflight")
        if isinstance(preflight, dict) and preflight.get("phase_id"):
            phases.setdefault(str(preflight["phase_id"]), [])
            for cell_id in _as_string_list(preflight.get("cell_ids")):
                if cell_id not in phases[str(preflight["phase_id"])]:
                    phases[str(preflight["phase_id"])].append(cell_id)

        for phase_entry in execution_plan.get("phases") or []:
            if not isinstance(phase_entry, dict) or not phase_entry.get("phase_id"):
                continue
            phase_id = str(phase_entry["phase_id"])
            phases.setdefault(phase_id, [])
            for cell_id in _as_string_list(phase_entry.get("cell_ids")):
                if cell_id not in phases[phase_id]:
                    phases[phase_id].append(cell_id)

    for cell in matrix.get("cells") or []:
        if not isinstance(cell, dict) or not cell.get("id"):
            continue
        phase_id = str(cell.get("phase") or "?")
        cell_id = str(cell["id"])
        phases.setdefault(phase_id, [])
        if cell_id not in phases[phase_id]:
            phases[phase_id].append(cell_id)

    return phases


def phase_for_cell(matrix: Mapping[str, Any], cell_id: str) -> str | None:
    for cell in matrix.get("cells") or []:
        if isinstance(cell, dict) and str(cell.get("id")) == cell_id:
            phase = cell.get("phase")
            return str(phase) if phase is not None else None
    for phase_id, phase_cell_ids in phase_to_cell_ids(matrix).items():
        if cell_id in phase_cell_ids:
            return phase_id
    return None


def iter_selected_cells(
    matrix: Mapping[str, Any], *, phase: str | None, cell_ids: set[str] | None
) -> Iterable[Dict[str, Any]]:
    phase_cells = set(phase_to_cell_ids(matrix).get(phase, [])) if phase else None
    for cell in matrix.get("cells") or []:
        if not isinstance(cell, dict) or not cell.get("id"):
            continue
        cell_id = str(cell["id"])
        if phase_cells is not None and cell_id not in phase_cells:
            continue
        if cell_ids and cell_id not in cell_ids:
            continue
        yield dict(cell)


def _known_cell_ids(matrix: Mapping[str, Any]) -> set[str]:
    return {
        str(cell["id"])
        for cell in matrix.get("cells") or []
        if isinstance(cell, dict) and cell.get("id")
    }


def _ordered_cells_by_ids(
    matrix: Mapping[str, Any], selected_ids: Sequence[str]
) -> List[Dict[str, Any]]:
    selected = set(selected_ids)
    return [
        dict(cell)
        for cell in matrix.get("cells") or []
        if isinstance(cell, dict) and str(cell.get("id")) in selected
    ]


def _non_empty_phases(matrix: Mapping[str, Any]) -> List[str]:
    known = _known_cell_ids(matrix)
    return [
        phase
        for phase, ids in phase_to_cell_ids(matrix).items()
        if any(cell_id in known for cell_id in ids)
    ]


def select_package_cells(
    matrix: Mapping[str, Any],
    manifest: Mapping[str, Any],
    *,
    phase: str | None,
    cell_ids: set[str] | None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Select package aggregation cells and return source metadata."""
    known_ids = _known_cell_ids(matrix)
    if cell_ids:
        missing = sorted(cell_ids - known_ids)
        if missing:
            raise SystemExit(f"Unknown matrix cells: {', '.join(missing)}")
        selected = _ordered_cells_by_ids(matrix, sorted(cell_ids))
        phases = _unique([phase_for_cell(matrix, str(cell["id"])) for cell in selected])
        return selected, {
            "aggregation_scope": "explicit_cells",
            "phases_included": phases,
            "cells_included": [str(cell["id"]) for cell in selected],
        }

    if phase:
        selected = list(iter_selected_cells(matrix, phase=phase, cell_ids=None))
        if not selected:
            raise SystemExit(f"No cells selected for phase '{phase}'.")
        return selected, {
            "aggregation_scope": "explicit_phase",
            "phases_included": [phase],
            "cells_included": [str(cell["id"]) for cell in selected],
        }

    phase_model = load_phase_model(manifest, matrix)
    study_phases = phase_model.get("study_phases") or []
    if study_phases:
        phase_ids = phase_to_cell_ids(matrix)
        selected_ids: List[str] = []
        for study_phase in study_phases:
            for cell_id in phase_ids.get(study_phase, []):
                if cell_id not in selected_ids:
                    selected_ids.append(cell_id)
        selected = _ordered_cells_by_ids(matrix, selected_ids)
        if not selected:
            raise SystemExit(
                "No recordings can be selected because phase_model.study_phases "
                "does not map to any matrix cells."
            )
        included_phases = [
            phase_name
            for phase_name in study_phases
            if any(str(cell.get("phase")) == phase_name for cell in selected)
        ]
        return selected, {
            "aggregation_scope": "study_phases",
            "phases_included": included_phases,
            "cells_included": [str(cell["id"]) for cell in selected],
        }

    non_empty_phases = _non_empty_phases(matrix)
    if len(non_empty_phases) > 1:
        raise SystemExit(
            "Package export is ambiguous for a multi-phase matrix. Declare "
            "phase_model.study_phases or pass --phase/--cell with --package."
        )

    selected = [
        dict(cell)
        for cell in matrix.get("cells") or []
        if isinstance(cell, dict) and cell.get("id")
    ]
    if not selected:
        raise SystemExit("No cells selected for package export.")
    return selected, {
        "aggregation_scope": "all_phases",
        "phases_included": non_empty_phases,
        "cells_included": [str(cell["id"]) for cell in selected],
    }


def validate_package_phase_scope(
    experiment_dir: Path,
    manifest: Mapping[str, Any],
    results: Mapping[str, Any],
) -> List[str]:
    matrix_path = experiment_dir / "matrix.yaml"
    if not matrix_path.exists():
        return []

    matrix = yaml.safe_load(matrix_path.read_text(encoding="utf-8")) or {}
    if not isinstance(matrix, dict):
        return [f"{experiment_dir.name}: matrix.yaml must be mapping for phase validation"]

    source = results.get("source")
    if not isinstance(source, dict):
        return []

    phase_model = load_phase_model(manifest, matrix)
    has_phase_model = any(phase_model.get(field) for field in PHASE_MODEL_FIELDS)
    has_source_scope = any(
        key in source for key in ("aggregation_scope", "phases_included", "cells_included")
    )
    if not has_phase_model and not has_source_scope:
        return []

    errors: List[str] = []
    experiment_name = experiment_dir.name
    scope = source.get("aggregation_scope")
    phases_included = source.get("phases_included")
    cells_included = source.get("cells_included")

    if not isinstance(scope, str) or not scope:
        errors.append(f"{experiment_name}: results.json.source.aggregation_scope missing")
    if not _is_list_of_strings(phases_included):
        errors.append(f"{experiment_name}: results.json.source.phases_included must be list[str]")
        phases: List[str] = []
    else:
        phases = list(phases_included)
    if not _is_list_of_strings(cells_included):
        errors.append(f"{experiment_name}: results.json.source.cells_included must be list[str]")
        cells: List[str] = []
    else:
        cells = list(cells_included)

    phase_cells = phase_to_cell_ids(matrix)
    known_cells = _known_cell_ids(matrix)
    known_phases = set(phase_cells)
    unknown_phases = sorted(set(phases) - known_phases)
    unknown_cells = sorted(set(cells) - known_cells)
    if unknown_phases:
        errors.append(
            f"{experiment_name}: results.json.source.phases_included unknown phases "
            f"{unknown_phases}"
        )
    if unknown_cells:
        errors.append(
            f"{experiment_name}: results.json.source.cells_included unknown cells {unknown_cells}"
        )

    cell_phases = _unique([phase_for_cell(matrix, cell_id) for cell_id in cells])
    cells_outside_phases = sorted(set(cell_phases) - set(phases))
    if cells_outside_phases:
        errors.append(
            f"{experiment_name}: results.json.source.cells_included contains cells outside "
            f"phases_included {cells_outside_phases}"
        )

    study_phases = set(phase_model.get("study_phases") or [])
    excluded_phases = set(phase_model.get("preflight_phases") or []) | set(
        phase_model.get("excluded_phases") or []
    )

    if scope == "study_phases" and study_phases:
        non_study = sorted(set(phases) - study_phases)
        if non_study:
            errors.append(
                f"{experiment_name}: study_phases package export includes non-study phases "
                f"{non_study}"
            )
        contaminated = sorted(set(phases) & excluded_phases)
        if contaminated:
            errors.append(
                f"{experiment_name}: study_phases package export includes excluded phases "
                f"{contaminated}"
            )
    elif has_phase_model and scope not in EXPLICIT_PACKAGE_SCOPES:
        contaminated = sorted(set(phases) & excluded_phases)
        if contaminated:
            errors.append(
                f"{experiment_name}: package export includes excluded phases {contaminated}"
            )

    return errors


def _unique(values: Iterable[str | None]) -> List[str]:
    unique_values: List[str] = []
    for value in values:
        if value is None or value in unique_values:
            continue
        unique_values.append(value)
    return unique_values


def _is_list_of_strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


__all__ = [
    "EXPLICIT_PACKAGE_SCOPES",
    "PHASE_MODEL_FIELDS",
    "iter_selected_cells",
    "load_phase_model",
    "phase_for_cell",
    "phase_to_cell_ids",
    "select_package_cells",
    "validate_package_phase_scope",
]
