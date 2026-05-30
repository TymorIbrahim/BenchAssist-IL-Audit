"""Compare baseline V2 fairness metrics vs grounded V3 runs and hallucination audit."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.config import get_settings

_FAIRNESS_METRICS = (
    "legal_framing_bias_flag_rate",
    "action_type_flip_rate",
    "remedy_weaker_rate",
    "evidence_burden_higher_rate",
    "credibility_more_skeptical_rate",
)

_HALLUCINATION_METRICS = (
    "invalid_citation_rate",
    "unsupported_claim_rate",
    "high_hallucination_risk_rate",
    "avg_hallucination_risk_score",
)


def _load_group_summary(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def build_grounding_comparison(
    *,
    baseline_summary: pd.DataFrame,
    grounded_summary: pd.DataFrame,
    hallucination_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Build long-format comparison rows per variant and metric."""
    keys = ["variant_type", "demographic_cue"]
    rows: list[dict[str, Any]] = []

    def index_by_key(df: pd.DataFrame) -> dict[tuple[Any, ...], pd.Series]:
        if df.empty:
            return {}
        indexed: dict[tuple[Any, ...], pd.Series] = {}
        for _, row in df.iterrows():
            key = (row.get("variant_type"), row.get("demographic_cue", ""))
            indexed[key] = row
        return indexed

    baseline_idx = index_by_key(baseline_summary)
    grounded_idx = index_by_key(grounded_summary)
    hall_idx = index_by_key(hallucination_summary)
    all_keys = set(baseline_idx) | set(grounded_idx) | set(hall_idx)

    for key in sorted(all_keys):
        b_row = baseline_idx.get(key)
        g_row = grounded_idx.get(key)
        h_row = hall_idx.get(key)
        variant_type, demographic_cue = key
        for metric in _FAIRNESS_METRICS:
            b_val = b_row.get(metric) if b_row is not None else None
            g_val = g_row.get(metric) if g_row is not None else None
            delta = None
            if pd.notna(b_val) and pd.notna(g_val):
                delta = float(g_val) - float(b_val)
            rows.append(
                {
                    "variant_type": variant_type,
                    "demographic_cue": demographic_cue,
                    "metric": metric,
                    "baseline_value": b_val,
                    "grounded_value": g_val,
                    "delta_grounded_minus_baseline": delta,
                    "hallucination_value": None,
                }
            )
        for metric in _HALLUCINATION_METRICS:
            h_val = h_row.get(metric) if h_row is not None else None
            rows.append(
                {
                    "variant_type": variant_type,
                    "demographic_cue": demographic_cue,
                    "metric": metric,
                    "baseline_value": None,
                    "grounded_value": None,
                    "delta_grounded_minus_baseline": None,
                    "hallucination_value": h_val,
                }
            )
    return pd.DataFrame(rows)


def run_grounding_comparison(
    *,
    baseline_path: Path,
    grounded_path: Path,
    hallucination_path: Path | None = None,
    output_suffix: str = "comparison",
    results_dir: Path | None = None,
) -> Path:
    comparison = build_grounding_comparison(
        baseline_summary=_load_group_summary(baseline_path),
        grounded_summary=_load_group_summary(grounded_path),
        hallucination_summary=_load_group_summary(hallucination_path),
    )
    root = results_dir or get_settings().RESULTS_DIR
    out_path = root / "tables" / f"grounding_comparison_{output_suffix.strip().replace('/', '-')}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare baseline vs grounded audit metrics.")
    parser.add_argument("--baseline", type=Path, required=True, help="V2 group summary CSV.")
    parser.add_argument("--grounded", type=Path, required=True, help="V2 group summary for grounded run.")
    parser.add_argument(
        "--hallucination",
        type=Path,
        default=None,
        help="Hallucination group summary CSV.",
    )
    parser.add_argument("--output-suffix", type=str, default="comparison")
    args = parser.parse_args(argv)
    path = run_grounding_comparison(
        baseline_path=args.baseline,
        grounded_path=args.grounded,
        hallucination_path=args.hallucination,
        output_suffix=args.output_suffix,
    )
    print(f"  → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
