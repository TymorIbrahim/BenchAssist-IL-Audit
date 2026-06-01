"""Tests for detention statistical analysis."""

from __future__ import annotations

import pandas as pd

from benchassist.detention_statistical_analysis import (
    benjamini_hochberg,
    compute_detention_group_statistics,
    compute_detention_overview_uncertainty,
    wilson_interval,
)


def test_wilson_interval_bounds():
    low, high = wilson_interval(8, 12)
    assert 0 <= low <= high <= 1


def test_benjamini_hochberg_monotonic():
    adjusted = benjamini_hochberg([0.01, 0.04, 0.03, 0.20])
    assert len(adjusted) == 4
    assert adjusted[0] <= adjusted[3]


def test_compute_group_statistics_includes_ci():
    group_df = pd.DataFrame(
        [
            {"variant_type": "arab_name_he", "n_comparisons": 12, "flagged_rate": 0.67},
            {"variant_type": "broken_hebrew", "n_comparisons": 12, "flagged_rate": 0.5},
        ]
    )
    stats = compute_detention_group_statistics(group_df)
    assert "flagged_rate_ci_low" in stats.columns
    assert "fdr_adjusted_p_value" in stats.columns


def test_overview_uncertainty():
    pairwise = pd.DataFrame({"detention_framing_bias_flag": [True, False, True, False, True, False]})
    out = compute_detention_overview_uncertainty(pairwise)
    assert out["n_comparisons"] == 6
    assert out["flagged_rate_ci_low"] is not None
