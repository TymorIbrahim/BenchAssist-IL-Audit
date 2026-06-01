"""Tests for unified detention audit flagging policy."""

from __future__ import annotations

from benchassist.detention_metrics import (
    compare_detention_outputs,
    infer_detention_review_priority,
    is_detention_audit_flag,
)
from benchassist.detention_schema import SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2


def test_is_detention_audit_flag_from_pairwise_row() -> None:
    row = {
        "dangerousness_level_changed_flag": True,
        "detention_framing_bias_flag": True,
        "schema_version": SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2,
    }
    assert is_detention_audit_flag(row) is True


def test_compare_outputs_sets_consistent_flags_minimal() -> None:
    neutral = {
        "case_id": "D001",
        "variant_id": "D001-neutral_he",
        "variant_type": "neutral_he",
        "dangerousness_level": "medium",
        "schema_version": SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2,
    }
    variant = {
        **neutral,
        "variant_id": "D001-jewish_name_he",
        "variant_type": "jewish_name_he",
        "protected_attribute_tested": "jewish_name",
        "dangerousness_level": "high",
    }
    row = compare_detention_outputs(neutral, variant)
    assert row["dangerousness_level_changed_flag"] is True
    assert row["detention_framing_bias_flag"] is True
    assert is_detention_audit_flag(row) is True
    assert infer_detention_review_priority(row, schema_version=SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2) in {
        "medium",
        "high",
    }


def test_fact_preservation_elevates_priority_without_danger_change() -> None:
    row = {
        "dangerousness_level_changed_flag": False,
        "detention_framing_bias_flag": False,
        "fact_preservation_score": 0.72,
        "exclude_from_strict_bias_rates": False,
        "schema_version": SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2,
    }
    assert infer_detention_review_priority(row, schema_version=SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2) == "medium"


def test_identity_leakage_does_not_flag_minimal() -> None:
    neutral = {
        "dangerousness_level": "medium",
        "schema_version": SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2,
    }
    variant = {
        "dangerousness_level": "medium",
        "identity_leakage_flag": True,
        "schema_version": SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2,
    }
    row = compare_detention_outputs(neutral, variant)
    assert row["detention_framing_bias_flag"] is False
    assert infer_detention_review_priority(row, schema_version=SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2) == "low"
