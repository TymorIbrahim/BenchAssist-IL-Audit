"""Tests for V2 legal-framing audit metrics."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from benchassist.audit_metrics_v2 import (
    compute_v2_group_summary,
    compute_v2_pairwise_comparisons,
    extract_v2_flagged_cases,
    load_and_normalize_outputs,
    run_v2_counterfactual_audit,
)


def _v2_row(
    *,
    case_id: str = "H001",
    variant_id: str,
    variant_type: str,
    demographic_cue: str,
    recommended_action_type: str = "temporary_relief",
    remedy_strength_score: int = 4,
    evidence_burden_level: str = "medium",
    party_credibility_framing: str = "neutral",
    rights_orientation: str = "high",
    procedural_posture: str = "urgent_intervention",
    urgency: str = "high",
) -> dict:
    return {
        "run_id": f"run-{variant_id}",
        "case_id": case_id,
        "variant_id": variant_id,
        "variant_type": variant_type,
        "demographic_cue": demographic_cue,
        "language": "he",
        "input_text": f"input for {variant_id}",
        "raw_output": "{}",
        "parse_error": None,
        "model_name": "mock",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "case_summary": "summary",
        "legal_area": "housing",
        "urgency": urgency,
        "recommended_action_type": recommended_action_type,
        "remedy_strength_score": remedy_strength_score,
        "evidence_burden_level": evidence_burden_level,
        "party_credibility_framing": party_credibility_framing,
        "rights_orientation": rights_orientation,
        "procedural_posture": procedural_posture,
        "reasoning_text": "reasoning",
        "evidence_needed": json.dumps(["doc"], ensure_ascii=False),
        "risk_flags": json.dumps(["requires_human_review"], ensure_ascii=False),
        "confidence": "medium",
        "limitations": "Non-binding memo.",
    }


def _synthetic_v2_outputs() -> pd.DataFrame:
    neutral = _v2_row(
        variant_id="H001-neutral_he",
        variant_type="neutral_he",
        demographic_cue="neutral",
    )
    same = _v2_row(
        variant_id="H001-same",
        variant_type="same_fields",
        demographic_cue="same",
    )
    weaker_remedy = _v2_row(
        variant_id="H001-weaker_remedy",
        variant_type="weaker_remedy",
        demographic_cue="weaker",
        recommended_action_type="regular_hearing",
        remedy_strength_score=2,
        procedural_posture="continue_regular_process",
        rights_orientation="medium",
    )
    higher_burden = _v2_row(
        variant_id="H001-higher_burden",
        variant_type="higher_burden",
        demographic_cue="burden",
        evidence_burden_level="high",
    )
    skeptical = _v2_row(
        variant_id="H001-skeptical",
        variant_type="skeptical_framing",
        demographic_cue="skeptical",
        party_credibility_framing="skeptical",
    )
    action_flip = _v2_row(
        variant_id="H001-action_flip",
        variant_type="action_flip",
        demographic_cue="flip",
        recommended_action_type="reject",
        remedy_strength_score=0,
        procedural_posture="continue_regular_process",
        rights_orientation="low",
        urgency="low",
    )
    return pd.DataFrame(
        [neutral, same, weaker_remedy, higher_burden, skeptical, action_flip]
    )


@pytest.fixture()
def synthetic_csv(tmp_path):
    path = tmp_path / "model_outputs.csv"
    _synthetic_v2_outputs().to_csv(path, index=False)
    return path


@pytest.fixture()
def normalized_df(synthetic_csv):
    return load_and_normalize_outputs(synthetic_csv)


@pytest.fixture()
def pairwise_df(normalized_df):
    return compute_v2_pairwise_comparisons(normalized_df)


class TestLoadAndNormalize:
    def test_load_csv_v2_fields(self, synthetic_csv) -> None:
        normalized = load_and_normalize_outputs(synthetic_csv)
        assert "recommended_action_type" in normalized.columns
        assert normalized.loc[0, "remedy_strength_score"] == 4


class TestV2PairwiseComparisons:
    def test_same_fields_as_neutral_has_no_flags(self, pairwise_df) -> None:
        row = pairwise_df[pairwise_df["variant_type"] == "same_fields"].iloc[0]
        assert not row["action_type_flip"]
        assert not row["legal_framing_bias_flag"]
        assert not row["remedy_weaker"]
        assert not row["evidence_burden_higher"]
        assert not row["credibility_more_skeptical"]

    def test_weaker_remedy_flags(self, pairwise_df) -> None:
        row = pairwise_df[pairwise_df["variant_type"] == "weaker_remedy"].iloc[0]
        assert row["remedy_weaker"]
        assert row["legal_framing_bias_flag"]
        assert row["remedy_strength_delta"] < 0

    def test_higher_evidence_burden_flags(self, pairwise_df) -> None:
        row = pairwise_df[pairwise_df["variant_type"] == "higher_burden"].iloc[0]
        assert row["evidence_burden_higher"]
        assert row["legal_framing_bias_flag"]
        assert row["evidence_burden_delta"] > 0

    def test_skeptical_credibility_flag(self, pairwise_df) -> None:
        row = pairwise_df[pairwise_df["variant_type"] == "skeptical_framing"].iloc[0]
        assert row["credibility_more_skeptical"]
        assert row["legal_framing_bias_flag"]

    def test_action_type_flip(self, pairwise_df) -> None:
        row = pairwise_df[pairwise_df["variant_type"] == "action_flip"].iloc[0]
        assert row["action_type_flip"]
        assert row["variant_recommended_action_type"] == "reject"
        assert row["neutral_recommended_action_type"] == "temporary_relief"

    def test_neutral_baseline_not_flagged_against_itself(self, pairwise_df) -> None:
        row = pairwise_df[pairwise_df["variant_type"] == "neutral_he"].iloc[0]
        assert not row["legal_framing_bias_flag"]
        assert not row["action_type_flip"]
        assert row["remedy_strength_delta"] == 0


class TestV2GroupSummary:
    def test_group_summary_rates(self, pairwise_df) -> None:
        summary = compute_v2_group_summary(pairwise_df)
        weaker = summary[summary["variant_type"] == "weaker_remedy"].iloc[0]
        assert weaker["remedy_weaker_rate"] == 1.0
        assert weaker["legal_framing_bias_flag_rate"] == 1.0

        same = summary[summary["variant_type"] == "same_fields"].iloc[0]
        assert same["legal_framing_bias_flag_rate"] == 0.0
        assert same["action_type_flip_rate"] == 0.0


class TestV2FlaggedCases:
    def test_extract_flagged_sorted(self, pairwise_df) -> None:
        flagged = extract_v2_flagged_cases(pairwise_df)
        assert not flagged.empty
        assert "weaker_remedy" in flagged["variant_type"].tolist()
        assert flagged.iloc[0]["legal_framing_bias_flag"] or flagged.iloc[0]["action_type_flip"]


class TestRunV2Audit:
    def test_run_writes_distinct_v2_files(self, tmp_path) -> None:
        outputs = tmp_path / "outputs"
        tables = tmp_path / "tables"
        charts = tmp_path / "charts"
        outputs.mkdir()
        tables.mkdir()
        charts.mkdir()
        _synthetic_v2_outputs().to_csv(outputs / "model_outputs.csv", index=False)

        result = run_v2_counterfactual_audit(
            model_outputs_path=outputs / "model_outputs.csv",
            tables_dir=tables,
            charts_dir=charts,
        )
        assert result["outputs_loaded"] == 6
        assert result["pairwise_rows"] == 6
        assert result["flagged_rows"] >= 4
        assert (tables / "v2_pairwise_comparison.csv").exists()
        assert (tables / "v2_group_summary.csv").exists()
        assert (tables / "v2_flagged_cases.csv").exists()
        assert (charts / "v2_action_type_flip_rate_by_variant.png").exists()
