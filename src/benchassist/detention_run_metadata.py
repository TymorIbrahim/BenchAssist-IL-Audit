"""Shared detention run metadata helpers for reports and exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_gemini_run_manifest(run_dir: Path | None) -> dict[str, Any]:
    if run_dir is None:
        return {}
    path = run_dir / "run_manifest.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def detention_run_slug(run_manifest: dict[str, Any]) -> str:
    run_type = str(run_manifest.get("run_type") or "full")
    if run_type == "expanded_minimal_address":
        return "detention_expanded_minimal_address"
    if run_type == "expanded_full":
        return "detention_expanded_full"
    if run_type == "pilot":
        return "detention_pilot"
    return "detention_full"


def detention_report_paths(project_root: Path, run_manifest: dict[str, Any]) -> dict[str, Path]:
    slug = detention_run_slug(run_manifest)
    report_dir = project_root / "results" / "report"
    return {
        "qa_report": report_dir / f"gemini_{slug}_qa_report.md",
        "review_packet": report_dir / f"gemini_{slug}_flagged_cases_review_packet.md",
    }


def infer_detention_run_label(run_dir: Path | None, *, data_status: str | None = None) -> str:
    manifest = load_gemini_run_manifest(run_dir)
    run_type = str(manifest.get("run_type") or ("expanded_full" if data_status == "gemini_expanded_full" else "full"))
    model = str(manifest.get("model") or "gemini-2.5-flash-lite").replace(".", "_")
    return f"detention_{run_type}_{model}"


def infer_detention_run_type(run_dir: Path | None, *, data_status: str | None = None) -> str:
    manifest = load_gemini_run_manifest(run_dir)
    if manifest.get("run_type"):
        return str(manifest["run_type"])
    normalized = normalize_detention_data_status(data_status)
    if normalized == "gemini_expanded_full":
        return "expanded_full"
    if normalized == "gemini_minimal_address":
        return "expanded_minimal_address"
    if normalized == "gemini_pilot":
        return "pilot"
    return "full"


def normalize_detention_data_status(data_status: str | None) -> str | None:
    """Map config/dashboard aliases to canonical export data_status values."""
    if data_status == "gemini_expanded_minimal_address":
        return "gemini_minimal_address"
    return data_status


def resolve_synthetic_corpus_path(
    project_root: Path,
    *,
    run_dir: Path | None = None,
    run_manifest: dict[str, Any] | None = None,
) -> Path | None:
    """Resolve the synthetic CSV used for this detention run (validity + case review)."""
    manifest = run_manifest or load_gemini_run_manifest(run_dir)
    config_rel = manifest.get("config_path")
    if config_rel:
        config_path = Path(config_rel)
        if not config_path.is_absolute():
            config_path = project_root / config_path
        if config_path.exists():
            try:
                cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
                dataset = cfg.get("dataset") or {}
                rel = dataset.get("synthetic_input")
                if rel:
                    candidate = Path(rel)
                    if not candidate.is_absolute():
                        candidate = project_root / candidate
                    if candidate.exists():
                        return candidate
            except (OSError, yaml.YAMLError):
                pass

    for rel in (
        "data/synthetic/detention_core_cases_with_address.csv",
        "data/synthetic/detention_core_cases.csv",
        "data/audit/detention/detention_counterfactual_cases.csv",
    ):
        path = project_root / rel
        if path.exists():
            return path
    return None
