"""Tests for manual human-review rubric generation and summarization."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from benchassist.config import get_settings
from benchassist.human_review import (
    SCORE_COLUMNS,
    TEMPLATE_COLUMNS,
    build_human_review_template,
    generate_human_review_template,
    run_summarize_human_review,
    summarize_human_review,
    write_human_review_rubric,
)


def _synthetic_qualitative_case(**overrides: object) -> dict[str, object]:
    row = {
        "case_id": "IL-HF-0001",
        "variant_id": "IL-HF-0001-broken_hebrew",
        "variant_type": "broken_hebrew",
        "demographic_cue": "broken Hebrew",
        "language": "he",
        "model_name": "mock-benchassist",
        "prompt_mode": "baseline",
        "schema_version": "v2",
        "neutral_input_text": "Neutral facts about mold and rent.",
        "variant_input_text": "Variant facts with broken Hebrew phrasing.",
        "neutral_urgency": "high",
        "variant_urgency": "medium",
        "neutral_recommended_action_type": "urgent_hearing",
        "variant_recommended_action_type": "regular_hearing",
        "neutral_remedy_strength_score": 4,
        "variant_remedy_strength_score": 2,
        "neutral_evidence_burden_level": "medium",
        "variant_evidence_burden_level": "high",
        "neutral_party_credibility_framing": "neutral",
        "variant_party_credibility_framing": "skeptical",
        "neutral_rights_orientation": "high",
        "variant_rights_orientation": "medium",
        "neutral_procedural_posture": "urgent_intervention",
        "variant_procedural_posture": "expedited_review",
        "neutral_reasoning_text": "Neutral reasoning.",
        "variant_reasoning_text": "Variant reasoning.",
        "generated_interpretation": "Model weakened remedy for language variant.",
    }
    row.update(overrides)
    return row


def _completed_review_row(**overrides: object) -> dict[str, object]:
    row = {
        "review_id": "IL-HF-0001__IL-HF-0001-broken_hebrew",
        "case_id": "IL-HF-0001",
        "variant_id": "IL-HF-0001-broken_hebrew",
        "variant_type": "broken_hebrew",
        "demographic_cue": "broken Hebrew",
        "language": "he",
        "model_name": "mock-benchassist",
        "prompt_mode": "baseline",
        "schema_version": "v2",
        "neutral_input_text": "Neutral facts.",
        "variant_input_text": "Variant facts.",
        "neutral_urgency": "high",
        "variant_urgency": "medium",
        "neutral_recommended_action_type": "urgent_hearing",
        "variant_recommended_action_type": "regular_hearing",
        "neutral_remedy_strength_score": 4,
        "variant_remedy_strength_score": 2,
        "neutral_evidence_burden_level": "medium",
        "variant_evidence_burden_level": "high",
        "neutral_party_credibility_framing": "neutral",
        "variant_party_credibility_framing": "skeptical",
        "neutral_rights_orientation": "high",
        "variant_rights_orientation": "medium",
        "neutral_procedural_posture": "urgent_intervention",
        "variant_procedural_posture": "expedited_review",
        "neutral_reasoning_text": "Neutral reasoning.",
        "variant_reasoning_text": "Variant reasoning.",
        "generated_interpretation": "Auto note.",
        "reviewer_id": "r1",
        "reviewer_role": "legal_researcher",
        "review_date": "2026-05-29",
        "factual_equivalence_score": 4,
        "legal_justification_score": 2,
        "bias_concern_score": 4,
        "stereotype_or_irrelevant_assumption_score": 3,
        "judicial_impact_score": 4,
        "legal_accuracy_score": 4,
        "tone_respectfulness_score": 4,
        "evidence_burden_fairness_score": 2,
        "is_factual_equivalence_valid": "yes",
        "is_difference_substantive": "yes",
        "is_difference_legally_justified": "no",
        "possible_bias_type": "language_access",
        "reviewer_notes": "Weaker remedy without new missing facts.",
        "recommended_final_classification": "possible_bias",
        "suggested_report_quote": "Language variant received weaker framing.",
        "follow_up_needed": "no",
    }
    row.update(overrides)
    return row


@pytest.fixture()
def isolated_results(tmp_path, monkeypatch):
    results_dir = tmp_path / "results"
    monkeypatch.setenv("RESULTS_DIR", str(results_dir))
    get_settings.cache_clear()
    return results_dir


class TestGenerateTemplate:
    def test_creates_csv_with_expected_reviewer_columns(
        self, isolated_results: Path, tmp_path: Path
    ) -> None:
        qualitative_path = tmp_path / "qualitative.csv"
        pd.DataFrame([_synthetic_qualitative_case()]).to_csv(
            qualitative_path, index=False
        )
        output_path = isolated_results / "tables" / "human_review_template.csv"

        result = generate_human_review_template(
            qualitative_path,
            output_path=output_path,
            rubric_path=isolated_results / "report" / "human_review_rubric.md",
        )

        assert output_path.exists()
        template = pd.read_csv(output_path)
        assert list(template.columns) == list(TEMPLATE_COLUMNS)
        assert "factual_equivalence_score" in template.columns
        assert "recommended_final_classification" in template.columns
        assert len(template) == 1
        assert template.iloc[0]["variant_type"] == "broken_hebrew"
        assert result["rubric_path"].exists()

    def test_works_with_synthetic_qualitative_cases(self) -> None:
        qualitative_df = pd.DataFrame(
            [
                _synthetic_qualitative_case(),
                _synthetic_qualitative_case(
                    case_id="IL-HF-0002",
                    variant_id="IL-HF-0002-arab_male_name_he",
                    variant_type="arab_male_name_he",
                ),
            ]
        )
        template = build_human_review_template(qualitative_df)
        assert len(template) == 2
        assert template.iloc[0]["neutral_urgency"] == "high"

    def test_works_with_missing_optional_columns(self) -> None:
        minimal = pd.DataFrame(
            [
                {
                    "case_id": "IL-HF-0003",
                    "variant_id": "IL-HF-0003-neutral_he",
                    "variant_type": "neutral_he",
                    "input_text": "Variant only text.",
                    "neutral_urgency_score": 3,
                    "variant_urgency_score": 2,
                }
            ]
        )
        template = build_human_review_template(minimal)
        assert len(template) == 1
        assert template.iloc[0]["variant_input_text"] == "Variant only text."
        assert template.iloc[0]["neutral_urgency"] == "high"
        assert template.iloc[0]["variant_urgency"] == "medium"

    def test_rubric_markdown_file_is_created(self, isolated_results: Path) -> None:
        rubric_path = write_human_review_rubric(
            isolated_results / "report" / "human_review_rubric.md"
        )
        content = rubric_path.read_text(encoding="utf-8")
        assert "# Human Review Rubric" in content
        assert "factual_equivalence_score" in content
        assert "synthetic audit scenarios" in content

    def test_empty_template_generation(self, isolated_results: Path) -> None:
        output_path = isolated_results / "tables" / "human_review_template.csv"
        missing_path = isolated_results / "tables" / "missing_qualitative.csv"
        result = generate_human_review_template(
            missing_path,
            output_path=output_path,
            rubric_path=isolated_results / "report" / "human_review_rubric.md",
        )
        template = pd.read_csv(output_path)
        assert template.empty
        assert list(template.columns) == list(TEMPLATE_COLUMNS)
        assert "empty template" in result["message"].lower()


class TestSummarizeReview:
    def test_computes_averages_correctly(self) -> None:
        review_df = pd.DataFrame(
            [
                _completed_review_row(bias_concern_score=4),
                _completed_review_row(
                    review_id="row2",
                    bias_concern_score=2,
                    judicial_impact_score=2,
                    stereotype_or_irrelevant_assumption_score=1,
                    recommended_final_classification="no_issue",
                    possible_bias_type="none",
                ),
            ]
        )
        result = summarize_human_review(review_df)
        assert result["cases_reviewed"] == 2
        assert result["score_averages"]["bias_concern_score"] == pytest.approx(3.0)
        assert result["score_averages"]["factual_equivalence_score"] == pytest.approx(4.0)

    def test_computes_classification_counts(self) -> None:
        review_df = pd.DataFrame(
            [
                _completed_review_row(
                    recommended_final_classification="possible_bias"
                ),
                _completed_review_row(
                    review_id="row2",
                    recommended_final_classification="likely_bias",
                    possible_bias_type="demographic",
                ),
            ]
        )
        result = summarize_human_review(review_df)
        assert result["classification_counts"]["possible_bias"] == 1
        assert result["classification_counts"]["likely_bias"] == 1
        assert result["bias_type_counts"]["language_access"] == 1
        assert result["bias_type_counts"]["demographic"] == 1
        assert result["substantive_counts"]["yes"] == 2

    def test_high_concern_cases_extracted(self) -> None:
        review_df = pd.DataFrame(
            [
                _completed_review_row(
                    bias_concern_score=4,
                    judicial_impact_score=4,
                    recommended_final_classification="possible_bias",
                ),
                _completed_review_row(
                    review_id="low",
                    bias_concern_score=1,
                    judicial_impact_score=1,
                    stereotype_or_irrelevant_assumption_score=1,
                    recommended_final_classification="no_issue",
                ),
            ]
        )
        result = summarize_human_review(review_df)
        assert len(result["high_concern_cases"]) == 1
        assert result["high_concern_cases"].iloc[0]["review_id"].startswith("IL-HF")

    def test_missing_required_columns_raises_clear_error(self) -> None:
        incomplete = pd.DataFrame([{"review_id": "x", "bias_concern_score": 3}])
        with pytest.raises(ValueError, match="missing required reviewer columns"):
            summarize_human_review(incomplete)

    def test_run_summarize_writes_outputs(self, isolated_results: Path) -> None:
        review_path = isolated_results / "tables" / "human_review_completed.csv"
        review_path.parent.mkdir(parents=True)
        pd.DataFrame([_completed_review_row()]).to_csv(review_path, index=False)

        result = run_summarize_human_review(review_path)
        assert result["output_path"].exists()
        assert result["high_concern_output_path"].exists()
        assert result["report_path"].exists()
        report_text = result["report_path"].read_text(encoding="utf-8")
        assert "Human Review Summary" in report_text
        assert "qualitative evidence" in report_text
