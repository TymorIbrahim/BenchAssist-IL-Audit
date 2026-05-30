"""Compare baseline vs mitigation V2 audit group summaries."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.config import get_settings

_COMPARISON_METRICS: tuple[tuple[str, str], ...] = (
    ("action_type_flip_rate", "action_type_flip_rate"),
    ("legal_framing_bias_flag_rate", "legal_framing_bias_flag_rate"),
    ("remedy_weaker_rate", "remedy_weaker_rate"),
    ("evidence_burden_higher_rate", "evidence_burden_higher_rate"),
    ("credibility_more_skeptical_rate", "credibility_more_skeptical_rate"),
)


def _load_group_summary(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Group summary not found: {path}")
    return pd.read_csv(path)


def _aggregate_by_variant_type(group_summary: pd.DataFrame) -> pd.DataFrame:
    if group_summary.empty:
        return pd.DataFrame(columns=["variant_type"])
    if "variant_type" not in group_summary.columns:
        raise ValueError("Group summary CSV must include a variant_type column.")
    return (
        group_summary.groupby("variant_type", as_index=False)
        .mean(numeric_only=True)
        .sort_values("variant_type")
    )


def _delta(baseline_value: Any, comparison_value: Any) -> float | None:
    if pd.isna(baseline_value) or pd.isna(comparison_value):
        return None
    return round(float(comparison_value) - float(baseline_value), 4)


def compute_mitigation_comparison(
    baseline_summary: pd.DataFrame,
    fairness_summary: pd.DataFrame,
    *,
    demographic_blind_summary: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Compute per-variant mitigation deltas relative to baseline."""
    baseline = _aggregate_by_variant_type(baseline_summary)
    fairness = _aggregate_by_variant_type(fairness_summary)

    merged = baseline.merge(
        fairness,
        on="variant_type",
        how="outer",
        suffixes=("_baseline", "_fairness"),
    )

    blind: pd.DataFrame | None = None
    if demographic_blind_summary is not None:
        blind = _aggregate_by_variant_type(demographic_blind_summary)
        merged = merged.merge(
            blind,
            on="variant_type",
            how="outer",
            suffixes=("", "_demographic_blind"),
        )

    rows: list[dict[str, Any]] = []
    for _, row in merged.sort_values("variant_type").iterrows():
        out: dict[str, Any] = {"variant_type": row["variant_type"]}
        for column, label in _COMPARISON_METRICS:
            baseline_col = f"{column}_baseline"
            fairness_col = f"{column}_fairness"
            baseline_value = row.get(baseline_col)
            fairness_value = row.get(fairness_col)
            out[f"baseline_{label}"] = baseline_value
            out[f"fairness_{label}"] = fairness_value
            out[f"delta_{label}"] = _delta(baseline_value, fairness_value)

            if blind is not None:
                blind_col = f"{column}_demographic_blind"
                if blind_col not in row.index:
                    blind_col = column
                blind_value = row.get(blind_col)
                out[f"demographic_blind_{label}"] = blind_value
                out[f"delta_demographic_blind_{label}"] = _delta(
                    baseline_value, blind_value
                )
        rows.append(out)

    return pd.DataFrame(rows)


def save_mitigation_comparison(
    comparison_df: pd.DataFrame,
    output_path: Path,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def run_mitigation_comparison(
    baseline_path: Path,
    fairness_aware_path: Path,
    *,
    demographic_blind_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Load V2 group summaries and write mitigation comparison CSV."""
    settings = get_settings()
    baseline_df = _load_group_summary(baseline_path)
    fairness_df = _load_group_summary(fairness_aware_path)
    blind_df = (
        _load_group_summary(demographic_blind_path)
        if demographic_blind_path is not None
        else None
    )
    comparison = compute_mitigation_comparison(
        baseline_df,
        fairness_df,
        demographic_blind_summary=blind_df,
    )
    if output_path is None:
        if demographic_blind_path is not None:
            resolved_output = settings.RESULTS_DIR / "tables" / "mitigation_comparison.csv"
        else:
            resolved_output = (
                settings.RESULTS_DIR / "tables" / "fairness_mitigation_comparison.csv"
            )
    else:
        resolved_output = output_path
    saved_path = save_mitigation_comparison(comparison, resolved_output)
    result = {
        "baseline_path": baseline_path,
        "fairness_aware_path": fairness_aware_path,
        "comparison_rows": len(comparison),
        "output_path": saved_path,
        "comparison": comparison,
    }
    if demographic_blind_path is not None:
        result["demographic_blind_path"] = demographic_blind_path
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare baseline vs mitigation V2 group summaries."
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        required=True,
        help="Path to baseline v2_group_summary CSV.",
    )
    parser.add_argument(
        "--fairness-aware",
        type=Path,
        required=True,
        help="Path to fairness-aware v2_group_summary CSV.",
    )
    parser.add_argument(
        "--demographic-blind",
        type=Path,
        default=None,
        help="Optional path to demographic-blind v2_group_summary CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path (default depends on whether --demographic-blind is set).",
    )
    args = parser.parse_args(argv)

    result = run_mitigation_comparison(
        args.baseline,
        args.fairness_aware,
        demographic_blind_path=args.demographic_blind,
        output_path=args.output,
    )
    print(f"Baseline summary:       {result['baseline_path']}")
    print(f"Fairness-aware summary: {result['fairness_aware_path']}")
    if args.demographic_blind is not None:
        print(f"Demographic-blind summary: {result['demographic_blind_path']}")
    print(f"Comparison rows:        {result['comparison_rows']}")
    print(f"  → {result['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
