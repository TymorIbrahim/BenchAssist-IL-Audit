"""Smoke test for end-to-end pipeline verification."""

from __future__ import annotations

from pathlib import Path

import pytest

from benchassist.config import get_settings
from benchassist.verify_pipeline import verify_pipeline


@pytest.fixture()
def isolated_dirs(tmp_path, monkeypatch):
    """Use temporary data/results trees."""
    data_dir = tmp_path / "data"
    results_dir = tmp_path / "results"
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("RESULTS_DIR", str(results_dir))
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    get_settings.cache_clear()
    yield data_dir, results_dir


class TestVerifyPipeline:
    def test_verify_pipeline_completes_with_mock(self, isolated_dirs) -> None:
        _, results_dir = isolated_dirs

        result = verify_pipeline(provider="mock")

        assert result.base_case_count == 12
        assert result.counterfactual_count == 120
        assert result.model_output_count == 120
        assert result.group_summary_path.exists()
        assert result.audit_report_path.exists()
        assert result.charts_dir.exists()

        assert (results_dir / "outputs" / "model_outputs.csv").exists()
        assert (results_dir / "outputs" / "model_outputs.jsonl").exists()
        assert (results_dir / "tables" / "per_case_comparison.csv").exists()
        assert (results_dir / "tables" / "flagged_cases.csv").exists()
        assert len(list(result.charts_dir.glob("*.png"))) >= 1

    def test_main_exit_code_zero(self, isolated_dirs, monkeypatch) -> None:
        from benchassist import verify_pipeline as vp_module

        monkeypatch.setattr(vp_module, "verify_pipeline", verify_pipeline)
        assert vp_module.main([]) == 0
