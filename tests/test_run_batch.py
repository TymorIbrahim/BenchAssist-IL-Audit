"""Smoke tests for the model batch CLI."""

from __future__ import annotations

import json

import pytest

from benchassist.config import get_settings
from benchassist.run_batch import run_model_batch


@pytest.fixture()
def isolated_project_dirs(tmp_path, monkeypatch):
    """Point DATA_DIR and RESULTS_DIR at a temporary tree."""
    data_dir = tmp_path / "data"
    results_dir = tmp_path / "results"
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("RESULTS_DIR", str(results_dir))
    monkeypatch.setenv("MODEL_PROVIDER", "mock")
    monkeypatch.setenv("MODEL_NAME", "mock-benchassist")
    get_settings.cache_clear()
    yield data_dir, results_dir


class TestRunModelBatchSmoke:
    def test_mock_batch_writes_three_records(
        self, isolated_project_dirs
    ) -> None:
        _, results_dir = isolated_project_dirs
        output_dir = results_dir / "outputs"

        records = run_model_batch(
            provider="mock",
            limit=3,
            output_dir=output_dir,
        )

        jsonl_path = output_dir / "model_outputs.jsonl"
        csv_path = output_dir / "model_outputs.csv"

        assert len(records) == 3
        assert jsonl_path.exists()
        assert csv_path.exists()

        lines = [line for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line]
        assert len(lines) == 3

        first = json.loads(lines[0])
        assert first["run_id"]
        assert first["case_id"]
        assert first["variant_id"]
        assert first["legal_area"] == "housing"
        assert first["parse_error"] is None
