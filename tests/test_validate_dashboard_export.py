"""Tests for dashboard export validation."""

from __future__ import annotations

import json
from pathlib import Path

from benchassist.validate_dashboard_export import validate_export


def test_validate_export_passes_on_current_data(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "manifest.json").write_text(json.dumps({"use_case": "housing"}), encoding="utf-8")
    assert validate_export(data) == []

def test_validate_export_catches_duplicate_pairs(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "manifest.json").write_text(json.dumps({"use_case": "detention"}), encoding="utf-8")
    pairwise = [
        {"case_id": "D1", "variant_id": "v1"},
        {"case_id": "D1", "variant_id": "v1"},
    ]
    (data / "detention_pairwise_comparison.json").write_text(json.dumps(pairwise), encoding="utf-8")
    errors = validate_export(data)
    assert any("unique pairs" in e for e in errors)


def test_validate_export_baseline_flagged_vs_all_modes(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    (data / "manifest.json").write_text(json.dumps({"use_case": "detention"}), encoding="utf-8")
    flagged = [
        {"case_id": "D1", "variant_id": "v1", "prompt_mode": "baseline"},
        {"case_id": "D1", "variant_id": "v1", "prompt_mode": "fairness_aware"},
    ]
    overview = [{"n_flagged_comparisons": 1, "n_flagged_comparisons_all_modes": 2}]
    (data / "detention_flagged_cases.json").write_text(json.dumps(flagged), encoding="utf-8")
    (data / "detention_overview_metrics.json").write_text(json.dumps(overview), encoding="utf-8")
    assert validate_export(data) == []
