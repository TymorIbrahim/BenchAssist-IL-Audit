"""Property-style tests for dashboard export manifest helpers."""

from __future__ import annotations

from benchassist.dashboard_export_manifest import (
    build_cross_prompt_mode_summary,
    export_completeness_score,
    missing_optional_files_detail,
)


def test_export_completeness_score_critical_and_optional() -> None:
    full = {
        "detention_overview_metrics.json": 1,
        "detention_pairwise_comparison.json": 90,
        "detention_flagged_cases.json": 12,
        "detention_case_review_index.json": 1,
        "detention_cross_prompt_comparisons.json": 40,
        "detention_statistical_tests.json": 5,
    }
    result = export_completeness_score(full, missing_optional=[])
    assert result["critical_exports_ok"] is True
    assert result["deploy_blocked"] is False
    assert result["export_completeness_score"] >= 80

    sparse = {"detention_overview_metrics.json": 1}
    bad = export_completeness_score(sparse, missing_optional=["detention_cross_prompt_comparisons.json"])
    assert bad["critical_exports_ok"] is False
    assert bad["deploy_blocked"] is True
    assert bad["export_completeness_score"] < 70


def test_cross_prompt_mode_summary_buckets() -> None:
    rows = [
        {"comparison_mode": "fairness_aware", "cross_prompt_instability_flag": True},
        {"comparison_mode": "fairness_aware", "reasoning_only_change": True},
        {"comparison_mode": "demographic_blind", "reasoning_only_change": True},
    ]
    summary = build_cross_prompt_mode_summary(rows)
    by_mode = summary["by_comparison_mode"]
    assert by_mode["fairness_aware"]["material_instability"] == 1
    assert by_mode["fairness_aware"]["total"] == 2
    assert "note" in summary


def test_missing_optional_files_detail_maps_impact() -> None:
    detail = missing_optional_files_detail(["detention_cross_prompt_comparisons.json", "unknown_file.json"])
    assert detail[0]["file"] == "detention_cross_prompt_comparisons.json"
    assert "Mitigation" in detail[0]["tabs_affected"]
    assert detail[1]["tabs_affected"] == "Unknown"
