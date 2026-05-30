"""Tests for repeated-run stability testing."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from benchassist.config import get_settings
from benchassist.run_batch import run_model_batch
from benchassist.stability_metrics import (
    compare_counterfactual_vs_random_instability,
    compute_stability_group_summary,
    compute_within_prompt_stability,
    run_stability_analysis,
)


def _synthetic_repeated_outputs() -> pd.DataFrame:
    base = {
        "case_id": "H001",
        "variant_id": "H001-neutral_he",
        "variant_type": "neutral_he",
        "demographic_cue": "neutral",
        "language": "he",
        "schema_version": "v2",
        "prompt_mode": "baseline",
        "legal_area": "housing",
        "evidence_burden_level": "medium",
        "party_credibility_framing": "neutral",
        "rights_orientation": "high",
        "procedural_posture": "urgent_intervention",
        "case_summary": "summary",
        "reasoning_text": "reasoning",
        "confidence": "medium",
        "limitations": "Non-binding memo.",
        "evidence_needed": "[]",
        "parse_error": None,
    }
    rows = [
        {
            **base,
            "repetition_index": 1,
            "urgency": "high",
            "recommended_action_type": "temporary_relief",
            "remedy_strength_score": 4,
        },
        {
            **base,
            "repetition_index": 2,
            "urgency": "high",
            "recommended_action_type": "temporary_relief",
            "remedy_strength_score": 4,
        },
        {
            **base,
            "repetition_index": 3,
            "urgency": "medium",
            "recommended_action_type": "urgent_hearing",
            "remedy_strength_score": 3,
        },
    ]
    return pd.DataFrame(rows)


class TestWithinPromptStability:
    def test_identical_repetitions_not_unstable(self) -> None:
        df = _synthetic_repeated_outputs().iloc[:2].copy()
        within = compute_within_prompt_stability(df)
        row = within.iloc[0]
        assert row["urgency_instability"] == False
        assert row["action_type_instability"] == False
        assert row["any_instability"] == False

    def test_urgency_instability_detected(self) -> None:
        within = compute_within_prompt_stability(_synthetic_repeated_outputs())
        row = within.iloc[0]
        assert row["urgency_instability"] == True

    def test_action_type_instability_detected(self) -> None:
        within = compute_within_prompt_stability(_synthetic_repeated_outputs())
        row = within.iloc[0]
        assert row["action_type_instability"] == True

    def test_remedy_strength_range(self) -> None:
        within = compute_within_prompt_stability(_synthetic_repeated_outputs())
        row = within.iloc[0]
        assert row["remedy_strength_range"] == pytest.approx(1.0)


class TestStabilityGroupSummary:
    def test_group_summary_rates(self) -> None:
        within = compute_within_prompt_stability(_synthetic_repeated_outputs())
        summary = compute_stability_group_summary(within)
        row = summary.iloc[0]
        assert row["n_prompts"] == 1
        assert row["urgency_instability_rate"] == pytest.approx(1.0)
        assert row["action_type_instability_rate"] == pytest.approx(1.0)
        assert row["any_instability_rate"] == pytest.approx(1.0)


class TestCounterfactualVsRandom:
    def test_comparison_deltas(self) -> None:
        pairwise = pd.DataFrame(
            [
                {
                    "variant_type": "arab_male_name_he",
                    "action_type_flip": True,
                    "legal_framing_bias_flag": True,
                },
                {
                    "variant_type": "arab_male_name_he",
                    "action_type_flip": False,
                    "legal_framing_bias_flag": False,
                },
            ]
        )
        stability = pd.DataFrame(
            [
                {
                    "variant_type": "arab_male_name_he",
                    "demographic_cue": "Ahmed",
                    "prompt_mode": "baseline",
                    "action_type_instability_rate": 0.2,
                    "any_instability_rate": 0.3,
                }
            ]
        )
        comparison = compare_counterfactual_vs_random_instability(pairwise, stability)
        row = comparison.iloc[0]
        assert row["counterfactual_action_flip_rate"] == pytest.approx(0.5)
        assert row["random_action_instability_rate"] == pytest.approx(0.2)
        assert row["delta_action_instability"] == pytest.approx(0.3)


class TestRunBatchRepetitions:
    @pytest.fixture()
    def isolated_project_dirs(self, tmp_path, monkeypatch):
        data_dir = tmp_path / "data"
        results_dir = tmp_path / "results"
        monkeypatch.setenv("DATA_DIR", str(data_dir))
        monkeypatch.setenv("RESULTS_DIR", str(results_dir))
        monkeypatch.setenv("MODEL_PROVIDER", "mock")
        monkeypatch.setenv("MODEL_NAME", "mock-benchassist")
        get_settings.cache_clear()
        return data_dir, results_dir

    def test_repetitions_produce_three_rows_per_case(
        self, isolated_project_dirs
    ) -> None:
        _, results_dir = isolated_project_dirs
        records = run_model_batch(
            provider="mock",
            limit=2,
            output_dir=results_dir / "outputs",
            schema_version="v2",
            prompt_mode="baseline",
            repetitions=3,
            mock_unstable=True,
        )
        assert len(records) == 6
        for variant_id in {record["variant_id"] for record in records}:
            reps = sorted(
                record["repetition_index"]
                for record in records
                if record["variant_id"] == variant_id
            )
            assert reps == [1, 2, 3]

    def test_repetition_index_defaults_to_one(self, isolated_project_dirs) -> None:
        _, results_dir = isolated_project_dirs
        records = run_model_batch(
            provider="mock",
            limit=1,
            output_dir=results_dir / "outputs",
        )
        assert records[0]["repetition_index"] == 1


class TestStabilityCLI:
    def test_run_stability_analysis_writes_files(self, tmp_path) -> None:
        outputs = _synthetic_repeated_outputs()
        input_path = tmp_path / "repeated_outputs.csv"
        outputs.to_csv(input_path, index=False)

        tables_dir = tmp_path / "tables"
        charts_dir = tmp_path / "charts"
        result = run_stability_analysis(
            input_path,
            tables_dir=tables_dir,
            charts_dir=charts_dir,
            output_suffix="test",
        )

        assert result["within_prompt_rows"] == 1
        assert (tables_dir / "stability_within_prompt_test.csv").exists()
        assert (tables_dir / "stability_group_summary_test.csv").exists()
        assert (charts_dir / "stability_any_instability_rate_by_variant_test.png").exists()

    def test_run_with_pairwise_writes_comparison(self, tmp_path) -> None:
        outputs = _synthetic_repeated_outputs()
        input_path = tmp_path / "repeated_outputs.csv"
        outputs.to_csv(input_path, index=False)

        pairwise_path = tmp_path / "pairwise.csv"
        pd.DataFrame(
            [
                {
                    "variant_type": "neutral_he",
                    "action_type_flip": False,
                    "legal_framing_bias_flag": False,
                },
                {
                    "variant_type": "arab_male_name_he",
                    "action_type_flip": True,
                    "legal_framing_bias_flag": True,
                },
            ]
        ).to_csv(pairwise_path, index=False)

        tables_dir = tmp_path / "tables"
        result = run_stability_analysis(
            input_path,
            pairwise_path=pairwise_path,
            tables_dir=tables_dir,
            charts_dir=tmp_path / "charts",
            output_suffix="test",
        )
        assert (
            tables_dir / "counterfactual_vs_random_instability_test.csv"
        ).exists()
        assert result["comparison_rows"] >= 1
