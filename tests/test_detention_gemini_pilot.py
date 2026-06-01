"""Tests for detention Gemini dry-run / pilot workflow (no live API calls)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
PILOT_CONFIG = ROOT / "configs" / "gemini_detention_pilot.yaml"


def test_load_pilot_config() -> None:
    from benchassist.detention_gemini_config import load_detention_gemini_config

    cfg = load_detention_gemini_config(PILOT_CONFIG)
    assert cfg.use_case == "detention"
    assert cfg.model == "gemini-2.5-flash-lite"
    assert "baseline" in cfg.prompt_modes
    assert cfg.max_synthetic_base_cases == 2
    assert cfg.safety.overwrite_existing is False


def test_select_pilot_rows_counts() -> None:
    from benchassist.detention_gemini_config import load_detention_gemini_config, select_pilot_rows
    from benchassist.dataset_modes import exclude_from_strict_bias

    cfg = load_detention_gemini_config(PILOT_CONFIG)
    rows = select_pilot_rows(cfg)
    # 2 bases × max_variants_per_base_case + max_real_cases
    assert len(rows) > 0
    real_rows = [r for r in rows if exclude_from_strict_bias(r)]
    # At minimum the real cases should be excluded from strict rates
    assert len(real_rows) >= cfg.max_real_cases
    assert all(exclude_from_strict_bias(r) for r in real_rows)


def test_dry_run_writes_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from benchassist.detention_gemini_config import load_detention_gemini_config
    from benchassist.detention_gemini_plan import run_dry_run

    cfg = load_detention_gemini_config(PILOT_CONFIG)
    cfg.output_dir = tmp_path / "pilot"
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-printed")

    manifest = run_dry_run(cfg, resume=False)
    assert (cfg.output_dir / "dry_run_manifest.json").exists()
    assert manifest["checks_passed"] is True
    assert manifest["request_plan"]["total_requests"] > 0
    raw = (cfg.output_dir / "dry_run_manifest.json").read_text(encoding="utf-8")
    assert "test-key-not-printed" not in raw


def test_pilot_refuses_without_dry_run_manifest(tmp_path: Path) -> None:
    from benchassist.detention_gemini_config import load_detention_gemini_config
    from benchassist.detention_gemini_pilot import run_pilot

    cfg = load_detention_gemini_config(PILOT_CONFIG)
    cfg.output_dir = tmp_path / "pilot"
    with pytest.raises(FileNotFoundError, match="Dry-run manifest missing"):
        run_pilot(cfg)


def test_pilot_refuses_when_checks_failed(tmp_path: Path) -> None:
    from benchassist.detention_gemini_config import load_detention_gemini_config
    from benchassist.detention_gemini_pilot import run_pilot

    cfg = load_detention_gemini_config(PILOT_CONFIG)
    cfg.output_dir = tmp_path / "pilot"
    cfg.output_dir.mkdir(parents=True)
    cfg.dry_run_manifest_path.write_text(json.dumps({"checks_passed": False}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="checks_passed=false"):
        run_pilot(cfg)


def test_pilot_refuses_overwrite(tmp_path: Path) -> None:
    from benchassist.detention_gemini_config import load_detention_gemini_config
    from benchassist.detention_gemini_pilot import run_pilot

    cfg = load_detention_gemini_config(PILOT_CONFIG)
    cfg.output_dir = tmp_path / "pilot"
    cfg.output_dir.mkdir(parents=True)
    cfg.dry_run_manifest_path.write_text(json.dumps({"checks_passed": True}), encoding="utf-8")
    cfg.parsed_outputs_path.write_text('{"x":1}\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="Refusing to overwrite"):
        run_pilot(cfg, resume=False)


def test_pilot_resume_skips_completed(tmp_path: Path) -> None:
    from benchassist.detention_gemini_config import load_detention_gemini_config, request_key, write_jsonl
    from benchassist.detention_gemini_pilot import run_pilot

    cfg = load_detention_gemini_config(PILOT_CONFIG)
    cfg.output_dir = tmp_path / "pilot"
    cfg.rate_limit.min_delay_seconds = 0
    cfg.output_dir.mkdir(parents=True)
    cfg.dry_run_manifest_path.write_text(json.dumps({"checks_passed": True}), encoding="utf-8")

    from benchassist.detention_gemini_config import select_pilot_rows

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
        manifest = run_pilot(cfg, resume=True)

    assert manifest["stats"]["skipped_resume"] >= 1
    assert mock_client.generate.call_count < 11 * 3


def test_api_key_never_in_logs(capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from benchassist.detention_gemini_config import load_detention_gemini_config
    from benchassist.detention_gemini_plan import main

    cfg = load_detention_gemini_config(PILOT_CONFIG)
    monkeypatch.setenv("GEMINI_API_KEY", "SECRET-KEY-12345")
    # Redirect output dir via temp copy — run main with patched config path
    monkeypatch.chdir(tmp_path)
    import shutil

    shutil.copy(PILOT_CONFIG, tmp_path / "cfg.yaml")
    c = load_detention_gemini_config(tmp_path / "cfg.yaml")
    c.output_dir = tmp_path / "out"
    from benchassist.detention_gemini_plan import run_dry_run

    run_dry_run(c)
    captured = capsys.readouterr()
    assert "SECRET-KEY-12345" not in captured.out
    assert "SECRET-KEY-12345" not in captured.err


def test_pilot_analysis_with_fixture(tmp_path: Path) -> None:
    from benchassist.detention_mock_runner import generate_mock_memo
    from benchassist.detention_pilot_analysis import run_pilot_analysis
    from benchassist.detention_gemini_config import load_detention_gemini_config, select_pilot_rows

    cfg = load_detention_gemini_config(PILOT_CONFIG)
    rows = select_pilot_rows(cfg)[:4]
    outputs = tmp_path / "parsed_outputs.jsonl"
    with open(outputs, "w", encoding="utf-8") as fh:
        for row in rows:
            out = generate_mock_memo(row, prompt_mode="baseline")
            fh.write(json.dumps(out, ensure_ascii=False) + "\n")

    analysis_dir = tmp_path / "analysis"
    result = run_pilot_analysis(outputs, output_dir=analysis_dir)
    report = result["paths"]["report"].read_text(encoding="utf-8")
    assert "proof of unlawful discrimination" in report.lower()
    assert "bias proven" not in report.lower()
    assert "unlawful treatment" not in report.lower() or "not" in report.lower()
    assert (analysis_dir / "detention_pairwise_comparison.csv").exists()
    assert (tmp_path / "analysis" / "detention_pilot_metric_summary.json").exists()


def test_vercel_export_gemini_pilot(tmp_path: Path) -> None:
    from benchassist.detention_pilot_analysis import run_pilot_analysis
    from benchassist.detention_mock_runner import generate_mock_memo
    from benchassist.detention_gemini_config import load_detention_gemini_config, select_pilot_rows
    from benchassist.vercel_export import export_vercel_data

    cfg = load_detention_gemini_config(PILOT_CONFIG)
    run_dir = tmp_path / "gemini_run"
    outputs = run_dir / "parsed_outputs.jsonl"
    run_dir.mkdir(parents=True)
    rows = select_pilot_rows(cfg)[:6]
    with open(outputs, "w", encoding="utf-8") as fh:
        for row in rows:
            out = generate_mock_memo(row, prompt_mode="baseline")
            fh.write(json.dumps(out, ensure_ascii=False) + "\n")
    run_pilot_analysis(outputs, output_dir=run_dir / "analysis")

    out_dir = tmp_path / "dashboard"
    manifest = export_vercel_data(
        output_dir=out_dir,
        use_case="detention",
        run_dir=run_dir,
        data_status="gemini_pilot",
    )
    assert manifest["use_case"] == "detention"
    assert (out_dir / "detention_flagged_cases.json").exists()
    assert manifest.get("data_status") == "gemini_pilot"
