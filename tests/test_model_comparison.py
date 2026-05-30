"""Tests for multi-model support, output naming, and model comparison."""

from __future__ import annotations

import pandas as pd
import pytest

from benchassist.config import get_settings
from benchassist.model_client import (
    GeminiModelClient,
    MockModelClient,
    OpenAIModelClient,
    get_model_client,
)
from benchassist.model_comparison import (
    build_model_comparison_long,
    build_model_comparison_pivot,
    generate_model_comparison_charts,
    run_model_comparison,
)
from benchassist.output_naming import (
    build_run_group_id,
    resolve_model_output_basename,
    sanitize_output_token,
)
from benchassist.run_batch import run_model_batch


@pytest.fixture()
def isolated_project_dirs(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    results_dir = tmp_path / "results"
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("RESULTS_DIR", str(results_dir))
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    monkeypatch.setenv("MODEL_NAME", "mock-benchassist")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    yield data_dir, results_dir


def _synthetic_group_summary(variant_type: str, flip_rate: float) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "variant_type": variant_type,
                "demographic_cue": "test",
                "n_pairs": 1,
                "action_type_flip_rate": flip_rate,
                "legal_framing_bias_flag_rate": flip_rate + 0.05,
                "remedy_weaker_rate": flip_rate + 0.02,
                "evidence_burden_higher_rate": flip_rate + 0.03,
                "credibility_more_skeptical_rate": flip_rate + 0.04,
                "rights_orientation_weaker_rate": flip_rate + 0.01,
                "avg_remedy_strength_delta": -flip_rate,
                "avg_evidence_burden_delta": flip_rate,
                "avg_credibility_skepticism_delta": flip_rate,
                "avg_rights_orientation_delta": -flip_rate,
            }
        ]
    )


class TestOutputNaming:
    def test_sanitize_output_token(self) -> None:
        assert sanitize_output_token("gemini-2.5/flash-lite") == "gemini-2.5-flash-lite"
        assert sanitize_output_token("  Weird Name!! ") == "weird-name"

    def test_resolve_basename_legacy_mock_v1(self) -> None:
        assert (
            resolve_model_output_basename(
                provider="mock",
                model_name="mock-benchassist",
                schema_version="v1",
                prompt_mode="baseline",
            )
            == "model_outputs"
        )

    def test_resolve_basename_includes_model_for_v2(self) -> None:
        assert (
            resolve_model_output_basename(
                provider="mock",
                model_name="mock-benchassist",
                schema_version="v2",
                prompt_mode="baseline",
            )
            == "model_outputs_mock_v2_baseline"
        )
        assert (
            resolve_model_output_basename(
                provider="gemini",
                model_name="gemini-2.5-flash-lite",
                schema_version="v2",
                prompt_mode="baseline",
            )
            == "model_outputs_gemini-2.5-flash-lite_v2_baseline"
        )

    def test_output_prefix_override_is_sanitized(self) -> None:
        assert (
            resolve_model_output_basename(
                provider="gemini",
                model_name="gemini-2.5-flash",
                schema_version="v2",
                prompt_mode="baseline",
                output_prefix="my/run name",
            )
            == "my-run-name"
        )

    def test_build_run_group_id(self) -> None:
        group_id = build_run_group_id(
            model_name="gemini-2.5-flash-lite",
            schema_version="v2",
            prompt_mode="baseline",
            timestamp="2026-05-29T12:00:00",
        )
        assert group_id == "gemini-2.5-flash-lite_v2_baseline_2026-05-29T120000"


class TestModelProviders:
    def test_mock_provider_still_works(self) -> None:
        client = get_model_client("mock")
        assert isinstance(client, MockModelClient)
        assert client.provider == "mock"
        raw = client.generate([{"role": "user", "content": "פינוי דחוף עקב עובש"}])
        assert raw.startswith("{")

    def test_gemini_fails_without_api_key(self, monkeypatch) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        get_settings.cache_clear()
        try:
            import google.genai  # noqa: F401
        except ImportError:
            pytest.skip("google-genai not installed")
        with pytest.raises(ValueError, match="Gemini API key"):
            GeminiModelClient(model_name="gemini-2.5-flash-lite")

    def test_openai_fails_without_dependency(self, monkeypatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        get_settings.cache_clear()
        try:
            import openai  # noqa: F401
        except ImportError:
            with pytest.raises(ImportError, match="openai is required"):
                OpenAIModelClient(model_name="gpt-4o-mini")
            return
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            OpenAIModelClient(model_name="gpt-4o-mini")


class TestRunBatchMetadata:
    def test_run_batch_includes_provider_and_run_group_id(
        self, isolated_project_dirs
    ) -> None:
        _, results_dir = isolated_project_dirs
        output_dir = results_dir / "outputs"
        records = run_model_batch(
            provider="mock",
            limit=2,
            output_dir=output_dir,
            schema_version="v2",
            prompt_mode="baseline",
            temperature=0.0,
        )
        assert len(records) == 2
        first = records[0]
        assert first["provider"] == "mock"
        assert first["model_name"] == "mock-benchassist"
        assert first["temperature"] == 0.0
        assert first["run_group_id"]
        assert first["schema_version"] == "v2"
        assert first["prompt_mode"] == "baseline"
        assert first["repetition_index"] == 1
        assert records[0]["run_group_id"] == records[1]["run_group_id"]
        assert records[0]["run_id"] != records[1]["run_id"]

        basename = resolve_model_output_basename(
            provider="mock",
            model_name="mock-benchassist",
            schema_version="v2",
            prompt_mode="baseline",
        )
        assert (output_dir / f"{basename}.csv").exists()

    def test_output_prefix_override_writes_custom_filename(
        self, isolated_project_dirs
    ) -> None:
        _, results_dir = isolated_project_dirs
        output_dir = results_dir / "outputs"
        run_model_batch(
            provider="mock",
            limit=1,
            output_dir=output_dir,
            schema_version="v2",
            prompt_mode="baseline",
            output_prefix="my_run_name",
        )
        assert (output_dir / "my_run_name.csv").exists()


class TestModelComparison:
    def test_loads_two_synthetic_summaries(self, tmp_path) -> None:
        mock_path = tmp_path / "v2_group_summary_mock_baseline.csv"
        gemini_path = tmp_path / "v2_group_summary_gemini_flash_lite_baseline.csv"
        _synthetic_group_summary("arab_male_name_he", 0.4).to_csv(
            mock_path, index=False
        )
        _synthetic_group_summary("arab_male_name_he", 0.2).to_csv(
            gemini_path, index=False
        )

        long_df = build_model_comparison_long(
            [(mock_path, pd.read_csv(mock_path)), (gemini_path, pd.read_csv(gemini_path))]
        )
        assert len(long_df) == 2
        assert set(long_df["model_label"]) == {"mock-benchassist", "gemini-2.5-flash-lite"}

    def test_writes_combined_and_pivot_tables(self, tmp_path, monkeypatch) -> None:
        results_dir = tmp_path / "results"
        tables_dir = results_dir / "tables"
        charts_dir = results_dir / "charts"
        monkeypatch.setenv("RESULTS_DIR", str(results_dir))
        get_settings.cache_clear()

        mock_path = tables_dir / "v2_group_summary_mock_baseline.csv"
        gemini_path = tables_dir / "v2_group_summary_gemini_flash_lite_baseline.csv"
        tables_dir.mkdir(parents=True)
        _synthetic_group_summary("broken_hebrew", 0.5).to_csv(mock_path, index=False)
        _synthetic_group_summary("broken_hebrew", 0.3).to_csv(gemini_path, index=False)

        result = run_model_comparison([mock_path, gemini_path], charts_dir=charts_dir)
        assert result["output_path"].exists()
        assert result["pivot_output_path"].exists()
        assert not result["comparison"].empty
        assert not result["pivot"].empty

    def test_generates_comparison_charts(self, tmp_path) -> None:
        charts_dir = tmp_path / "charts"
        long_df = build_model_comparison_long(
            [
                (
                    tmp_path / "v2_group_summary_mock_baseline.csv",
                    _synthetic_group_summary("arab_male_name_he", 0.4),
                ),
                (
                    tmp_path / "v2_group_summary_gemini_flash_lite_baseline.csv",
                    _synthetic_group_summary("arab_male_name_he", 0.2),
                ),
            ]
        )
        chart_paths = generate_model_comparison_charts(long_df, charts_dir)
        assert len(chart_paths) == 4
        for path in chart_paths.values():
            assert path.exists()

    def test_pivot_includes_metric_columns(self) -> None:
        long_df = pd.DataFrame(
            [
                {
                    "variant_type": "broken_hebrew",
                    "model_label": "mock",
                    "action_type_flip_rate": 0.5,
                    "legal_framing_bias_flag_rate": 0.6,
                },
                {
                    "variant_type": "broken_hebrew",
                    "model_label": "gemini-2.5-flash-lite",
                    "action_type_flip_rate": 0.3,
                    "legal_framing_bias_flag_rate": 0.4,
                },
            ]
        )
        pivot = build_model_comparison_pivot(long_df)
        assert "mock__action_type_flip_rate" in pivot.columns
        assert "gemini-2.5-flash-lite__legal_framing_bias_flag_rate" in pivot.columns
