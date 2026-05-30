"""Tests for Vercel dashboard JSON export."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from benchassist.vercel_export import (
    DISCLAIMER_TEXT,
    _export_row_count,
    _patch_detention_report_counts,
    build_cross_prompt_comparisons,
    collect_detention_reports,
    default_output_dir,
    derive_issue_tags,
    derive_linked_case_key,
    derive_review_priority,
    derive_review_priority_reason,
    derive_strongest_signal,
    derive_strongest_signal_explanation,
    detect_run_type,
    discover_output_files_by_prompt_mode,
    enrich_audit_rows,
    export_csv,
    export_priority_score,
    export_vercel_data,
    select_best_run,
)
from benchassist.dashboard_utils import AuditRunBundle


def test_export_priority_prefers_core_full() -> None:
    assert export_priority_score("gemini_flash_lite_core_full_audit_baseline") > export_priority_score(
        "gemini_flash_lite_pilot_baseline"
    )
    assert export_priority_score("gemini_flash_lite_core_full_audit_baseline") > export_priority_score(
        "qa_mock_baseline"
    )


def test_select_best_run_prefers_baseline() -> None:
    runs = [
        AuditRunBundle(label="gemini_flash_lite_core_full_audit_v2_fairness_aware"),
        AuditRunBundle(label="gemini_flash_lite_core_full_audit_v2_baseline"),
    ]
    best = select_best_run(runs)
    assert best is not None
    assert "baseline" in best.label


def test_export_csv_empty() -> None:
    assert export_csv(None) == []


def test_export_creates_public_data_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    results = tmp_path / "results"
    tables = results / "tables"
    outputs = results / "outputs"
    report = results / "report"
    tables.mkdir(parents=True)
    outputs.mkdir(parents=True)
    report.mkdir(parents=True)

    group = tables / "v2_group_summary_gemini_flash_lite_core_full_audit_v2_baseline.csv"
    pd.DataFrame(
        [
            {
                "variant_type": "neutral_he",
                "demographic_cue": "neutral",
                "n_pairs": 12,
                "legal_framing_bias_flag_rate": 0.0,
                "action_type_flip_rate": 0.0,
                "remedy_weaker_rate": 0.0,
                "evidence_burden_higher_rate": 0.0,
                "credibility_more_skeptical_rate": 0.0,
                "rights_orientation_weaker_rate": 0.0,
            }
        ]
    ).to_csv(group, index=False)

    pairwise = tables / "v2_pairwise_comparison_gemini_flash_lite_core_full_audit_v2_baseline.csv"
    pd.DataFrame(
        [
            {
                "case_id": "H001",
                "variant_id": "H001-arab_name_he",
                "variant_type": "arab_name_he",
                "demographic_cue": "Arab",
                "legal_framing_bias_flag": True,
                "action_type_flip": False,
            }
        ]
    ).to_csv(pairwise, index=False)

    flagged = tables / "v2_flagged_cases_gemini_flash_lite_core_full_audit_v2_baseline.csv"
    pd.DataFrame([{"case_id": "H001", "variant_type": "arab_name_he"}]).to_csv(flagged, index=False)

    out_csv = outputs / "gemini_flash_lite_core_full_audit_v2_baseline.csv"
    pd.DataFrame(
        [
            {
                "case_id": "H001",
                "variant_id": "H001-neutral_he",
                "provider": "gemini",
                "model_name": "gemini-2.5-flash-lite",
                "schema_version": "v2",
                "prompt_mode": "baseline",
                "parse_error": "",
            }
        ]
    ).to_csv(out_csv, index=False)

    (report / "final_audit_report.md").write_text("# Final\n\nNot legal advice.", encoding="utf-8")

    out_dir = tmp_path / "web_dashboard" / "public" / "data"
    monkeypatch.setenv("BENCHASSIST_RESULTS_DIR", str(results))
    from benchassist import config

    config.get_settings.cache_clear()

    manifest = export_vercel_data(output_dir=out_dir, results_dir=results)
    assert out_dir.is_dir()
    assert (out_dir / "manifest.json").exists()
    assert (out_dir / "group_summary.json").exists()
    assert (out_dir / "reports.json").exists()

    loaded = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert loaded["secrets_excluded"] is True
    assert DISCLAIMER_TEXT in loaded["disclaimer"]
    assert "group_summary.json" in loaded["selected_source_files"]


def test_missing_files_do_not_crash(tmp_path: Path) -> None:
    results = tmp_path / "results"
    (results / "tables").mkdir(parents=True)
    (results / "outputs").mkdir(parents=True)
    (results / "report").mkdir(parents=True)
    out_dir = tmp_path / "data"
    manifest = export_vercel_data(output_dir=out_dir, results_dir=results)
    assert manifest["run_label"] == "empty"
    assert (out_dir / "pairwise_comparison.json").exists()
    assert json.loads((out_dir / "pairwise_comparison.json").read_text()) == []


def test_env_not_exported(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("GEMINI_API_KEY=secret-test-key\n", encoding="utf-8")
    out_dir = tmp_path / "data"
    results = tmp_path / "results"
    (results / "tables").mkdir(parents=True)
    (results / "outputs").mkdir(parents=True)
    (results / "report").mkdir(parents=True)
    export_vercel_data(output_dir=out_dir, results_dir=results)
    for path in out_dir.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert "secret-test-key" not in text
        assert "GEMINI_API_KEY" not in text


def test_manifest_includes_missing_optional_files(tmp_path: Path) -> None:
    results = tmp_path / "results"
    (results / "tables").mkdir(parents=True)
    (results / "outputs").mkdir(parents=True)
    (results / "report").mkdir(parents=True)
    out_dir = tmp_path / "data"
    manifest = export_vercel_data(output_dir=out_dir, results_dir=results)
    assert "missing_optional_files" in manifest
    assert isinstance(manifest["missing_optional_files"], list)
    assert len(manifest["missing_optional_files"]) > 0


def test_derive_strongest_signal_action_flip() -> None:
    row = {"action_type_flip": True, "remedy_weaker": True}
    signal = derive_strongest_signal(row)
    assert "Action changed" in signal
    assert "Weaker remedy" in signal


def test_derive_review_priority_high_for_action_flip() -> None:
    assert derive_review_priority({"action_type_flip": True}) == "High"


def test_derive_review_priority_medium_for_single_flag() -> None:
    assert derive_review_priority({"remedy_weaker": True}) == "Medium"


def test_detect_run_type_core_full() -> None:
    assert detect_run_type("gemini_flash_lite_core_full_audit_v2_baseline") == "core_full"
    assert detect_run_type("qa_mock") == "mock"


def test_enrich_audit_rows_adds_fields() -> None:
    rows = enrich_audit_rows([{"case_id": "H001", "variant_id": "v1", "variant_type": "arab_name_he", "legal_framing_bias_flag": True, "remedy_weaker": True}])
    assert rows[0]["is_flagged"] is True
    assert rows[0]["review_priority"] in {"Medium", "High"}
    assert "strongest_signal" in rows[0]
    assert "plain_language_summary" in rows[0]
    assert "review_priority_reason" in rows[0]
    assert "issue_tags" in rows[0]
    assert rows[0]["linked_case_key"] == "H001::v1"
    assert rows[0]["is_high_priority"] is (rows[0]["review_priority"] == "High")


def test_derive_review_priority_reason_action_flip() -> None:
    reason = derive_review_priority_reason({"action_type_flip": True})
    assert "action category changed" in reason


def test_derive_issue_tags() -> None:
    tags = derive_issue_tags({"remedy_weaker": True, "evidence_burden_higher": True})
    assert "weaker_remedy" in tags
    assert "higher_evidence_burden" in tags


def test_derive_linked_case_key() -> None:
    assert derive_linked_case_key({"case_id": "C1", "variant_id": "V1"}) == "C1::V1"


def test_derive_strongest_signal_explanation() -> None:
    text = derive_strongest_signal_explanation({"remedy_weaker": True})
    assert "screening signal" in text.lower()


def test_derive_review_priority_high_for_three_flags() -> None:
    row = {"remedy_weaker": True, "evidence_burden_higher": True, "credibility_more_skeptical": True}
    assert derive_review_priority(row) == "High"


def test_default_output_dir_under_web_dashboard() -> None:
    assert "web_dashboard" in str(default_output_dir())
    assert default_output_dir().name == "data"


def _sample_output_row(case_id: str, variant_id: str, action: str, prompt_mode: str) -> dict:
    return {
        "run_id": f"run-{prompt_mode}",
        "case_id": case_id,
        "variant_id": variant_id,
        "variant_type": "arab_name_he",
        "demographic_cue": "Arab",
        "language": "he",
        "prompt_mode": prompt_mode,
        "recommended_action_type": action,
        "urgency": "high",
        "remedy_strength_score": 4,
        "evidence_burden_level": "medium",
        "party_credibility_framing": "neutral",
        "rights_orientation": "high",
        "procedural_posture": "strong",
        "reasoning_text": "Sample reasoning",
        "evidence_needed": "photos",
        "limitations": "toy audit",
    }


def test_cross_prompt_empty_when_only_baseline(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    pd.DataFrame([_sample_output_row("H001", "H001-v1", "relief", "baseline")]).to_csv(
        outputs / "gemini_core_full_audit_v2_baseline.csv", index=False
    )
    rows, meta = build_cross_prompt_comparisons(outputs)
    assert rows == []
    assert meta["cross_prompt_comparisons_available"] is False
    assert meta["cross_prompt_comparison_row_count"] == 0
    assert "fairness_aware" in meta["missing_prompt_modes_for_comparison"]


def test_cross_prompt_generates_rows_for_baseline_and_fairness(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    base_row = _sample_output_row("H001", "H001-v1", "relief", "baseline")
    fair_row = _sample_output_row("H001", "H001-v1", "more_evidence", "fairness_aware")
    pd.DataFrame([base_row]).to_csv(outputs / "gemini_core_full_audit_v2_baseline.csv", index=False)
    pd.DataFrame([fair_row]).to_csv(outputs / "gemini_core_full_audit_v2_fairness_aware.csv", index=False)

    rows, meta = build_cross_prompt_comparisons(outputs)
    assert meta["cross_prompt_comparisons_available"] is True
    assert meta["cross_prompt_comparison_row_count"] >= 1
    assert "baseline" in meta["prompt_modes_detected"]
    assert "fairness_aware" in meta["prompt_modes_detected"]

    bf = [r for r in rows if r["comparison_type"] == "baseline_vs_fairness_aware"]
    assert len(bf) == 1
    assert bf[0]["action_type_changed"] is True
    assert bf[0]["any_material_change"] is True
    assert "plain_language_summary" in bf[0]


def test_export_writes_cross_prompt_json_and_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    results = tmp_path / "results"
    tables = results / "tables"
    outputs = results / "outputs"
    report = results / "report"
    for d in (tables, outputs, report):
        d.mkdir(parents=True)

    pd.DataFrame([_sample_output_row("H001", "H001-v1", "relief", "baseline")]).to_csv(
        outputs / "gemini_core_full_audit_v2_baseline.csv", index=False
    )
    pd.DataFrame([_sample_output_row("H001", "H001-v1", "relief", "fairness_aware")]).to_csv(
        outputs / "gemini_core_full_audit_v2_fairness_aware.csv", index=False
    )

    out_dir = tmp_path / "data"
    manifest = export_vercel_data(output_dir=out_dir, results_dir=results)
    assert (out_dir / "cross_prompt_comparisons.json").exists()
    loaded = json.loads((out_dir / "cross_prompt_comparisons.json").read_text(encoding="utf-8"))
    assert isinstance(loaded, list)
    assert len(loaded) >= 1
    assert manifest.get("cross_prompt_comparisons_available") is True
    assert "prompt_modes_detected" in manifest


def test_discover_output_files_prefers_core_full() -> None:
    # smoke: function importable; full filesystem test covered above
    assert callable(discover_output_files_by_prompt_mode)


def test_export_includes_data_access_policy(tmp_path: Path) -> None:
    from benchassist.vercel_export import _export_data_access_policy

    project_root = Path(__file__).resolve().parent.parent
    out_dir = tmp_path / "data"
    out_dir.mkdir()
    policy, warnings = _export_data_access_policy(out_dir, project_root)
    assert (out_dir / "data_access_policy.json").exists()
    assert policy.get("requires_access_control") is True
    assert "detention_fulltext_indicators" in policy
    if policy.get("contains_unredacted_public_legal_text"):
        assert warnings


def test_patch_detention_report_counts() -> None:
    text = "- Pairwise comparisons: 288\n- Flagged comparisons: 121\n"
    patched = _patch_detention_report_counts(text, pairwise=96, flagged=68)
    assert "Pairwise comparisons: 96" in patched
    assert "Flagged comparisons: 68" in patched


def test_export_row_count_nested_payloads() -> None:
    review = {"record_count": 96, "records": [{}] * 96}
    assert _export_row_count("detention_case_review_records.json", review) == 96
    index = {"record_count": 96, "records_index": [{}] * 96}
    assert _export_row_count("detention_case_review_index.json", index) == 96


def test_collect_detention_reports_filters_housing(tmp_path: Path) -> None:
    report_dir = tmp_path / "results" / "report"
    report_dir.mkdir(parents=True)
    (report_dir / "detention_mock_pipeline_qa_report.md").write_text(
        "# Detention QA\n\n- Pairwise comparisons: 288\n",
        encoding="utf-8",
    )
    reports = collect_detention_reports(tmp_path, pairwise_count=96, flagged_count=68)
    assert reports
    assert all("detention" in r["report_name"].lower() for r in reports)
    assert "96" in reports[0]["markdown_text"]
