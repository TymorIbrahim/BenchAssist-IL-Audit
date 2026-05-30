"""Tests for detention pairwise deduplication."""

from __future__ import annotations

import pandas as pd

from benchassist.detention_metrics import _parse_list_field, dedupe_detention_pairwise_rows


def test_parse_list_field_python_style() -> None:
    raw = "['audit signal: procedural safeguards omitted vs neutral', 'flagged for legal review: identity']"
    parsed = _parse_list_field(raw)
    assert len(parsed) == 2
    assert "audit signal" in parsed[0]


def test_dedupe_pairwise_rows_merges_flags() -> None:
    df = pd.DataFrame(
        [
            {
                "case_id": "D001",
                "variant_id": "D001-jewish_name_he",
                "variant_type": "jewish_name_he",
                "detention_audit_flags": "['audit signal: procedural safeguards omitted vs neutral']",
                "detention_framing_bias_flag": True,
                "review_label": "audit signal: procedural safeguards omitted vs neutral",
                "dangerousness_level_delta": 0,
            },
            {
                "case_id": "D001",
                "variant_id": "D001-jewish_name_he",
                "variant_type": "jewish_name_he",
                "detention_audit_flags": "[]",
                "detention_framing_bias_flag": False,
                "review_label": None,
                "dangerousness_level_delta": 0,
            },
            {
                "case_id": "D001",
                "variant_id": "D001-jewish_name_he",
                "variant_type": "jewish_name_he",
                "detention_audit_flags": "['flagged for legal review: possible identity-based language in reasoning']",
                "detention_framing_bias_flag": True,
                "review_label": "flagged for legal review: possible identity-based language in reasoning",
                "dangerousness_level_delta": 0,
            },
        ]
    )
    deduped = dedupe_detention_pairwise_rows(df)
    assert len(deduped) == 1
    flags = _parse_list_field(deduped.iloc[0]["detention_audit_flags"])
    assert len(flags) == 2
    assert deduped.iloc[0]["detention_framing_bias_flag"] == True  # noqa: E712
