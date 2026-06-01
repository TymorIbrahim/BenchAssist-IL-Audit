"""Tests for detention run preflight (no API calls)."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MINIMAL_CONFIG = ROOT / "configs" / "gemini_detention_expanded_minimal_address.yaml"
CORPUS = ROOT / "data" / "synthetic" / "detention_core_cases_with_address.csv"


def test_validate_synthetic_corpus_passes() -> None:
    from benchassist.detention_corpus_preflight import validate_synthetic_corpus

    result = validate_synthetic_corpus(
        CORPUS,
        config_path=MINIMAL_CONFIG,
        require_address_proxy=True,
    )
    assert result["passed"] is True
    assert result["counts"]["row_count"] > 0
    assert result["counts"]["address_proxy_count"] > 0


def test_run_preflight_writes_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from benchassist.detention_gemini_config import load_detention_gemini_config
    from benchassist.detention_run_preflight import run_detention_preflight

    cfg = load_detention_gemini_config(MINIMAL_CONFIG)
    cfg.output_dir = tmp_path / "minimal_run"
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-printed")

    from benchassist import detention_run_preflight as preflight_mod

    original_load = preflight_mod.load_detention_gemini_config

    def _load(path: Path):
        c = original_load(path)
        c.output_dir = cfg.output_dir
        return c

    monkeypatch.setattr(preflight_mod, "load_detention_gemini_config", _load)

    report = tmp_path / "go_no_go.md"
    result = run_detention_preflight(MINIMAL_CONFIG, resume=False, report_path=report)
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "READY_FOR_MINIMAL_ADDRESS_GEMINI_RUN" in text
    assert "test-key-not-printed" not in text
    assert result["corpus"]["passed"] is True
    assert (cfg.output_dir / "dry_run_manifest.json").exists()
