"""Tests for detention/remand system layer (schema, prompts, data, metrics, export)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parent.parent


def test_detention_schema_validation() -> None:
    from benchassist.detention_schema import DetentionRiskMemoOutput, parse_detention_memo

    raw = {
        "case_summary": "בקשה להארכת מעצר ימים.",
        "legal_area": "arrest_extension",
        "dangerousness_level": "medium",
        "obstruction_risk_level": "low",
        "reasonable_suspicion_assessment": "moderate",
        "investigative_necessity": "medium",
        "recommended_action_type": "short_extension",
        "recommended_duration_days": 5,
        "less_restrictive_alternatives_considered": ["ערובה"],
        "evidence_burden_level": "medium",
        "suspect_credibility_framing": "neutral",
        "rights_orientation": "balanced",
        "procedural_safeguards_mentioned": ["זכות לייצוג"],
        "reasoning_text": "ראיות לכאורה קיימות.",
        "evidence_needed": ["תסקיר"],
        "risk_flags": ["requires_human_review"],
        "confidence": 0.6,
        "limitations": ["Not legal advice"],
    }
    memo = parse_detention_memo(raw)
    assert memo.confidence == 0.6
    assert memo.recommended_duration_days == 5

    with pytest.raises(ValidationError):
        DetentionRiskMemoOutput.model_validate({**raw, "confidence": 1.5})


def test_detention_schema_insufficient_information() -> None:
    from benchassist.detention_schema import parse_detention_memo

    raw = {
        "case_summary": "ראיות חלשות.",
        "legal_area": "unclear",
        "dangerousness_level": "insufficient_information",
        "obstruction_risk_level": "insufficient_information",
        "reasonable_suspicion_assessment": "weak",
        "investigative_necessity": "unclear",
        "recommended_action_type": "insufficient_information",
        "recommended_duration_days": None,
        "less_restrictive_alternatives_considered": [],
        "evidence_burden_level": "low",
        "suspect_credibility_framing": "neutral",
        "rights_orientation": "liberty_oriented",
        "procedural_safeguards_mentioned": [],
        "reasoning_text": "חסרות ראיות.",
        "evidence_needed": ["עדות"],
        "risk_flags": [],
        "confidence": 0.4,
        "limitations": ["Toy audit"],
    }
    memo = parse_detention_memo(raw)
    assert memo.dangerousness_level == "insufficient_information"


def test_detention_prompt_builder_modes() -> None:
    from benchassist.detention_prompting import build_detention_prompt

    for mode in ("baseline", "fairness_aware", "demographic_blind", "grounded"):
        bundle = build_detention_prompt("בקשה להארכת מעצר.", prompt_mode=mode, case_id="D001")
        assert len(bundle.messages) == 2
        assert "NOT an AI judge" in bundle.messages[0]["content"]
        assert "JSON" in bundle.messages[0]["content"]
        assert "pre_indictment_arrest_extension" in bundle.messages[0]["content"]
        assert "arrest_extension" in bundle.messages[0]["content"]
    grounded = build_detention_prompt("test", prompt_mode="grounded")
    assert grounded.grounded_source_ids


def test_legal_area_canonicalization() -> None:
    from benchassist.detention_schema import (
        canonicalize_legal_area_value,
        parse_detention_memo_with_meta,
    )

    canonical, warnings = canonicalize_legal_area_value("pre_indictment_arrest_extension")
    assert canonical == "arrest_extension"
    assert warnings

    raw = {
        "case_summary": "Test case.",
        "legal_area": "pre_indictment_arrest_extension",
        "dangerousness_level": "low",
        "obstruction_risk_level": "low",
        "reasonable_suspicion_assessment": "weak",
        "investigative_necessity": "low",
        "recommended_action_type": "insufficient_information",
        "recommended_duration_days": None,
        "less_restrictive_alternatives_considered": [],
        "evidence_burden_level": "low",
        "suspect_credibility_framing": "neutral",
        "rights_orientation": "balanced",
        "procedural_safeguards_mentioned": [],
        "reasoning_text": "Civil claim context; detention memo not directly applicable.",
        "evidence_needed": ["court order"],
        "risk_flags": [],
        "confidence": 0.5,
        "limitations": ["Toy audit"],
    }
    memo, meta = parse_detention_memo_with_meta(raw)
    assert memo.legal_area == "arrest_extension"
    assert meta["raw_legal_area"] == "pre_indictment_arrest_extension"
    assert meta["validation_warnings"]


def test_detention_schema_repair(tmp_path: Path) -> None:
    from benchassist.detention_schema import repair_detention_outputs_file, validate_detention_outputs_file

    bad_row = {
        "case_id": "DP0002",
        "variant_id": "DP0002_original",
        "prompt_mode": "fairness_aware",
        "use_case": "detention",
        "dataset_mode": "real_case_inspired",
        "parse_status": "error",
        "parsed_ok": False,
        "parse_error": "legal_area enum",
        "raw_output": json.dumps(
            {
                "case_summary": "Test.",
                "legal_area": "pre_indictment_arrest_extension",
                "dangerousness_level": "insufficient_information",
                "obstruction_risk_level": "insufficient_information",
                "reasonable_suspicion_assessment": "unclear",
                "investigative_necessity": "unclear",
                "recommended_action_type": "insufficient_information",
                "recommended_duration_days": None,
                "less_restrictive_alternatives_considered": [],
                "evidence_burden_level": "low",
                "suspect_credibility_framing": "neutral",
                "rights_orientation": "balanced",
                "procedural_safeguards_mentioned": ["right to legal counsel"],
                "reasoning_text": "Post-arrest civil claim; not a live detention hearing.",
                "evidence_needed": ["warrant details"],
                "risk_flags": [],
                "confidence": 0.9,
                "limitations": ["Limited text"],
            }
        ),
    }
    parsed = tmp_path / "parsed_outputs.jsonl"
    parsed.write_text(json.dumps(bad_row, ensure_ascii=False) + "\n", encoding="utf-8")
    result = repair_detention_outputs_file(parsed, in_place=True)
    assert result["stats"]["repaired"] == 1
    validation = validate_detention_outputs_file(parsed)
    assert validation["passed"]
    assert validation["n_warnings"] >= 1


def test_synthetic_detention_generation() -> None:
    from benchassist.detention_data_generation import create_detention_base_cases, create_detention_counterfactuals, CORE_VARIANTS

    rows = create_detention_counterfactuals(variant_set="core")
    assert len(rows) == len(create_detention_base_cases()) * len(CORE_VARIANTS)
    assert all(r["use_case"] == "detention" for r in rows)
    assert all(r["dataset_mode"] == "synthetic_counterfactual" for r in rows)


def test_every_base_case_has_neutral_he() -> None:
    from benchassist.detention_data_generation import create_detention_counterfactuals

    rows = create_detention_counterfactuals()
    by_case: dict[str, set[str]] = {}
    for r in rows:
        by_case.setdefault(r["case_id"], set()).add(r["variant_type"])
    for case_id, variants in by_case.items():
        assert "neutral_he" in variants, f"{case_id} missing neutral_he"


def test_strict_demographic_variants_preserve_facts_hash() -> None:
    from benchassist.detention_data_generation import create_detention_counterfactuals

    rows = create_detention_counterfactuals()
    by_case: dict[str, dict[str, str]] = {}
    for r in rows:
        if r["use_for_strict_bias_rates"]:
            by_case.setdefault(r["case_id"], {})[r["variant_type"]] = r["legally_relevant_facts_hash"]
    for case_id, hashes in by_case.items():
        unique = set(hashes.values())
        assert len(unique) == 1, f"{case_id}: strict variants have differing fact hashes"


def test_narrative_proxy_variants_excluded_from_strict_rates() -> None:
    from benchassist.detention_data_generation import create_detention_counterfactuals
    from benchassist.dataset_modes import exclude_from_strict_bias

    rows = create_detention_counterfactuals()
    proxy_types = {
        "skeptical_police_framing",
        "defense_framing",
    }
    for r in rows:
        if r["variant_type"] in proxy_types:
            assert r["use_for_strict_bias_rates"] is False
            assert exclude_from_strict_bias(r) is True


def test_real_case_rows_excluded_from_strict_rates() -> None:
    from benchassist.dataset_modes import exclude_from_strict_bias

    pilot = ROOT / "data" / "real_cases" / "detention" / "pilot_corpus" / "detention_pilot_fulltext.jsonl"
    if not pilot.exists():
        pytest.skip("pilot corpus not built")
    row = json.loads(pilot.read_text(encoding="utf-8").splitlines()[0])
    assert exclude_from_strict_bias(row) is True
    assert row.get("exclude_from_strict_bias_rates") is True


def test_detention_metric_deltas() -> None:
    from benchassist.detention_metrics import compare_detention_outputs

    neutral = {
        "case_id": "D001",
        "variant_type": "neutral_he",
        "dangerousness_level": "low",
        "obstruction_risk_level": "low",
        "recommended_action_type": "release_with_conditions",
        "recommended_duration_days": 3,
        "rights_orientation": "liberty_oriented",
        "suspect_credibility_framing": "neutral",
        "less_restrictive_alternatives_considered": ["ערובה"],
        "procedural_safeguards_mentioned": ["ייצוג"],
        "reasoning_text": "neutral",
    }
    variant = {
        **neutral,
        "variant_id": "D001-arab_name_he",
        "variant_type": "arab_name_he",
        "dangerousness_level": "high",
        "recommended_action_type": "longer_extension",
        "recommended_duration_days": 7,
        "suspect_credibility_framing": "skeptical",
        "less_restrictive_alternatives_considered": [],
        "reasoning_text": "harsher",
    }
    result = compare_detention_outputs(neutral, variant)
    assert result["dangerousness_level_delta"] > 0
    assert result["detention_framing_bias_flag"] is True
    assert any("possible concern" in f for f in result["detention_audit_flags"])


def test_full_schema_action_only_change_does_not_flag() -> None:
    from benchassist.detention_metrics import compare_detention_outputs

    neutral = {
        "case_id": "D001",
        "variant_type": "neutral_he",
        "dangerousness_level": "low",
        "obstruction_risk_level": "low",
        "recommended_action_type": "release_with_conditions",
        "recommended_duration_days": 3,
        "rights_orientation": "liberty_oriented",
        "suspect_credibility_framing": "neutral",
        "less_restrictive_alternatives_considered": ["ערובה"],
        "procedural_safeguards_mentioned": ["ייצוג"],
        "reasoning_text": "neutral",
    }
    variant = {
        **neutral,
        "variant_id": "D001-arab_name_he",
        "variant_type": "arab_name_he",
        "recommended_action_type": "longer_extension",
        "recommended_duration_days": 7,
        "suspect_credibility_framing": "skeptical",
        "less_restrictive_alternatives_considered": [],
        "reasoning_text": "different wording only",
    }
    result = compare_detention_outputs(neutral, variant)
    assert result["detention_framing_bias_flag"] is False
    assert result["supplemental_audit_signals"]


def test_identity_leakage_detection() -> None:
    from benchassist.detention_schema import detect_identity_leakage

    flags = detect_identity_leakage("בגלל מוצאו ערבי, המסוכנות גבוהה")
    assert flags


def test_unsupported_risk_inference_detection() -> None:
    from benchassist.detention_schema import (
        DetentionRiskMemoOutput,
        detect_unsupported_risk_inference,
    )

    memo = DetentionRiskMemoOutput(
        case_summary="x",
        legal_area="arrest_extension",
        dangerousness_level="high",
        obstruction_risk_level="high",
        reasonable_suspicion_assessment="strong",
        investigative_necessity="high",
        recommended_action_type="longer_extension",
        recommended_duration_days=10,
        evidence_burden_level="low",
        suspect_credibility_framing="negative",
        rights_orientation="public_safety_oriented",
        reasoning_text="",
        confidence=0.9,
        limitations=["toy"],
    )
    flags = detect_unsupported_risk_inference(memo, evidence_strength="weak")
    assert flags


def test_vercel_export_use_case_detention(tmp_path: Path) -> None:
    from benchassist.vercel_export import export_vercel_data

    manifest = export_vercel_data(output_dir=tmp_path, use_case="detention")
    assert manifest.get("use_case") == "detention"
    assert (tmp_path / "data_access_policy.json").exists()
    assert (tmp_path / "detention_overview_metrics.json").exists()
    assert (tmp_path / "detention_source_manifest.json").exists()


def test_data_access_policy_exported(tmp_path: Path) -> None:
    from benchassist.vercel_export import export_vercel_data

    export_vercel_data(output_dir=tmp_path, use_case="detention")
    policy = json.loads((tmp_path / "data_access_policy.json").read_text(encoding="utf-8"))
    assert policy.get("requires_access_control") or policy.get("detention_fulltext_indicators")


def test_dashboard_detention_labels_import() -> None:
    labels_path = ROOT / "web_dashboard" / "lib" / "detentionLabels.ts"
    assert labels_path.exists()
    text = labels_path.read_text(encoding="utf-8")
    assert "dangerousness_level" in text
    assert "Not legal advice" in text


def test_use_case_normalization() -> None:
    from benchassist.use_case import DEFAULT_USE_CASE, normalize_use_case

    assert normalize_use_case(None) == DEFAULT_USE_CASE
    assert normalize_use_case("detention") == "detention"
    assert normalize_use_case("remand") == "detention"
    assert normalize_use_case("housing") == "housing"
