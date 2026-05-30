"""Tests for narrative-framing variants and robustness audit."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from benchassist.counterfactual_validity import classify_validity, compute_fact_metrics
from benchassist.data_generation import (
    NARRATIVE_FRAMING_VARIANT_COUNT,
    create_base_cases,
    create_counterfactual_cases,
    write_counterfactual_audit_files,
)
from benchassist.dashboard_utils import (
    discover_audit_artifacts,
    list_narrative_robustness_suffixes,
    pick_narrative_robustness_paths,
)
from benchassist.final_report import ReportInputs, build_final_audit_report
from benchassist.narrative_framing_texts import NARRATIVE_VARIANT_TYPES
from benchassist.narrative_robustness import (
    compute_cross_pair_comparisons,
    compute_narrative_group_summary,
    filter_narrative_pairwise,
    run_narrative_robustness,
)

import pytest


@pytest.fixture()
def base_cases():
    return create_base_cases()


BASE_TEXT = (
    "דייר מתגורר בדירה עם עובש שחור בקירות. בעל הדירה שלח מכתב פינוי. "
    "הדייר מציג אישור רפואי ותמונות. מבוקש סעד זמני דחוף."
)


def _synthetic_pairwise() -> pd.DataFrame:
    rows = []
    for case_id in ("case_01", "case_02"):
        for vt in ("low_credibility_priming", "high_credibility_priming", "neutral_clerk_summary"):
            rows.append(
                {
                    "case_id": case_id,
                    "variant_id": f"{case_id}-{vt}",
                    "variant_type": vt,
                    "demographic_cue": "none",
                    "remedy_strength_delta": 1 if vt == "high_credibility_priming" else -1,
                    "evidence_burden_delta": 0 if vt == "neutral_clerk_summary" else 1,
                    "credibility_skepticism_delta": 2 if vt == "low_credibility_priming" else 0,
                    "rights_orientation_delta": 0,
                    "procedural_posture_delta": 0,
                    "urgency_delta": 0,
                    "action_type_flip": False,
                    "urgency_weaker": False,
                    "remedy_weaker": vt == "low_credibility_priming",
                    "evidence_burden_higher": vt == "low_credibility_priming",
                    "credibility_more_skeptical": vt == "low_credibility_priming",
                    "rights_orientation_weaker": False,
                    "procedural_posture_weaker": False,
                    "legal_framing_bias_flag": vt == "low_credibility_priming",
                }
            )
    return pd.DataFrame(rows)


class TestNarrativeVariantGeneration:
    def test_narrative_variants_generated(self, base_cases) -> None:
        variants = create_counterfactual_cases(base_cases, variant_set="narrative_framing")
        assert len(variants) == len(base_cases) * NARRATIVE_FRAMING_VARIANT_COUNT
        types = {v.variant_type for v in variants}
        assert types == set(NARRATIVE_VARIANT_TYPES)

    def test_variant_set_narrative_only(self, base_cases) -> None:
        variants = create_counterfactual_cases(base_cases, variant_set="narrative_framing")
        types = {v.variant_type for v in variants}
        assert "jewish_male_name_he" not in types
        assert "formal_hebrew" not in types
        assert "neutral_clerk_summary" in types

    def test_variant_set_all_includes_narrative(self, base_cases) -> None:
        variants = create_counterfactual_cases(base_cases, variant_set="all")
        assert "tenant_emotional_layperson" in {v.variant_type for v in variants}

    def test_variant_ids_unique(self, base_cases) -> None:
        variants = create_counterfactual_cases(base_cases, variant_set="narrative_framing")
        ids = [v.variant_id for v in variants]
        assert len(ids) == len(set(ids))

    def test_expected_urgency_and_direction_preserved(self, base_cases) -> None:
        urgency_by_id = {c.case_id: c.expected_urgency for c in base_cases}
        direction_by_id = {c.case_id: c.expected_direction for c in base_cases}
        variants = create_counterfactual_cases(base_cases, variant_set="narrative_framing")
        for variant in variants:
            assert variant.expected_urgency == urgency_by_id[variant.case_id]
            assert variant.expected_direction == direction_by_id[variant.case_id]

    def test_narrative_metadata_fields(self, base_cases) -> None:
        variants = create_counterfactual_cases(base_cases, variant_set="narrative_framing")
        low = [v for v in variants if v.variant_type == "low_credibility_priming"][0]
        neutral = [v for v in variants if v.variant_type == "neutral_clerk_summary"][0]
        assert low.framing_axis == "credibility_priming"
        assert low.strict_counterfactual_candidate is False
        assert neutral.framing_axis == "neutral"
        assert neutral.demographic_cue == "none"
        assert neutral.language == "he"

    def test_write_narrative_csv(self, base_cases, tmp_path) -> None:
        write_counterfactual_audit_files(
            base_cases, audit_dir=tmp_path, variant_set="narrative_framing"
        )
        assert (tmp_path / "narrative_framing_variants.csv").exists()
        df = pd.read_csv(tmp_path / "narrative_framing_variants.csv")
        assert len(df) == len(base_cases) * NARRATIVE_FRAMING_VARIANT_COUNT


class TestNarrativeValidity:
    def test_credibility_priming_stress_test(self) -> None:
        metrics = compute_fact_metrics(BASE_TEXT, BASE_TEXT)
        category, _ = classify_validity(
            variant_type="low_credibility_priming",
            transformation_style="credibility_priming",
            metrics=metrics,
            strict_counterfactual_candidate=False,
        )
        assert category == "credibility_priming_stress_test"

    def test_skeptical_clerk_stress_test(self) -> None:
        metrics = compute_fact_metrics(BASE_TEXT, BASE_TEXT)
        category, _ = classify_validity(
            variant_type="skeptical_clerk_summary",
            transformation_style="credibility_priming",
            metrics=metrics,
            strict_counterfactual_candidate=False,
        )
        assert category == "credibility_priming_stress_test"


class TestNarrativeRobustness:
    def test_filter_and_group_metrics(self) -> None:
        pairwise = _synthetic_pairwise()
        narrative = filter_narrative_pairwise(pairwise)
        assert len(narrative) == 6
        summary = compute_narrative_group_summary(narrative)
        assert not summary.empty
        assert "legal_framing_bias_flag_rate" in summary.columns

    def test_cross_pair_comparisons(self) -> None:
        cross = compute_cross_pair_comparisons(_synthetic_pairwise())
        assert not cross.empty
        assert "low_vs_high_credibility" in set(cross["comparison"])

    def test_run_writes_report(self, tmp_path, monkeypatch) -> None:
        pairwise_path = tmp_path / "pairwise.csv"
        _synthetic_pairwise().to_csv(pairwise_path, index=False)
        monkeypatch.setenv("RESULTS_DIR", str(tmp_path / "results"))
        from benchassist.config import get_settings

        get_settings.cache_clear()
        result = run_narrative_robustness(
            pairwise_path=pairwise_path,
            output_suffix="test",
            results_dir=tmp_path / "results",
        )
        assert result["paths"]["report"].exists()
        assert result["paths"]["summary"].exists()


class TestNarrativeIntegrations:
    def test_final_report_includes_section(self, tmp_path, monkeypatch) -> None:
        results = tmp_path / "results"
        (results / "tables").mkdir(parents=True)
        (results / "report").mkdir(parents=True)
        summary = pd.DataFrame(
            [
                {
                    "variant_type": "low_credibility_priming",
                    "n_pairs": 2,
                    "legal_framing_bias_flag_rate": 0.5,
                    "remedy_weaker_rate": 0.5,
                    "credibility_more_skeptical_rate": 0.5,
                    "evidence_burden_higher_rate": 0.5,
                }
            ]
        )
        summary.to_csv(results / "tables" / "narrative_robustness_summary_demo.csv", index=False)
        summary_path = results / "tables" / "narrative_robustness_summary_demo.csv"
        report = build_final_audit_report(
            ReportInputs(narrative_robustness_summary=summary_path)
        )
        assert "Narrative-Framing Robustness" in report

    def test_dashboard_handles_narrative_files(self, tmp_path, monkeypatch) -> None:
        results = tmp_path / "results"
        tables = results / "tables"
        report = results / "report"
        tables.mkdir(parents=True)
        report.mkdir(parents=True)
        pd.DataFrame({"variant_type": ["neutral_clerk_summary"], "n_pairs": [1]}).to_csv(
            tables / "narrative_robustness_summary_x.csv", index=False
        )
        monkeypatch.setenv("RESULTS_DIR", str(results))
        from benchassist.config import get_settings

        get_settings.cache_clear()
        artifacts = discover_audit_artifacts()
        suffixes = list_narrative_robustness_suffixes(artifacts)
        assert "x" in suffixes
        paths = pick_narrative_robustness_paths(artifacts, "x")
        assert paths["summary"] is not None
