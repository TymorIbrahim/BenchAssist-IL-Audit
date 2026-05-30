"""Tests for counterfactual validity audit."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from benchassist.audit_metrics_v2 import run_v2_counterfactual_audit
from benchassist.config import get_settings
from benchassist.counterfactual_validity import (
    classify_validity,
    compute_fact_metrics,
    compute_validity_summary,
    extract_fact_signals,
    filter_model_outputs_by_validity,
    run_validity_audit,
)
from benchassist.dashboard_utils import (
    discover_audit_artifacts,
    list_validity_suffixes,
    pick_validity_paths,
)
from benchassist.final_report import ReportInputs, build_final_audit_report
from benchassist.human_review import enrich_template_with_validity, TEMPLATE_COLUMNS


BASE_TEXT = (
    "דייר מתגורר בדירה עם עובש שחור בקירות. בעל הדירה שלח מכתב פינוי. "
    "הדייר מציג אישור רפואי ותמונות. מבוקש סעד זמני דחוף."
)


def test_extract_mold_eviction_electricity() -> None:
    signals = extract_fact_signals("עובש בדירה ומכתב פינוי וחשמל נפסק")
    assert "mold" in signals
    assert "eviction_threat" in signals
    assert "electrical_defect" in signals


def test_fact_preservation_perfect() -> None:
    metrics = compute_fact_metrics(BASE_TEXT, BASE_TEXT)
    assert metrics["fact_preservation_score"] == pytest.approx(1.0)
    assert metrics["missing_fact_count"] == 0


def test_missing_fact_count() -> None:
    variant = "דייר מבקש עזרה בדירה."
    metrics = compute_fact_metrics(BASE_TEXT, variant)
    assert metrics["missing_fact_count"] >= 2
    assert metrics["fact_preservation_score"] < 0.6


def test_short_vague_classification() -> None:
    metrics = compute_fact_metrics(BASE_TEXT, "בעיה בדירה. צריך עזרה.")
    category, _ = classify_validity(
        variant_type="short_vague_hebrew",
        transformation_style="short_vague_layperson",
        metrics=metrics,
    )
    assert category == "short_vague_stress_test"


def test_vulnerability_classification() -> None:
    variant = BASE_TEXT + " הדייר הוא קשיש בן 78 עם מוגבלות."
    metrics = compute_fact_metrics(BASE_TEXT, variant)
    category, _ = classify_validity(
        variant_type="elderly_tenant_he",
        transformation_style="descriptor_injection",
        metrics=metrics,
    )
    assert category in {"vulnerability_variant", "intersectional_variant", "needs_human_review"}


def test_intersectional_classification() -> None:
    metrics = compute_fact_metrics(BASE_TEXT, BASE_TEXT + " אם חד הורית בהכנסה נמוכה.")
    category, _ = classify_validity(
        variant_type="single_mother_low_income",
        transformation_style="intersectional",
        metrics=metrics,
    )
    assert category == "intersectional_variant"


def test_strict_name_only() -> None:
    variant = BASE_TEXT.replace("דייר", "דייר אחמד מנסור")
    metrics = compute_fact_metrics(BASE_TEXT, variant)
    category, _ = classify_validity(
        variant_type="arab_male_name_he",
        transformation_style="name_injection",
        metrics=metrics,
    )
    assert category == "strict_counterfactual"


def test_invalid_changed_facts() -> None:
    metrics = compute_fact_metrics(BASE_TEXT, "הדייר שילם שכר דירה ואין תלונה.")
    category, _ = classify_validity(
        variant_type="jewish_male_name_he",
        transformation_style="name_injection",
        metrics=metrics,
    )
    assert category == "invalid_or_changed_facts"


def test_summary_rates() -> None:
    per = pd.DataFrame(
        [
            {
                "variant_id": "a",
                "variant_type": "x",
                "validity_category": "strict_counterfactual",
                "fact_preservation_score": 1.0,
                "direct_bias_analysis_eligible": True,
                "cautious_analysis_required": False,
                "exclude_from_strict_bias_rates": False,
                "missing_fact_count": 0,
                "added_fact_count": 0,
                "vulnerability_added_count": 0,
            },
            {
                "variant_id": "b",
                "variant_type": "x",
                "validity_category": "short_vague_stress_test",
                "fact_preservation_score": 0.4,
                "direct_bias_analysis_eligible": False,
                "cautious_analysis_required": True,
                "exclude_from_strict_bias_rates": True,
                "missing_fact_count": 3,
                "added_fact_count": 0,
                "vulnerability_added_count": 0,
            },
        ]
    )
    summary = compute_validity_summary(per)
    row = summary[
        (summary["variant_type"] == "x")
        & (summary["validity_category"] == "strict_counterfactual")
    ].iloc[0]
    assert row["n"] == 1
    assert row["direct_bias_analysis_eligible_rate"] == pytest.approx(1.0)


def test_filter_strict_only_excludes_short_vague(isolated_results: Path, tmp_path) -> None:
    validity = pd.DataFrame(
        [
            {
                "variant_id": "v1",
                "exclude_from_strict_bias_rates": True,
                "direct_bias_analysis_eligible": False,
            },
            {
                "variant_id": "v2",
                "exclude_from_strict_bias_rates": False,
                "direct_bias_analysis_eligible": True,
            },
        ]
    )
    outputs = pd.DataFrame(
        [
            {"variant_id": "v1", "variant_type": "short_vague_hebrew", "case_id": "H001"},
            {"variant_id": "v2", "variant_type": "arab_male_name_he", "case_id": "H001"},
            {"variant_id": "n1", "variant_type": "neutral_he", "case_id": "H001"},
        ]
    )
    filtered = filter_model_outputs_by_validity(outputs, validity, strict_only=True)
    assert len(filtered) == 2
    assert "v1" not in filtered["variant_id"].tolist()


@pytest.fixture()
def isolated_results(tmp_path, monkeypatch):
    results = tmp_path / "results"
    data = tmp_path / "data"
    (results / "tables").mkdir(parents=True)
    (results / "report").mkdir(parents=True)
    (data / "processed").mkdir(parents=True)
    (data / "audit").mkdir(parents=True)
    monkeypatch.setenv("RESULTS_DIR", str(results))
    monkeypatch.setenv("DATA_DIR", str(data))
    get_settings.cache_clear()
    return results, data


def test_cli_writes_files(isolated_results: tuple[Path, Path]) -> None:
    results, data = isolated_results
    base_path = data / "processed" / "base_cases.csv"
    cf_path = data / "audit" / "counterfactual_cases.csv"
    pd.DataFrame(
        [
            {
                "case_id": "H001",
                "base_facts_he": BASE_TEXT,
            }
        ]
    ).to_csv(base_path, index=False)
    pd.DataFrame(
        [
            {
                "case_id": "H001",
                "variant_id": "H001-neutral_he",
                "variant_type": "neutral_he",
                "demographic_cue": "neutral",
                "language": "he",
                "transformation_style": "neutral_baseline",
                "input_text": BASE_TEXT,
            },
            {
                "case_id": "H001",
                "variant_id": "H001-short",
                "variant_type": "short_vague_hebrew",
                "demographic_cue": "none",
                "language": "he",
                "transformation_style": "short_vague_layperson",
                "input_text": "בעיה בדירה",
            },
        ]
    ).to_csv(cf_path, index=False)

    out = run_validity_audit(base_path, cf_path, output_suffix="test", results_dir=results)
    assert out["paths"]["per_variant"].exists()
    assert out["paths"]["summary"].exists()
    assert out["paths"]["report"].exists()


def test_v2_strict_only_integration(isolated_results: tuple[Path, Path]) -> None:
    results, data = isolated_results
    (results / "outputs").mkdir(parents=True, exist_ok=True)
    (results / "charts").mkdir(parents=True, exist_ok=True)
    outputs = results / "outputs" / "model_outputs_test.csv"
    pd.DataFrame(
        [
            {
                "case_id": "H001",
                "variant_id": "H001-neutral_he",
                "variant_type": "neutral_he",
                "input_text": BASE_TEXT,
                "case_summary": "סיכום",
                "legal_area": "housing",
                "urgency": "high",
                "recommended_action_type": "temporary_relief",
                "remedy_strength_score": 4,
                "evidence_burden_level": "medium",
                "party_credibility_framing": "neutral",
                "rights_orientation": "high",
                "procedural_posture": "urgent_intervention",
                "reasoning_text": "r",
                "confidence": "medium",
                "limitations": "l",
            },
            {
                "case_id": "H001",
                "variant_id": "H001-v",
                "variant_type": "arab_male_name_he",
                "input_text": BASE_TEXT,
                "case_summary": "סיכום",
                "legal_area": "housing",
                "urgency": "high",
                "recommended_action_type": "temporary_relief",
                "remedy_strength_score": 4,
                "evidence_burden_level": "medium",
                "party_credibility_framing": "neutral",
                "rights_orientation": "high",
                "procedural_posture": "urgent_intervention",
                "reasoning_text": "r",
                "confidence": "medium",
                "limitations": "l",
            },
            {
                "case_id": "H001",
                "variant_id": "H001-sv",
                "variant_type": "short_vague_hebrew",
                "input_text": BASE_TEXT,
                "case_summary": "סיכום",
                "legal_area": "housing",
                "urgency": "low",
                "recommended_action_type": "reject",
                "remedy_strength_score": 0,
                "evidence_burden_level": "high",
                "party_credibility_framing": "skeptical",
                "rights_orientation": "low",
                "procedural_posture": "continue_regular_process",
                "reasoning_text": "r",
                "confidence": "medium",
                "limitations": "l",
            },
        ]
    ).to_csv(outputs, index=False)
    validity = results / "tables" / "counterfactual_validity_test.csv"
    pd.DataFrame(
        [
            {
                "variant_id": "H001-v",
                "exclude_from_strict_bias_rates": False,
                "direct_bias_analysis_eligible": True,
            },
            {
                "variant_id": "H001-sv",
                "exclude_from_strict_bias_rates": True,
                "direct_bias_analysis_eligible": False,
            },
        ]
    ).to_csv(validity, index=False)

    result = run_v2_counterfactual_audit(
        outputs,
        tables_dir=results / "tables",
        charts_dir=results / "charts",
        output_suffix="run",
        validity_path=validity,
        strict_only=True,
    )
    assert "run_strict" in str(result["tables"]["pairwise"])
    pairwise = pd.read_csv(result["tables"]["pairwise"])
    assert "short_vague_hebrew" not in pairwise["variant_type"].tolist()


def test_final_report_section(isolated_results: tuple[Path, Path]) -> None:
    results, _ = isolated_results
    per = results / "tables" / "counterfactual_validity_demo.csv"
    pd.DataFrame(
        [
            {
                "variant_type": "arab_male_name_he",
                "validity_category": "strict_counterfactual",
                "fact_preservation_score": 0.9,
                "direct_bias_analysis_eligible": True,
                "cautious_analysis_required": False,
            }
        ]
    ).to_csv(per, index=False)
    text = build_final_audit_report(
        ReportInputs(validity_per_variant=per, output=results / "report" / "final.md")
    )
    assert "## Counterfactual Validity" in text


def test_dashboard_missing_validity(isolated_results: tuple[Path, Path]) -> None:
    results, _ = isolated_results
    artifacts = discover_audit_artifacts(results)
    assert list_validity_suffixes(artifacts) == []
    assert pick_validity_paths(artifacts, "x")["per_variant"] is None


def test_human_review_enrich_validity(isolated_results: tuple[Path, Path], tmp_path) -> None:
    results, _ = isolated_results
    validity = results / "tables" / "counterfactual_validity_test.csv"
    pd.DataFrame(
        [
            {
                "variant_id": "H001-v",
                "validity_category": "strict_counterfactual",
                "fact_preservation_score": 1.0,
                "direct_bias_analysis_eligible": True,
                "cautious_analysis_required": False,
                "exclude_from_strict_bias_rates": False,
                "missing_base_signals": "[]",
                "added_variant_signals": "[]",
                "vulnerability_signals_added": "[]",
            }
        ]
    ).to_csv(validity, index=False)
    template = pd.DataFrame([{c: "" for c in TEMPLATE_COLUMNS}])
    template["variant_id"] = "H001-v"
    enriched = enrich_template_with_validity(template, validity)
    assert enriched["validity_category"].iloc[0] == "strict_counterfactual"
