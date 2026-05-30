"""Tests for validate_data, stereotype_audit, qualitative_cases, and pipeline status."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from benchassist.config import get_settings
from benchassist.data_generation import create_base_cases, create_counterfactual_cases
from benchassist.pipeline import pipeline_status, print_real_run_plan
from benchassist.qualitative_cases import extract_qualitative_cases, run_qualitative_cases
from benchassist.stereotype_audit import audit_output_row, run_stereotype_audit
from benchassist.validate_data import validate_audit_files, validate_counterfactual_df


def test_validate_counterfactual_no_party_power() -> None:
    variants = create_counterfactual_cases(create_base_cases(), variant_set="demographic")
    df = pd.DataFrame([v.model_dump() for v in variants])
    errors = validate_counterfactual_df(df)
    assert not any("party_power" in e for e in errors)


def test_stereotype_audit_empty_text_ok() -> None:
    row = pd.Series(
        {
            "case_id": "c1",
            "variant_id": "c1-neutral_he",
            "variant_type": "neutral_he",
            "input_text": "דייר מדווח על עובש.",
            "reasoning_text": "יש לבקש ראיות נוספות.",
        }
    )
    result = audit_output_row(row)
    assert "stereotype_audit_flag" in result


def test_qualitative_extract_from_pairwise() -> None:
    pairwise = pd.DataFrame(
        [
            {
                "case_id": "IL-001",
                "variant_id": "IL-001-broken_hebrew",
                "variant_type": "broken_hebrew",
                "demographic_cue": "broken Hebrew",
                "legal_framing_bias_flag": True,
                "action_type_flip": False,
                "remedy_weaker": True,
                "credibility_more_skeptical": False,
                "evidence_burden_higher": False,
            }
        ]
    )
    outputs = pd.DataFrame(
        [
            {
                "case_id": "IL-001",
                "variant_id": "IL-001-neutral_he",
                "variant_type": "neutral_he",
                "input_text": "neutral",
                "reasoning_text": "n",
            },
            {
                "case_id": "IL-001",
                "variant_id": "IL-001-broken_hebrew",
                "variant_type": "broken_hebrew",
                "input_text": "variant",
                "reasoning_text": "v",
            },
        ]
    )
    cases = extract_qualitative_cases(
        outputs_df=outputs, pairwise_df=pairwise, flagged_df=None, top_n=3
    )
    assert len(cases) == 1
    assert "human legal review" in cases.iloc[0]["generated_interpretation"].lower()


def test_pipeline_status_and_plan(capsys) -> None:
    status = pipeline_status()
    for key in (
        "PROJECT_OVERVIEW.md",
        "DATA_DICTIONARY.md",
        "LEGAL_EXPERT_RUNBOOK.md",
        "SUBMISSION_PACKAGE.md",
        "submission_package/",
        "submission_package.zip",
    ):
        assert key in status["checks"]
    assert "checks" in status
    print_real_run_plan()
    captured = capsys.readouterr()
    assert "gemini" in captured.out.lower()
    assert "fairness_aware" in captured.out
    assert "submission_package" in captured.out


def test_run_stereotype_audit_writes_files(tmp_path, monkeypatch) -> None:
    results = tmp_path / "results"
    (results / "tables").mkdir(parents=True)
    (results / "report").mkdir(parents=True)
    monkeypatch.setenv("RESULTS_DIR", str(results))
    get_settings.cache_clear()

    outputs = tmp_path / "out.csv"
    pd.DataFrame(
        [
            {
                "case_id": "c1",
                "variant_id": "c1-neutral_he",
                "variant_type": "neutral_he",
                "demographic_cue": "none",
                "input_text": "עובש בדירה",
                "reasoning_text": "לבקש ראיות",
            }
        ]
    ).to_csv(outputs, index=False)

    result = run_stereotype_audit(outputs, output_suffix="qa_test")
    assert result["paths"]["report"].exists()


def test_validate_audit_files_on_synthetic(tmp_path, monkeypatch) -> None:
    data = tmp_path / "data"
    processed = data / "processed"
    audit = data / "audit"
    processed.mkdir(parents=True)
    audit.mkdir(parents=True)
    monkeypatch.setenv("DATA_DIR", str(data))
    get_settings.cache_clear()

    base = create_base_cases()
    variants = create_counterfactual_cases(base, variant_set="narrative_framing")
    pd.DataFrame([b.model_dump() for b in base]).to_csv(processed / "base_cases.csv", index=False)
    pd.DataFrame([v.model_dump() for v in variants]).to_csv(
        audit / "counterfactual_cases.csv", index=False
    )

    summary = validate_audit_files(variant_set="narrative_framing")
    assert not summary["errors"]
