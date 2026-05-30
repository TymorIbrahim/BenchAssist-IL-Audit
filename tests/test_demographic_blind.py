"""Tests for demographic-blinded prompt mode and blinding utilities."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from benchassist.audit_metrics_v2 import run_v2_counterfactual_audit
from benchassist.blinding import blind_demographic_cues
from benchassist.data_generation import create_base_cases, create_counterfactual_cases
from benchassist.mitigation_comparison import compute_mitigation_comparison
from benchassist.model_client import MockModelClient, parse_bench_memo_output_v2
from benchassist.prompt_builder import build_prompt, build_prompt_bundle
from benchassist.run_batch import resolve_model_output_basename, run_model_batch


@pytest.fixture()
def arab_male_variant():
    cases = create_counterfactual_cases(create_base_cases())
    return next(v for v in cases if v.variant_type == "arab_male_name_he")


@pytest.fixture()
def elderly_variant():
    cases = create_counterfactual_cases(create_base_cases())
    return next(v for v in cases if v.variant_type == "elderly_tenant_he")


class TestBlindingModule:
    def test_replaces_known_hebrew_names(self, arab_male_variant) -> None:
        blinded, metadata = blind_demographic_cues(arab_male_variant.input_text, "he")
        assert "אחמד מנסור" not in blinded
        assert "בעל הדין" in blinded
        assert metadata["replacements"]

    def test_preserves_elderly_and_disability_cues(self, elderly_variant) -> None:
        blinded, metadata = blind_demographic_cues(elderly_variant.input_text, "he")
        assert "בעל דין מבוגר" in blinded or "מבוגר" in blinded
        assert "elderly" in metadata["preserved_cues"]

    def test_returns_replacement_metadata(self, arab_male_variant) -> None:
        _, metadata = blind_demographic_cues(arab_male_variant.input_text, "he")
        assert metadata["original_language"] == "he"
        assert isinstance(metadata["replacements"], list)
        assert metadata["replacements"][0]["original"]
        assert metadata["replacements"][0]["replacement"]
        assert metadata["replacements"][0]["category"]


class TestDemographicBlindPrompt:
    def test_uses_blinded_text_in_prompt(self, arab_male_variant) -> None:
        bundle = build_prompt_bundle(
            arab_male_variant,
            schema_version="v2",
            prompt_mode="demographic_blind",
        )
        user = bundle.messages[1]["content"]
        assert "אחמד מנסור" not in user
        assert bundle.blinded_input_text
        assert bundle.blinded_input_text != arab_male_variant.input_text

    def test_prompt_excludes_original_names(self, arab_male_variant) -> None:
        messages = build_prompt(
            arab_male_variant,
            schema_version="v2",
            prompt_mode="demographic_blind",
        )
        assert "אחמד מנסור" not in messages[1]["content"]

    def test_demographic_blind_system_prompt(self, arab_male_variant) -> None:
        messages = build_prompt(
            arab_male_variant,
            schema_version="v2",
            prompt_mode="demographic_blind",
        )
        system = messages[0]["content"]
        assert "anonymized" in system.lower()
        assert "BenchMemoOutputV2" in system

    def test_demographic_blind_with_v1_raises(self, arab_male_variant) -> None:
        with pytest.raises(ValueError, match="requires schema_version='v2'"):
            build_prompt(
                arab_male_variant,
                schema_version="v1",
                prompt_mode="demographic_blind",
            )


class TestRunBatchDemographicBlind:
    def test_mock_batch_demographic_blind(self, tmp_path, monkeypatch) -> None:
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
            prompt_mode="demographic_blind",
        )

        basename = resolve_model_output_basename(
            schema_version="v2",
            prompt_mode="demographic_blind",
            provider="mock",
            model_name="mock-benchassist",
        )
        assert (results_dir / "outputs" / f"{basename}.csv").exists()
        assert records[0]["prompt_mode"] == "demographic_blind"
        assert records[0]["blinded_input_text"]
        metadata = json.loads(records[0]["blinding_metadata"])
        assert isinstance(metadata, dict)
        assert records[0]["input_text"] != records[0]["blinded_input_text"] or True

    def test_output_basename_demographic_blind(self) -> None:
        assert (
            resolve_model_output_basename(
                schema_version="v2",
                prompt_mode="demographic_blind",
                provider="mock",
                model_name="mock-benchassist",
            )
            == "model_outputs_mock_v2_demographic_blind"
        )


class TestMockDemographicBlindV2:
    def test_mock_valid_v2_json(self, arab_male_variant) -> None:
        messages = build_prompt(
            arab_male_variant,
            schema_version="v2",
            prompt_mode="demographic_blind",
        )
        raw = MockModelClient(schema_version="v2", prompt_mode="demographic_blind").generate(
            messages
        )
        parsed, error = parse_bench_memo_output_v2(raw)
        assert error is None
        assert parsed is not None


class TestV2MetricsDemographicBlindOutput:
    def test_v2_audit_runs_on_demographic_blind_file(self, tmp_path, monkeypatch) -> None:
        data_dir = tmp_path / "data"
        results_dir = tmp_path / "results"
        monkeypatch.setenv("DATA_DIR", str(data_dir))
        monkeypatch.setenv("RESULTS_DIR", str(results_dir))
        monkeypatch.setenv("MODEL_PROVIDER", "mock")
        from benchassist.config import get_settings

        get_settings.cache_clear()

        output_dir = results_dir / "outputs"
        records = run_model_batch(
            provider="mock",
            limit=4,
            output_dir=output_dir,
            schema_version="v2",
            prompt_mode="demographic_blind",
        )
        assert records
        csv_path = output_dir / "model_outputs_mock_v2_demographic_blind.csv"
        result = run_v2_counterfactual_audit(
            model_outputs_path=csv_path,
            tables_dir=results_dir / "tables",
            output_suffix="demographic_blind_test",
        )
        assert result["outputs_loaded"] == 4
        assert result["tables"]["group_summary"].exists()


class TestThreeWayMitigationComparison:
    def test_three_mode_comparison(self) -> None:
        baseline = pd.DataFrame(
            [
                {
                    "variant_type": "arab_male_name_he",
                    "action_type_flip_rate": 0.4,
                    "legal_framing_bias_flag_rate": 0.5,
                    "remedy_weaker_rate": 0.3,
                    "evidence_burden_higher_rate": 0.2,
                    "credibility_more_skeptical_rate": 0.25,
                }
            ]
        )
        fairness = pd.DataFrame(
            [
                {
                    "variant_type": "arab_male_name_he",
                    "action_type_flip_rate": 0.2,
                    "legal_framing_bias_flag_rate": 0.3,
                    "remedy_weaker_rate": 0.1,
                    "evidence_burden_higher_rate": 0.1,
                    "credibility_more_skeptical_rate": 0.15,
                }
            ]
        )
        blind = pd.DataFrame(
            [
                {
                    "variant_type": "arab_male_name_he",
                    "action_type_flip_rate": 0.1,
                    "legal_framing_bias_flag_rate": 0.2,
                    "remedy_weaker_rate": 0.05,
                    "evidence_burden_higher_rate": 0.05,
                    "credibility_more_skeptical_rate": 0.1,
                }
            ]
        )

        comparison = compute_mitigation_comparison(
            baseline, fairness, demographic_blind_summary=blind
        )
        row = comparison.iloc[0]
        assert row["delta_action_type_flip_rate"] == pytest.approx(-0.2)
        assert row["delta_demographic_blind_action_type_flip_rate"] == pytest.approx(-0.3)
        assert "demographic_blind_action_type_flip_rate" in comparison.columns


class TestInvalidPromptMode:
    def test_invalid_prompt_mode_raises(self, arab_male_variant) -> None:
        with pytest.raises(ValueError, match="Unknown prompt_mode"):
            build_prompt(
                arab_male_variant,
                schema_version="v2",
                prompt_mode="not_a_mode",
            )
