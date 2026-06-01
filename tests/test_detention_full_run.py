"""Tests for full Gemini detention run planning (no live API calls)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
FULL_CONFIG = ROOT / "configs" / "gemini_detention_full.yaml"
PILOT_CONFIG = ROOT / "configs" / "gemini_detention_pilot.yaml"


def test_load_full_config() -> None:
    from benchassist.detention_gemini_config import load_detention_gemini_config

    cfg = load_detention_gemini_config(FULL_CONFIG)
    assert cfg.use_case == "detention"
    assert cfg.is_full_run
    assert cfg.model == "gemini-2.5-flash-lite"
    assert not cfg.methodology.real_cases_in_strict_rates
    assert cfg.dashboard.data_status == "gemini_full"
    assert cfg.safety.stop_on_parse_error_rate_above == 0.10
    assert cfg.selected_inputs_path.name == "full_selected_inputs.jsonl"


def test_full_run_planner_dry_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from benchassist.detention_full_run_plan import run_full_run_plan
    from benchassist.detention_gemini_config import load_detention_gemini_config

    cfg = load_detention_gemini_config(FULL_CONFIG)
    cfg.output_dir = tmp_path / "full"
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-printed")

    manifest = run_full_run_plan(cfg, resume=False)
    assert (cfg.output_dir / "dry_run_manifest.json").exists()
    assert manifest["checks_passed"] is True
    assert manifest["request_plan"]["total_requests"] > 0
    assert manifest["row_counts"]["strict_eligible_synthetic"] > 0
    raw = (cfg.output_dir / "dry_run_manifest.json").read_text(encoding="utf-8")
    assert "test-key-not-printed" not in raw


def test_full_planner_refuses_if_pilot_qa_failed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from benchassist.detention_full_run_plan import run_full_run_plan
    from benchassist.detention_gemini_config import load_detention_gemini_config, verify_pilot_qa_passed

    cfg = load_detention_gemini_config(FULL_CONFIG)
    cfg.output_dir = tmp_path / "full"
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    with patch("benchassist.detention_full_run_plan.verify_pilot_qa_passed") as mock_qa:
        mock_qa.return_value = {"passed": False, "checks": [{"name": "pilot_qa", "ok": False, "detail": "fail"}]}
        manifest = run_full_run_plan(cfg, resume=False)
    assert manifest["checks_passed"] is False
    pilot_check = next(c for c in manifest["checks"] if c["name"] == "pilot_qa_passed")
    assert pilot_check["ok"] is False


def test_full_planner_refuses_overwrite_conflict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from benchassist.detention_full_run_plan import run_full_run_plan
    from benchassist.detention_gemini_config import load_detention_gemini_config

    cfg = load_detention_gemini_config(FULL_CONFIG)
    cfg.output_dir = tmp_path / "full"
    cfg.output_dir.mkdir(parents=True)
    cfg.parsed_outputs_path.write_text('{"x":1}\n', encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    manifest = run_full_run_plan(cfg, resume=False)
    collision = next(c for c in manifest["checks"] if c["name"] == "output_collision")
    assert collision["ok"] is False


def test_full_runner_refuses_without_dry_run_manifest(tmp_path: Path) -> None:
    from benchassist.detention_gemini_config import load_detention_gemini_config
    from benchassist.detention_gemini_full import run_full

    cfg = load_detention_gemini_config(FULL_CONFIG)
    cfg.output_dir = tmp_path / "full"
    with pytest.raises(FileNotFoundError, match="Dry-run manifest missing"):
        run_full(cfg)


def test_full_runner_refuses_when_checks_failed(tmp_path: Path) -> None:
    from benchassist.detention_gemini_config import load_detention_gemini_config
    from benchassist.detention_gemini_full import run_full

    cfg = load_detention_gemini_config(FULL_CONFIG)
    cfg.output_dir = tmp_path / "full"
    cfg.output_dir.mkdir(parents=True)
    cfg.dry_run_manifest_path.write_text(json.dumps({"checks_passed": False}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="checks_passed=false"):
        run_full(cfg)


def test_full_runner_resume_skips_completed(tmp_path: Path) -> None:
    from unittest.mock import MagicMock

    from benchassist.detention_gemini_config import load_detention_gemini_config, request_key, select_pilot_rows, write_jsonl
    from benchassist.detention_gemini_full import run_full

    cfg = load_detention_gemini_config(FULL_CONFIG)
    cfg.output_dir = tmp_path / "full"
    cfg.rate_limit.min_delay_seconds = 0
    cfg.output_dir.mkdir(parents=True)
    cfg.dry_run_manifest_path.write_text(json.dumps({"checks_passed": True}), encoding="utf-8")

    row = select_pilot_rows(cfg)[0]
    rk = request_key(row, "baseline")
    write_jsonl(cfg.parsed_outputs_path, [{"request_key": rk, "parse_status": "success", "prompt_mode": "baseline"}], append=False)

    mock_client = MagicMock()
    mock_client.generate.return_value = json.dumps(
        {
            "case_summary": "test",
            "legal_area": "arrest_extension",
            "dangerousness_level": "low",
            "obstruction_risk_level": "low",
            "reasonable_suspicion_assessment": "moderate",
            "investigative_necessity": "low",
            "recommended_action_type": "release_with_conditions",
            "recommended_duration_days": None,
            "less_restrictive_alternatives_considered": ["ערובה"],
            "evidence_burden_level": "medium",
            "suspect_credibility_framing": "neutral",
            "rights_orientation": "balanced",
            "procedural_safeguards_mentioned": ["זכות לייצוג"],
            "reasoning_text": "Test reasoning based on facts.",
            "evidence_needed": ["תסקיר"],
            "risk_flags": [],
            "confidence": 0.5,
            "limitations": ["Not legal advice"],
        }
    )

    with patch("benchassist.model_client.GeminiModelClient", return_value=mock_client):
        manifest = run_full(cfg, resume=True)

    total_requests = len(select_pilot_rows(cfg)) * len(cfg.prompt_modes)
    assert manifest["stats"]["skipped_resume"] >= 1
    assert mock_client.generate.call_count < total_requests


def test_full_analysis_scaffold(tmp_path: Path) -> None:
    from benchassist.detention_full_analysis import run_full_analysis
    from benchassist.detention_mock_runner import generate_mock_memo
    from benchassist.detention_gemini_config import load_detention_gemini_config, select_pilot_rows

    cfg = load_detention_gemini_config(PILOT_CONFIG)
    rows = select_pilot_rows(cfg)[:4]
    outputs = tmp_path / "parsed_outputs.jsonl"
    with open(outputs, "w", encoding="utf-8") as fh:
        for row in rows:
            out = generate_mock_memo(row, prompt_mode="baseline")
            fh.write(json.dumps(out, ensure_ascii=False) + "\n")

    analysis_dir = tmp_path / "analysis"
    result = run_full_analysis(outputs, output_dir=analysis_dir)
    report = result["paths"]["report"].read_text(encoding="utf-8")
    assert "proof of unlawful discrimination" in report.lower()
    assert "bias proven" not in report.lower()
    assert (analysis_dir / "detention_cross_prompt_comparisons.csv").exists()
    assert (analysis_dir / "detention_full_metric_summary.json").exists()


def test_vercel_export_gemini_full_scaffold(tmp_path: Path) -> None:
    from benchassist.detention_full_analysis import run_full_analysis
    from benchassist.detention_mock_runner import generate_mock_memo
    from benchassist.detention_gemini_config import load_detention_gemini_config, select_pilot_rows
    from benchassist.vercel_export import export_vercel_data

    cfg = load_detention_gemini_config(PILOT_CONFIG)
    run_dir = tmp_path / "gemini_full_run"
    outputs = run_dir / "parsed_outputs.jsonl"
    run_dir.mkdir(parents=True)
    rows = select_pilot_rows(cfg)[:6]
    with open(outputs, "w", encoding="utf-8") as fh:
        for row in rows:
            out = generate_mock_memo(row, prompt_mode="baseline")
            fh.write(json.dumps(out, ensure_ascii=False) + "\n")
    run_full_analysis(outputs, output_dir=run_dir / "analysis")

    out_dir = tmp_path / "dashboard"
    manifest = export_vercel_data(
        output_dir=out_dir,
        use_case="detention",
        run_dir=run_dir,
        data_status="gemini_full",
    )
    assert manifest.get("data_status") == "gemini_full"
    assert (out_dir / "detention_full_metric_summary.json").exists()
    assert (out_dir / "detention_cross_prompt_comparisons.json").exists()


def test_verify_pilot_qa_on_real_artifacts() -> None:
    from benchassist.detention_gemini_config import verify_pilot_qa_passed

    result = verify_pilot_qa_passed(ROOT)
    assert result["passed"] is True
    assert result["n_parsed_rows"] >= 11
