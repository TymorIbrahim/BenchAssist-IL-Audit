"""Tests for fairness-aware prompt mode and mitigation comparison."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from benchassist.data_generation import create_base_cases, create_counterfactual_cases
from benchassist.mitigation_comparison import compute_mitigation_comparison
from benchassist.model_client import MockModelClient, parse_bench_memo_output_v2
from benchassist.prompt_builder import build_prompt, load_system_prompt
from benchassist.run_batch import resolve_model_output_basename, run_model_batch


@pytest.fixture()
def sample_counterfactual():
    return create_counterfactual_cases(create_base_cases())[0]


class TestFairnessAwarePrompt:
    def test_fairness_prompt_includes_fairness_instructions(
        self, sample_counterfactual
    ) -> None:
        messages = build_prompt(
            sample_counterfactual,
            schema_version="v2",
            prompt_mode="fairness_aware",
        )
        system = messages[0]["content"]
        assert "Fairness requirements" in system
        assert "legally equivalent cases equivalently" in system
        assert "Do not infer credibility from language quality" in system

    def test_fairness_prompt_includes_v2_schema_fields(
        self, sample_counterfactual
    ) -> None:
        messages = build_prompt(
            sample_counterfactual,
            schema_version="v2",
            prompt_mode="fairness_aware",
        )
        system = messages[0]["content"]
        assert "BenchMemoOutputV2" in system
        assert "recommended_action_type" in system
        assert "remedy_strength_score" in system
        assert "party_credibility_framing" in system

    def test_fairness_aware_with_v1_raises(self, sample_counterfactual) -> None:
        with pytest.raises(ValueError, match="requires schema_version='v2'"):
            build_prompt(
                sample_counterfactual,
                schema_version="v1",
                prompt_mode="fairness_aware",
            )

    def test_invalid_prompt_mode_raises(self, sample_counterfactual) -> None:
        with pytest.raises(ValueError, match="Unknown prompt_mode"):
            build_prompt(
                sample_counterfactual,
                schema_version="v2",
                prompt_mode="unknown_mode",
            )

    def test_load_system_prompt_fairness_aware_file(self) -> None:
        prompt = load_system_prompt(schema_version="v2", prompt_mode="fairness_aware")
        assert "Every recommendation must be reviewed by a human judge or clerk" in prompt


class TestRunBatchPromptMode:
    def test_run_batch_mock_fairness_aware_v2(self, tmp_path, monkeypatch) -> None:
        data_dir = tmp_path / "data"
        results_dir = tmp_path / "results"
        monkeypatch.setenv("DATA_DIR", str(data_dir))
        monkeypatch.setenv("RESULTS_DIR", str(results_dir))
        monkeypatch.setenv("MODEL_PROVIDER", "mock")
        from benchassist.config import get_settings

        get_settings.cache_clear()

        records = run_model_batch(
            provider="mock",
            limit=2,
            output_dir=results_dir / "outputs",
            schema_version="v2",
            prompt_mode="fairness_aware",
        )

        basename = resolve_model_output_basename(
            schema_version="v2",
            prompt_mode="fairness_aware",
            provider="mock",
            model_name="mock-benchassist",
        )
        jsonl_path = results_dir / "outputs" / f"{basename}.jsonl"
        assert jsonl_path.exists()
        assert len(records) == 2
        assert records[0]["schema_version"] == "v2"
        assert records[0]["prompt_mode"] == "fairness_aware"
        assert records[0]["provider"] == "mock"
        assert records[0]["recommended_action_type"] is not None
        assert records[0]["parse_error"] is None

    def test_output_basename_legacy_default(self) -> None:
        assert (
            resolve_model_output_basename(
                schema_version="v1",
                prompt_mode="baseline",
                provider="mock",
                model_name="mock-benchassist",
            )
            == "model_outputs"
        )
        assert (
            resolve_model_output_basename(
                schema_version="v2",
                prompt_mode="baseline",
                provider="mock",
                model_name="mock-benchassist",
            )
            == "model_outputs_mock_v2_baseline"
        )
        assert (
            resolve_model_output_basename(
                schema_version="v2",
                prompt_mode="fairness_aware",
                provider="mock",
                model_name="mock-benchassist",
            )
            == "model_outputs_mock_v2_fairness_aware"
        )


class TestMockFairnessAwareV2:
    def test_mock_returns_valid_v2_json_fairness_mode(
        self, sample_counterfactual
    ) -> None:
        messages = build_prompt(
            sample_counterfactual,
            schema_version="v2",
            prompt_mode="fairness_aware",
        )
        client = MockModelClient(schema_version="v2", prompt_mode="fairness_aware")
        raw = client.generate(messages)
        parsed, error = parse_bench_memo_output_v2(raw)
        assert error is None
        assert parsed is not None
        assert parsed.recommended_action_type
        assert 0 <= parsed.remedy_strength_score <= 5


class TestMitigationComparison:
    def test_compute_deltas_from_synthetic_summaries(self) -> None:
        baseline = pd.DataFrame(
            [
                {
                    "variant_type": "arab_male_name_he",
                    "demographic_cue": "Ahmed",
                    "action_type_flip_rate": 0.4,
                    "legal_framing_bias_flag_rate": 0.5,
                    "remedy_weaker_rate": 0.3,
                    "evidence_burden_higher_rate": 0.2,
                    "credibility_more_skeptical_rate": 0.25,
                },
                {
                    "variant_type": "broken_hebrew",
                    "demographic_cue": "broken Hebrew",
                    "action_type_flip_rate": 0.6,
                    "legal_framing_bias_flag_rate": 0.7,
                    "remedy_weaker_rate": 0.5,
                    "evidence_burden_higher_rate": 0.4,
                    "credibility_more_skeptical_rate": 0.45,
                },
            ]
        )
        fairness = pd.DataFrame(
            [
                {
                    "variant_type": "arab_male_name_he",
                    "demographic_cue": "Ahmed",
                    "action_type_flip_rate": 0.2,
                    "legal_framing_bias_flag_rate": 0.3,
                    "remedy_weaker_rate": 0.1,
                    "evidence_burden_higher_rate": 0.1,
                    "credibility_more_skeptical_rate": 0.15,
                },
                {
                    "variant_type": "broken_hebrew",
                    "demographic_cue": "broken Hebrew",
                    "action_type_flip_rate": 0.5,
                    "legal_framing_bias_flag_rate": 0.6,
                    "remedy_weaker_rate": 0.4,
                    "evidence_burden_higher_rate": 0.35,
                    "credibility_more_skeptical_rate": 0.4,
                },
            ]
        )

        comparison = compute_mitigation_comparison(baseline, fairness)
        assert len(comparison) == 2

        arab_row = comparison.loc[
            comparison["variant_type"] == "arab_male_name_he"
        ].iloc[0]
        assert arab_row["baseline_action_type_flip_rate"] == pytest.approx(0.4)
        assert arab_row["fairness_action_type_flip_rate"] == pytest.approx(0.2)
        assert arab_row["delta_action_type_flip_rate"] == pytest.approx(-0.2)
        assert arab_row["delta_legal_framing_bias_flag_rate"] == pytest.approx(-0.2)
