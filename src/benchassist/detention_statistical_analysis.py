"""Statistical uncertainty analysis for detention audit metrics."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

CAUTION_DEFAULT = (
    "Exploratory screening; Benjamini–Hochberg FDR applied across variant groups; "
    "small samples possible; requires qualitative legal review."
)


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return float("nan"), float("nan")
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    margin = z * math.sqrt((p * (1.0 - p) / n) + (z2 / (4.0 * n * n))) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    """Return adjusted p-values (FDR)."""
    m = len(p_values)
    if m == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [1.0] * m
    prev = 1.0
    for rank, (idx, p) in enumerate(reversed(indexed), start=1):
        q = min(prev, p * m / (m - rank + 1))
        prev = q
        adjusted[idx] = q
    return adjusted


def _coerce_bool(value: Any) -> bool:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def compute_detention_group_statistics(
    group_df: pd.DataFrame,
    pairwise_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Wilson CIs, effect sizes, and FDR-adjusted screening for detention variant groups."""
    rows: list[dict[str, Any]] = []
    if group_df.empty:
        return pd.DataFrame(rows)

    raw_p_values: list[float] = []
    for _, row in group_df.iterrows():
        variant = row.get("variant_type") or row.get("variant_category")
        n = int(row.get("n_comparisons") or row.get("n_pairs") or 0)
        flagged_rate = float(
            row.get("flagged_rate")
            or row.get("detention_framing_bias_flag_rate")
            or row.get("flag_rate")
            or 0
        )
        n_flagged = int(round(flagged_rate * n)) if n else 0
        ci_low, ci_high = wilson_interval(n_flagged, n)
        mean_danger = row.get("mean_dangerousness_level_delta") or row.get("mean_dangerousness_shift")
        mean_action = row.get("mean_recommended_action_type_delta") or row.get("mean_action_shift")
        mean_duration = row.get("mean_recommended_duration_days_delta")

        # One-sided binomial p-value vs null rate 0.5 for exploratory flag rate elevation
        p_val = 1.0
        if n > 0:
            # simple normal approx
            p0 = 0.5
            se = math.sqrt(p0 * (1 - p0) / n)
            if se > 0:
                z_score = (flagged_rate - p0) / se
                p_val = 0.5 * (1 - math.erf(z_score / math.sqrt(2)))

        raw_p_values.append(min(max(p_val, 0.0), 1.0))
        prompt_mode = row.get("prompt_mode", "baseline")
        rows.append(
            {
                "variant_type": variant,
                "prompt_mode": prompt_mode,
                "n_comparisons": n,
                "n_flagged": n_flagged,
                "flagged_rate": round(flagged_rate, 4),
                "flagged_rate_ci_low": round(ci_low, 4) if not math.isnan(ci_low) else None,
                "flagged_rate_ci_high": round(ci_high, 4) if not math.isnan(ci_high) else None,
                "mean_dangerousness_shift": mean_danger,
                "mean_action_shift": mean_action,
                "mean_duration_shift": mean_duration,
                "metric": "detention_framing_bias_flag_rate",
                "exploratory_p_value": round(p_val, 6),
                "sample_size_note": (
                    f"n={n} comparisons for {variant}; interpret cautiously when n<12."
                ),
                "interpretation": CAUTION_DEFAULT,
            }
        )

    if rows and "prompt_mode" in rows[0] and len({str(r.get("prompt_mode") or "baseline") for r in rows}) > 1:
        for mode in sorted({str(r.get("prompt_mode") or "baseline") for r in rows}):
            indices = [i for i, r in enumerate(rows) if str(r.get("prompt_mode") or "baseline") == mode]
            mode_fdr = benjamini_hochberg([raw_p_values[i] for i in indices])
            for j, idx in enumerate(indices):
                rows[idx]["fdr_adjusted_p_value"] = round(mode_fdr[j], 6)
                rows[idx]["fdr_significant_at_0_10"] = mode_fdr[j] <= 0.10
    else:
        fdr = benjamini_hochberg(raw_p_values)
        for i, q in enumerate(fdr):
            rows[i]["fdr_adjusted_p_value"] = round(q, 6)
            rows[i]["fdr_significant_at_0_10"] = q <= 0.10

    if pairwise_df is not None and not pairwise_df.empty and "validity_category" in pairwise_df.columns:
        for i, row in enumerate(rows):
            vt = row["variant_type"]
            sub = pairwise_df[pairwise_df["variant_type"] == vt]
            if "prompt_mode" in row and "prompt_mode" in sub.columns:
                sub = sub[sub["prompt_mode"] == row["prompt_mode"]]
            valid = sub[~sub["exclude_from_strict_bias_rates"].apply(_coerce_bool)] if "exclude_from_strict_bias_rates" in sub.columns else sub
            rows[i]["n_validity_eligible"] = len(valid)
            rows[i]["n_validity_excluded"] = len(sub) - len(valid)

    return pd.DataFrame(rows)


def compute_detention_overview_uncertainty(pairwise_df: pd.DataFrame) -> dict[str, Any]:
    if pairwise_df.empty:
        return {}
    n = len(pairwise_df)
    flagged_col = "detention_framing_bias_flag"
    if flagged_col not in pairwise_df.columns:
        return {"n_comparisons": n}
    n_flagged = int(pairwise_df[flagged_col].apply(_coerce_bool).sum())
    rate = n_flagged / n if n else 0
    ci_low, ci_high = wilson_interval(n_flagged, n)
    return {
        "n_comparisons": n,
        "n_flagged": n_flagged,
        "flagged_rate": round(rate, 4),
        "flagged_rate_ci_low": round(ci_low, 4),
        "flagged_rate_ci_high": round(ci_high, 4),
        "uncertainty_note": f"95% Wilson CI on flagged rate; n={n} pairwise comparisons.",
    }


def compute_power_notes(n_base_cases: int, variants_per_case: int) -> dict[str, Any]:
    total = n_base_cases * variants_per_case
    return {
        "n_base_cases": n_base_cases,
        "variants_per_base_case": variants_per_case,
        "n_total_variant_rows": total,
        "power_note": (
            f"With {n_base_cases} base cases and ~{variants_per_case} variants, subgroup rates "
            f"below n≈12 per variant type have wide confidence intervals."
        ),
    }
