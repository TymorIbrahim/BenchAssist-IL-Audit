"""Tests for detention run metadata helpers."""

from __future__ import annotations

import json
from pathlib import Path

from benchassist.detention_run_metadata import (
    detention_report_paths,
    detention_run_slug,
    infer_detention_run_label,
)


def test_detention_run_slug_expanded() -> None:
    assert detention_run_slug({"run_type": "expanded_full"}) == "detention_expanded_full"


def test_detention_report_paths_expanded(tmp_path: Path) -> None:
    paths = detention_report_paths(tmp_path, {"run_type": "expanded_full"})
    assert paths["qa_report"].name == "gemini_detention_expanded_full_qa_report.md"


def test_infer_detention_run_label(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(
        json.dumps({"run_type": "expanded_full", "model": "gemini-2.5-flash-lite"}),
        encoding="utf-8",
    )
    assert infer_detention_run_label(run_dir) == "detention_expanded_full_gemini-2_5-flash-lite"
