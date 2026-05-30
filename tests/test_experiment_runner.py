"""Tests for the safe experiment runner."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from benchassist.config import get_settings
from benchassist.experiment_runner import (
    build_command_plan,
    check_safety_before_execute,
    estimate_cost,
    experiment_dir,
    load_experiment_config,
    output_prefix_for_run,
    run_command,
    run_experiment,
    should_skip_step,
    write_experiment_artifacts,
    PlannedCommand,
)


@pytest.fixture()
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture()
def mock_config_path(project_root: Path) -> Path:
    return project_root / "configs" / "audit_experiment_mock_qa.yaml"


@pytest.fixture()
def gemini_config_path(project_root: Path) -> Path:
    return project_root / "configs" / "audit_experiment_gemini_flash_lite.yaml"


@pytest.fixture()
def isolated_results(tmp_path, monkeypatch):
    results = tmp_path / "results"
    data = tmp_path / "data"
    for sub in ("outputs", "tables", "report", "experiments", "charts"):
        (results / sub).mkdir(parents=True)
    (data / "processed").mkdir(parents=True)
    (data / "audit").mkdir(parents=True)
    monkeypatch.setenv("RESULTS_DIR", str(results))
    monkeypatch.setenv("DATA_DIR", str(data))
    get_settings.cache_clear()
    return results


class TestExperimentConfig:
    def test_yaml_loads(self, mock_config_path: Path) -> None:
        config = load_experiment_config(mock_config_path)
        assert config.experiment_name == "mock_qa_experiment"
        assert config.provider == "mock"
        assert config.limit == 10
        assert "baseline" in config.prompt_modes
        assert config.grounded.enabled is True

    def test_cost_estimator_positive(self, mock_config_path: Path) -> None:
        config = load_experiment_config(mock_config_path)
        cost = estimate_cost(config, n_counterfactual=100)
        assert cost.v2_calls > 0
        assert cost.estimated_total_cost_usd > 0

    def test_output_prefix_sanitization(self, mock_config_path: Path) -> None:
        config = load_experiment_config(mock_config_path)
        prefix = output_prefix_for_run(
            config, schema_version="v2", prompt_mode="fairness_aware"
        )
        assert "/" not in prefix
        assert "mock_qa_experiment" in prefix


class TestCommandPlan:
    def test_includes_prompt_modes(self, mock_config_path: Path) -> None:
        config = load_experiment_config(mock_config_path)
        plan = build_command_plan(config)
        step_ids = {s.step_id for s in plan}
        assert "run_batch_baseline" in step_ids
        assert "run_batch_fairness_aware" in step_ids
        assert "run_batch_demographic_blind" in step_ids
        assert "mitigation_comparison" in step_ids


class TestDryRun:
    def test_dry_run_no_subprocess(self, mock_config_path: Path, isolated_results, tmp_path) -> None:
        log = tmp_path / "log.txt"
        log.write_text("", encoding="utf-8")
        status, rc = run_command(
            [sys.executable, "-c", "print('should not run')"],
            log,
            dry_run=True,
        )
        assert status == "DRY_RUN"
        assert rc == 0
        assert "DRY_RUN skipped" in log.read_text()

    def test_dry_run_writes_artifacts(self, mock_config_path: Path, isolated_results) -> None:
        config = load_experiment_config(mock_config_path)
        rc = run_experiment(config, dry_run=True, execute=False)
        assert rc == 0
        exp = experiment_dir(config)
        assert (exp / "command_plan.txt").exists()
        assert (exp / "dry_run_summary.md").exists()
        assert (exp / "cost_estimate.json").exists()


class TestSafety:
    def test_blocks_gemini_without_api_key(
        self, gemini_config_path: Path, monkeypatch
    ) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        get_settings.cache_clear()
        config = load_experiment_config(gemini_config_path)
        plan = build_command_plan(config)
        errors = check_safety_before_execute(
            config, plan, execute=True, force=False, resume=False
        )
        assert any("GEMINI_API_KEY" in e or "GOOGLE_API_KEY" in e for e in errors)


class TestResume:
    def test_skip_existing_outputs(self, tmp_path: Path) -> None:
        existing = tmp_path / "out.csv"
        existing.write_text("x", encoding="utf-8")
        step = PlannedCommand(
            step_id="test",
            command=["echo", "hi"],
            expected_outputs=[existing],
        )
        assert should_skip_step(step, resume=True, force=False) is True
        assert should_skip_step(step, resume=False, force=False) is False
        assert should_skip_step(step, resume=True, force=True) is False


class TestMockExecute:
    def test_execute_mock_creates_experiment_dir(
        self, mock_config_path: Path, isolated_results, monkeypatch
    ) -> None:
        config = load_experiment_config(mock_config_path)
        rc = run_experiment(
            config,
            dry_run=False,
            execute=True,
            force=True,
            continue_on_error=False,
        )
        assert rc == 0
        exp = experiment_dir(config)
        assert exp.exists()
        assert (exp / "execution_log.txt").exists()
        log_text = (exp / "execution_log.txt").read_text(encoding="utf-8")
        assert "SUCCESS" in log_text or "SKIPPED" in log_text
