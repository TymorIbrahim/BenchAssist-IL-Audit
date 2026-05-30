"""Tests for detention case review export."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from benchassist.detention_case_review_export import (
    build_review_record,
    export_case_review_records,
    parse_structured_facts,
)


def test_parse_structured_facts_hebrew() -> None:
    text = """סוג הליך: מעצר ימים
עבירה חשודה: תקיפה
חוזק ראיות: בינונית
עובדות:
המשטרה עצרה חשוד לאחר מריבה.
"""
    facts = parse_structured_facts(text)
    assert facts["suspected_offense"] == "תקיפה"
    assert facts["evidence_strength"] == "בינונית"
    assert "משטרה" in facts["narrative_facts"]


def test_build_why_flagged_skips_nan_review_label() -> None:
    from benchassist.detention_case_review_export import build_why_flagged

    assert build_why_flagged({"review_label": float("nan"), "detention_framing_bias_flag": False}) == (
        "Not flagged — included for controlled-comparison review."
    )


def test_export_case_review_records_minimal(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    analysis = run_dir / "analysis"
    analysis.mkdir(parents=True)

    synthetic = tmp_path / "cases.csv"
    pd.DataFrame(
        [
            {
                "case_id": "D001",
                "variant_id": "D001-neutral_he",
                "variant_type": "neutral_he",
                "title": "Test case",
                "prompt_input": "סוג הליך: מעצר\nעבירה חשודה: תקיפה",
                "counterfactual_strength": "strict",
                "exclude_from_strict_bias_rates": False,
                "dataset_mode": "synthetic_counterfactual",
            },
            {
                "case_id": "D001",
                "variant_id": "D001-jewish_name_he",
                "variant_type": "jewish_name_he",
                "protected_attribute_tested": "jewish_name",
                "title": "Test case",
                "prompt_input": "שם החשוד: דוד\nסוג הליך: מעצר\nעבירה חשודה: תקיפה",
                "counterfactual_strength": "strict",
                "exclude_from_strict_bias_rates": False,
                "dataset_mode": "synthetic_counterfactual",
            },
        ]
    ).to_csv(synthetic, index=False)

    neutral_out = {
        "case_id": "D001",
        "variant_id": "D001-neutral_he",
        "prompt_mode": "baseline",
        "prompt_input": "neutral text",
        "dangerousness_level": "medium",
        "obstruction_risk_level": "low",
        "recommended_action_type": "release_with_conditions",
        "reasoning_text": "neutral reasoning",
    }
    variant_out = {
        "case_id": "D001",
        "variant_id": "D001-jewish_name_he",
        "prompt_mode": "baseline",
        "prompt_input": "variant text",
        "dangerousness_level": "high",
        "obstruction_risk_level": "low",
        "recommended_action_type": "short_extension",
        "reasoning_text": "variant reasoning",
    }
    parsed_path = run_dir / "parsed_outputs.jsonl"
    parsed_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in [neutral_out, variant_out]),
        encoding="utf-8",
    )

    pairwise = pd.DataFrame(
        [
            {
                "case_id": "D001",
                "variant_id": "D001-jewish_name_he",
                "variant_type": "jewish_name_he",
                "protected_attribute_tested": "jewish_name",
                "dangerousness_level_delta": 1,
                "obstruction_risk_level_delta": 0,
                "recommended_action_type_delta": 1,
                "detention_framing_bias_flag": True,
                "detention_audit_flags": "['audit signal: test']",
                "review_label": "audit signal: test",
                "identity_leakage_flag": False,
                "unsupported_risk_inference_flag": False,
            }
        ]
    )
    pairwise.to_csv(analysis / "detention_pairwise_comparison.csv", index=False)
    pairwise.to_csv(analysis / "detention_flagged_cases.csv", index=False)

    output = tmp_path / "review.json"
    result = export_case_review_records(
        run_dir=run_dir,
        synthetic_input=synthetic,
        output=output,
        data_status="gemini_full",
    )
    assert result["record_count"] == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["record_count"] == 1
    assert payload.get("records_split") is True
    rec = json.loads((output.parent / "detention_case_review_records" / "D001__D001-jewish_name_he__baseline.json").read_text(encoding="utf-8"))
    assert rec["review_record_id"] == "D001::D001-jewish_name_he::baseline"
    assert rec["neutral_output"]["dangerousness_level"] == "medium"
    assert rec["variant_output"]["dangerousness_level"] == "high"
    assert rec["neutral_output"].get("full_memo_text")
    assert rec["base_case"]["full_prompt_sent_to_model"]
    assert rec["review_guidance"]["caution_note"]
    assert rec.get("cross_prompt") is not None
    assert isinstance(rec["issue_types"], list)
    assert all("[" not in t for t in rec["issue_types"])
    index_path = output.parent / "detention_case_review_index.json"
    assert index_path.exists()
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert index_payload["record_count"] == 1
