"""Tests for detention mock/local QA pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_INPUT = ROOT / "data" / "synthetic" / "detention_core_cases.csv"
MIXED_FIXTURE = ROOT / "tests" / "fixtures" / "detention_mixed_strict_filter.jsonl"


@pytest.fixture(scope="module")
def ensure_synthetic_data() -> Path:
    from benchassist.detention_data_generation import write_detention_audit_files

    paths = write_detention_audit_files()
    return paths["core_csv"]


def test_detention_mock_runner(ensure_synthetic_data: Path, tmp_path: Path) -> None:
    from benchassist.detention_mock_runner import run_mock_batch

    out = tmp_path / "mock.jsonl"
    n_expected = len(pd.read_csv(ensure_synthetic_data))
    result = run_mock_batch(ensure_synthetic_data, out, prompt_mode="baseline")
    assert result["n_outputs"] == n_expected
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert all(r["use_case"] == "detention" for r in rows)
    assert all(r["parse_status"] == "success" for r in rows)


def test_detention_mock_runner_minimal_schema(ensure_synthetic_data: Path, tmp_path: Path) -> None:
    from benchassist.detention_mock_runner import run_mock_batch
    from benchassist.detention_schema import SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2

    out = tmp_path / "mock_minimal.jsonl"
    n_expected = len(pd.read_csv(ensure_synthetic_data))
    result = run_mock_batch(
        ensure_synthetic_data,
        out,
        prompt_mode="baseline",
        schema_version=SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2,
    )
    assert result["n_outputs"] == n_expected
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert all(r["schema_version"] == SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2 for r in rows)
    assert all("recommended_action_type" not in r or r.get("recommended_action_type") is None for r in rows)
    assert all(r.get("dangerousness_level") for r in rows)


def test_schema_validation(ensure_synthetic_data: Path, tmp_path: Path) -> None:
    from benchassist.detention_mock_runner import run_mock_batch
    from benchassist.detention_schema import validate_detention_outputs_file

    out = tmp_path / "mock.jsonl"
    n_expected = len(pd.read_csv(ensure_synthetic_data))
    run_mock_batch(ensure_synthetic_data, out, prompt_mode="baseline")
    result = validate_detention_outputs_file(out)
    assert result["passed"]
    assert result["n_valid"] == n_expected


def test_detention_analysis_metrics(ensure_synthetic_data: Path, tmp_path: Path) -> None:
    from benchassist.detention_mock_runner import run_mock_batch
    from benchassist.detention_analysis import run_detention_analysis

    mock_out = tmp_path / "mock.jsonl"
    run_mock_batch(ensure_synthetic_data, mock_out, prompt_mode="baseline")
    analysis_dir = tmp_path / "analysis"
    result = run_detention_analysis(mock_out, output_dir=analysis_dir, strict_only=True)
    assert (analysis_dir / "detention_pairwise_comparison.csv").exists()
    assert (analysis_dir / "detention_analysis_report.md").exists()
    report = (analysis_dir / "detention_analysis_report.md").read_text(encoding="utf-8")
    assert "proof of unlawful discrimination" in report.lower()
    assert "bias proven" not in report.lower()
    pairwise = result["pairwise"]
    assert len(pairwise) > 0
    assert "dangerousness_level_delta" in pairwise.columns


def test_strict_filter_mixed_fixture() -> None:
    from benchassist.dataset_modes import exclude_from_strict_bias
    from benchassist.detention_metrics import filter_detention_strict_eligible

    rows = []
    for line in MIXED_FIXTURE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    filtered = filter_detention_strict_eligible(df)
    assert len(filtered) == 2
    assert set(filtered["variant_type"]) == {"neutral_he", "arab_name_he"}
    for _, row in df.iterrows():
        d = row.to_dict()
        if d["dataset_mode"] == "real_case_inspired":
            assert exclude_from_strict_bias(d)
        if d["variant_type"] in {"skeptical_police_framing", "low_income_neighborhood_proxy"}:
            assert exclude_from_strict_bias(d)


def test_real_case_qa(tmp_path: Path) -> None:
    from benchassist.detention_real_case_qa import run_real_case_qa

    pilot = ROOT / "data" / "real_cases" / "detention" / "pilot_corpus"
    if not pilot.exists():
        pytest.skip("pilot corpus missing")
    out = tmp_path / "real_case_qa.md"
    result = run_real_case_qa(pilot, out)
    assert result["n_rows"] > 0
    assert result["checks"]
    text = out.read_text(encoding="utf-8")
    assert "Real-case-inspired" in text


def test_vercel_export_mock_mode(tmp_path: Path) -> None:
    from benchassist.vercel_export import export_vercel_data

    manifest = export_vercel_data(output_dir=tmp_path, use_case="detention", mock_mode=True)
    assert manifest.get("use_case") == "detention"
    assert (tmp_path / "data_access_policy.json").exists()
    assert (tmp_path / "detention_overview_metrics.json").exists()


def test_synthetic_qa_report_generated() -> None:
    qa_md = ROOT / "results" / "report" / "detention_synthetic_data_qa.md"
    if not qa_md.exists():
        from benchassist.detention_data_generation import write_detention_audit_files

        write_detention_audit_files()
    assert qa_md.exists()
    text = qa_md.read_text(encoding="utf-8")
    assert "neutral_he" in text or "Base cases" in text
