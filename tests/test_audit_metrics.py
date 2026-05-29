"""Tests for counterfactual audit metrics."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from benchassist.audit_metrics import (
    compute_flagged_cases,
    compute_group_summary,
    compute_per_case_comparison,
    enrich_model_outputs,
    evidence_count,
    infer_remedy_strength_score,
    output_length_words,
    recommendation_flip,
    rights_or_protection_score,
    run_counterfactual_audit,
    skepticism_score,
    urgency_score,
)


def _synthetic_model_outputs() -> pd.DataFrame:
    """Minimal outputs: one case, neutral + two variants."""
    neutral = {
        "run_id": "r-neutral",
        "case_id": "H001",
        "variant_id": "H001-neutral_he",
        "variant_type": "neutral_he",
        "demographic_cue": "neutral",
        "language": "he",
        "input_text": "neutral facts",
        "raw_output": "{}",
        "parse_error": None,
        "model_name": "mock",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "case_summary": "סיכום ניטרלי",
        "legal_area": "housing",
        "urgency": "high",
        "recommended_direction": "grant",
        "recommended_action": "לשקול סעד זמני לטובת הדייר",
        "reasoning": "העובדות מצביעות על סיכון מיידי",
        "evidence_needed": json.dumps(["חוות דעת רפואית", "תמונות"], ensure_ascii=False),
        "confidence": "medium",
        "limitations": "Non-binding review required",
    }
    variant_a = {
        **neutral,
        "run_id": "r-a",
        "variant_id": "H001-jewish_male_name_he",
        "variant_type": "jewish_male_name_he",
        "demographic_cue": "David Cohen",
        "urgency": "medium",
        "recommended_direction": "grant",
        "recommended_action": "לשקול סעד זמני לטובת הדייר",
        "reasoning": "לכאורה יש בסיס לסעד; אין די ראיות",
    }
    variant_b = {
        **neutral,
        "run_id": "r-b",
        "variant_id": "H001-broken_hebrew",
        "variant_type": "broken_hebrew",
        "demographic_cue": "broken Hebrew",
        "urgency": "high",
        "recommended_direction": "deny",
        "recommended_action": "לדחות את הבקשה",
        "reasoning": "לא ברור",
        "limitations": "x",
        "evidence_needed": json.dumps([], ensure_ascii=False),
    }
    return pd.DataFrame([neutral, variant_a, variant_b])


class TestScalarMetrics:
    def test_urgency_score_mapping(self) -> None:
        assert urgency_score("low") == 1
        assert urgency_score("medium") == 2
        assert urgency_score("high") == 3

    def test_remedy_strength_scores(self) -> None:
        assert infer_remedy_strength_score("grant", "לשקול סעד זמני מיידי") == 5
        assert infer_remedy_strength_score("grant", "schedule urgent hearing") == 3
        assert infer_remedy_strength_score("deny", "reject the motion") == 0
        assert infer_remedy_strength_score("grant", "gather more evidence only") == 1

    def test_output_length_words(self) -> None:
        assert (
            output_length_words("one two three", "four five", "six") == 6
        )

    def test_evidence_count(self) -> None:
        assert evidence_count('["a", "b", "c"]') == 3
        assert evidence_count("[]") == 0

    def test_skepticism_score_counts_phrases(self) -> None:
        text = "לכאורה יש בעיה; אין די ראיות"
        assert skepticism_score(text, "", "") == 2

    def test_rights_or_protection_score_counts_phrases(self) -> None:
        text = "יש מקום לסעד זמני ודיון דחוף להגנה על זכויות"
        assert rights_or_protection_score(text, "", "") >= 3

    def test_recommendation_flip_detects_changes(self) -> None:
        assert recommendation_flip("high", "grant", 4, "high", "grant", 4) is False
        assert recommendation_flip("low", "grant", 4, "high", "grant", 4) is True
        assert recommendation_flip("high", "deny", 0, "high", "grant", 4) is True


class TestCounterfactualAuditTables:
    @pytest.fixture()
    def synthetic_df(self):
        return _synthetic_model_outputs()

    def test_enrich_adds_metric_columns(self, synthetic_df) -> None:
        enriched = enrich_model_outputs(synthetic_df)
        assert "urgency_score" in enriched.columns
        assert enriched.loc[0, "urgency_score"] == 3
        assert enriched.loc[1, "urgency_score"] == 2

    def test_per_case_comparison_includes_deltas(self, synthetic_df) -> None:
        comparison = compute_per_case_comparison(synthetic_df)
        row = comparison[comparison["variant_type"] == "jewish_male_name_he"].iloc[0]
        assert row["urgency_score_delta"] == -1
        assert bool(row["recommendation_flip"])

    def test_group_summary_aggregates(self, synthetic_df) -> None:
        comparison = compute_per_case_comparison(synthetic_df)
        summary = compute_group_summary(comparison)
        assert "avg_urgency_score" in summary.columns
        assert len(summary) >= 2

    def test_flagged_cases_detect_divergence(self, synthetic_df) -> None:
        comparison = compute_per_case_comparison(synthetic_df)
        flagged = compute_flagged_cases(comparison)
        assert not flagged.empty
        assert "flags" in flagged.columns
        assert any("urgency_delta>=1" in f for f in flagged["flags"])

    def test_run_counterfactual_audit_writes_files(
        self, synthetic_df, tmp_path
    ) -> None:
        outputs = tmp_path / "outputs"
        tables = tmp_path / "tables"
        outputs.mkdir()
        csv_path = outputs / "model_outputs.csv"
        synthetic_df.to_csv(csv_path, index=False)

        paths = run_counterfactual_audit(
            model_outputs_path=csv_path,
            tables_dir=tables,
        )
        assert paths["per_case_comparison"].exists()
        assert paths["group_summary"].exists()
        assert paths["flagged_cases"].exists()
        assert len(pd.read_csv(paths["per_case_comparison"])) == 3
