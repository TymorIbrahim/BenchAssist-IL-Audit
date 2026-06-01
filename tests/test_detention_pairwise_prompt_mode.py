"""Tests that detention pairwise comparisons stay within prompt_mode."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from benchassist.detention_metrics import compute_detention_pairwise_comparisons
from benchassist.detention_mock_runner import generate_mock_memo


def test_pairwise_groups_by_prompt_mode() -> None:
    row_base = {
        "case_id": "D001",
        "base_case_id": "D001",
        "variant_type": "neutral_he",
        "variant_id": "D001-neutral_he",
        "use_case": "detention",
        "dataset_mode": "synthetic_counterfactual",
        "use_for_strict_bias_rates": True,
    }
    row_variant = {
        **row_base,
        "case_id": "D001",
        "variant_type": "jewish_name_he",
        "variant_id": "D001-jewish_name_he",
        "protected_attribute_tested": "jewish_name",
    }
    rows: list[dict] = []
    for mode in ("baseline", "fairness_aware", "demographic_blind"):
        rows.append(generate_mock_memo({**row_base, "variant_type": "neutral_he", "variant_id": "D001-neutral_he"}, prompt_mode=mode))  # type: ignore[arg-type]
        rows.append(generate_mock_memo(row_variant, prompt_mode=mode))  # type: ignore[arg-type]

    df = pd.DataFrame(rows)
    pairwise = compute_detention_pairwise_comparisons(df)
    assert len(pairwise) == 3
    assert set(pairwise["prompt_mode"]) == {"baseline", "fairness_aware", "demographic_blind"}
    assert "prompt_mode" in pairwise.columns
