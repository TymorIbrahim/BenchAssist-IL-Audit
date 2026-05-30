"""Repeated-run stability metrics for BenchAssist-IL audit outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from benchassist.audit_metrics_v2 import (
    CREDIBILITY_SKEPTICISM_SCORE_MAP,
    EVIDENCE_BURDEN_SCORE_MAP,
    PROCEDURAL_POSTURE_SCORE_MAP,
    RIGHTS_ORIENTATION_SCORE_MAP,
    _add_v2_score_columns,
    _map_score,
    _row_memo_payload,
    _safe_int,
    _safe_value,
    load_model_outputs_file,
)
from benchassist.config import get_settings
from benchassist.schemas import normalize_bench_memo_output

_WITHIN_PROMPT_GROUP = ["case_id", "variant_id", "prompt_mode", "schema_version"]
_GROUP_SUMMARY_GROUP = ["variant_type", "demographic_cue", "prompt_mode"]

_STABILITY_TABLES = {
    "within_prompt": "stability_within_prompt.csv",
    "group_summary": "stability_group_summary.csv",
    "counterfactual_vs_random": "counterfactual_vs_random_instability.csv",
}

_CHART_SPECS = [
    (
        "any_instability_rate",
        "stability_any_instability_rate_by_variant.png",
        "Any Instability Rate by Variant Type",
        "Any Instability Rate",
    ),
    (
        "action_type_instability_rate",
        "stability_action_type_instability_rate_by_variant.png",
        "Action Type Instability Rate by Variant Type",
        "Action Type Instability Rate",
    ),
    (
        "avg_remedy_strength_range",
        "stability_avg_remedy_strength_range_by_variant.png",
        "Average Remedy Strength Range by Variant Type",
        "Avg Remedy Strength Range",
    ),
]


def _table_path(tables_dir: Path, key: str, output_suffix: str | None) -> Path:
    filename = _STABILITY_TABLES[key]
    if output_suffix:
        stem, ext = filename.rsplit(".", 1)
        filename = f"{stem}_{output_suffix}.{ext}"
    return tables_dir / filename


def load_stability_outputs(path: str | Path) -> pd.DataFrame:
    """Load model outputs and normalize fields, preserving repetition metadata."""
    raw_df = load_model_outputs_file(Path(path))
    rows: list[dict[str, Any]] = []

    for _, row in raw_df.iterrows():
        record: dict[str, Any] = {
            "case_id": _safe_value(row.get("case_id")),
            "variant_id": _safe_value(row.get("variant_id")),
            "variant_type": _safe_value(row.get("variant_type")),
            "demographic_cue": _safe_value(row.get("demographic_cue")),
            "language": _safe_value(row.get("language")),
            "input_text": _safe_value(row.get("input_text")),
            "schema_version": _safe_value(row.get("schema_version")) or "v1",
            "prompt_mode": _safe_value(row.get("prompt_mode")) or "baseline",
            "repetition_index": _safe_int(row.get("repetition_index"), 1),
            "parse_error": _safe_value(row.get("parse_error")),
        }

        memo_payload = _row_memo_payload(row)
        if memo_payload:
            memo_payload.setdefault("case_summary", "")
            memo_payload.setdefault("reasoning_text", memo_payload.get("reasoning", ""))
            memo_payload.setdefault("confidence", "medium")
            memo_payload.setdefault("limitations", "")
            memo_payload.setdefault("evidence_needed", [])
            memo_payload.setdefault("risk_flags", [])
            normalized = normalize_bench_memo_output(memo_payload)
            record.update(normalized)
        else:
            for field in (
                "urgency",
                "recommended_action_type",
                "remedy_strength_score",
                "evidence_burden_level",
                "party_credibility_framing",
                "rights_orientation",
                "procedural_posture",
            ):
                record[field] = None

        rows.append(record)

    df = pd.DataFrame(rows)
    return _add_v2_score_columns(df)


def _score_range(series: pd.Series, mapping: dict[str, int]) -> float:
    values = [
        _map_score(value, mapping, default=-1)
        for value in series.dropna()
        if _safe_value(value) is not None
    ]
    values = [value for value in values if value >= 0]
    if not values:
        return 0.0
    return float(max(values) - min(values))


def compute_within_prompt_stability(df: pd.DataFrame) -> pd.DataFrame:
    """Compute instability metrics for repeated runs of the same prompt."""
    rows: list[dict[str, Any]] = []
    grouped = df.groupby(_WITHIN_PROMPT_GROUP, dropna=False)

    for keys, group in grouped:
        if not isinstance(keys, tuple):
            keys = (keys,)
        key_map = dict(zip(_WITHIN_PROMPT_GROUP, keys, strict=True))

        urgencies = group["urgency"].dropna().astype(str)
        actions = group["recommended_action_type"].dropna().astype(str)
        remedy_scores = group["remedy_strength_score"].apply(lambda value: _safe_int(value, -1))
        remedy_scores = remedy_scores[remedy_scores >= 0]

        unique_urgency_count = urgencies.nunique()
        unique_action_count = actions.nunique()
        urgency_instability = unique_urgency_count > 1
        action_type_instability = unique_action_count > 1

        remedy_range = (
            float(remedy_scores.max() - remedy_scores.min())
            if len(remedy_scores) > 0
            else 0.0
        )
        evidence_range = _score_range(group["evidence_burden_level"], EVIDENCE_BURDEN_SCORE_MAP)
        credibility_range = _score_range(
            group["party_credibility_framing"], CREDIBILITY_SKEPTICISM_SCORE_MAP
        )
        rights_range = _score_range(group["rights_orientation"], RIGHTS_ORIENTATION_SCORE_MAP)
        procedural_range = _score_range(
            group["procedural_posture"], PROCEDURAL_POSTURE_SCORE_MAP
        )

        any_instability = bool(
            urgency_instability
            or action_type_instability
            or remedy_range > 0
            or evidence_range > 0
            or credibility_range > 0
            or rights_range > 0
            or procedural_range > 0
        )

        sample = group.iloc[0]
        rows.append(
            {
                **key_map,
                "variant_type": sample.get("variant_type"),
                "demographic_cue": sample.get("demographic_cue"),
                "n_repetitions": len(group),
                "unique_urgency_count": unique_urgency_count,
                "unique_recommended_action_type_count": unique_action_count,
                "urgency_instability": urgency_instability,
                "action_type_instability": action_type_instability,
                "remedy_strength_range": remedy_range,
                "evidence_burden_range": evidence_range,
                "credibility_skepticism_range": credibility_range,
                "rights_orientation_range": rights_range,
                "procedural_posture_range": procedural_range,
                "any_instability": any_instability,
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values(_WITHIN_PROMPT_GROUP).reset_index(drop=True)


def compute_stability_group_summary(within_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate within-prompt stability by variant type and demographic cue."""
    if within_df.empty:
        return pd.DataFrame()

    grouped = (
        within_df.groupby(_GROUP_SUMMARY_GROUP, dropna=False)
        .agg(
            n_prompts=("case_id", "count"),
            urgency_instability_rate=("urgency_instability", "mean"),
            action_type_instability_rate=("action_type_instability", "mean"),
            avg_remedy_strength_range=("remedy_strength_range", "mean"),
            avg_evidence_burden_range=("evidence_burden_range", "mean"),
            avg_credibility_skepticism_range=("credibility_skepticism_range", "mean"),
            avg_rights_orientation_range=("rights_orientation_range", "mean"),
            avg_procedural_posture_range=("procedural_posture_range", "mean"),
            any_instability_rate=("any_instability", "mean"),
        )
        .reset_index()
    )
    return grouped.round(4)


def compare_counterfactual_vs_random_instability(
    pairwise_df: pd.DataFrame,
    stability_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compare counterfactual flip rates to repeated-run random instability."""
    comparison = pairwise_df[pairwise_df["variant_type"] != "neutral_he"].copy()
    if comparison.empty or stability_df.empty:
        return pd.DataFrame()

    pairwise_by_variant = (
        comparison.groupby("variant_type", as_index=False)
        .agg(
            counterfactual_action_flip_rate=("action_type_flip", "mean"),
            counterfactual_legal_framing_bias_flag_rate=(
                "legal_framing_bias_flag",
                "mean",
            ),
        )
    )

    stability_by_variant = (
        stability_df.groupby("variant_type", as_index=False)
        .agg(
            random_action_instability_rate=("action_type_instability_rate", "mean"),
            random_any_instability_rate=("any_instability_rate", "mean"),
        )
    )

    merged = pairwise_by_variant.merge(
        stability_by_variant,
        on="variant_type",
        how="outer",
    )
    merged["delta_action_instability"] = (
        merged["counterfactual_action_flip_rate"]
        - merged["random_action_instability_rate"]
    ).round(4)
    merged["delta_total_instability"] = (
        merged["counterfactual_legal_framing_bias_flag_rate"]
        - merged["random_any_instability_rate"]
    ).round(4)
    return merged.sort_values("variant_type").reset_index(drop=True)


def _load_pairwise_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Pairwise comparison not found: {path}")
    return pd.read_csv(path)


def generate_stability_charts(
    group_summary: pd.DataFrame,
    charts_dir: Path,
    *,
    comparison_df: pd.DataFrame | None = None,
    output_suffix: str | None = None,
) -> dict[str, Path]:
    """Generate matplotlib stability charts."""
    charts_dir.mkdir(parents=True, exist_ok=True)
    saved: dict[str, Path] = {}

    if not group_summary.empty:
        plot_df = (
            group_summary.groupby("variant_type", as_index=False)
            .mean(numeric_only=True)
            .sort_values("variant_type")
        )
        x_labels = plot_df["variant_type"].tolist()
        x_positions = range(len(x_labels))

        for column, filename, title, ylabel in _CHART_SPECS:
            if column not in plot_df.columns:
                continue
            if output_suffix:
                stem, ext = filename.rsplit(".", 1)
                filename = f"{stem}_{output_suffix}.{ext}"
            fig, ax = plt.subplots(figsize=(9, 4))
            ax.bar(x_positions, plot_df[column].tolist())
            ax.set_title(title)
            ax.set_xlabel("Variant type")
            ax.set_ylabel(ylabel)
            ax.set_xticks(list(x_positions))
            ax.set_xticklabels(x_labels, rotation=35, ha="right")
            fig.tight_layout()
            path = charts_dir / filename
            fig.savefig(path, dpi=150)
            plt.close(fig)
            saved[column] = path

    if comparison_df is not None and not comparison_df.empty:
        filename = "counterfactual_vs_random_action_instability.png"
        if output_suffix:
            stem, ext = filename.rsplit(".", 1)
            filename = f"{stem}_{output_suffix}.{ext}"
        plot_df = comparison_df.sort_values("variant_type")
        x_labels = plot_df["variant_type"].tolist()
        x_positions = range(len(x_labels))
        width = 0.35
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(
            [x - width / 2 for x in x_positions],
            plot_df["counterfactual_action_flip_rate"].tolist(),
            width=width,
            label="Counterfactual flip rate",
        )
        ax.bar(
            [x + width / 2 for x in x_positions],
            plot_df["random_action_instability_rate"].tolist(),
            width=width,
            label="Random instability rate",
        )
        ax.set_title("Counterfactual vs Random Action Instability")
        ax.set_xlabel("Variant type")
        ax.set_ylabel("Rate")
        ax.set_xticks(list(x_positions))
        ax.set_xticklabels(x_labels, rotation=35, ha="right")
        ax.legend()
        fig.tight_layout()
        path = charts_dir / filename
        fig.savefig(path, dpi=150)
        plt.close(fig)
        saved["counterfactual_vs_random"] = path

    return saved


def run_stability_analysis(
    model_outputs_path: Path,
    *,
    pairwise_path: Path | None = None,
    tables_dir: Path | None = None,
    charts_dir: Path | None = None,
    output_suffix: str | None = None,
) -> dict[str, Any]:
    """Load repeated outputs, compute stability tables, and save charts."""
    settings = get_settings()
    out_tables = tables_dir or (settings.RESULTS_DIR / "tables")
    out_charts = charts_dir or (settings.RESULTS_DIR / "charts")
    out_tables.mkdir(parents=True, exist_ok=True)

    outputs_df = load_stability_outputs(model_outputs_path)
    within_df = compute_within_prompt_stability(outputs_df)
    group_df = compute_stability_group_summary(within_df)

    table_paths = {
        "within_prompt": _table_path(out_tables, "within_prompt", output_suffix),
        "group_summary": _table_path(out_tables, "group_summary", output_suffix),
    }
    within_df.to_csv(table_paths["within_prompt"], index=False, encoding="utf-8-sig")
    group_df.to_csv(table_paths["group_summary"], index=False, encoding="utf-8-sig")

    comparison_df: pd.DataFrame | None = None
    if pairwise_path is not None:
        pairwise_df = _load_pairwise_csv(pairwise_path)
        comparison_df = compare_counterfactual_vs_random_instability(
            pairwise_df, group_df
        )
        comparison_path = _table_path(
            out_tables, "counterfactual_vs_random", output_suffix
        )
        comparison_df.to_csv(comparison_path, index=False, encoding="utf-8-sig")
        table_paths["counterfactual_vs_random"] = comparison_path

    chart_paths = generate_stability_charts(
        group_df,
        out_charts,
        comparison_df=comparison_df,
        output_suffix=output_suffix,
    )

    return {
        "outputs_loaded": len(outputs_df),
        "within_prompt_rows": len(within_df),
        "group_summary_rows": len(group_df),
        "tables": table_paths,
        "charts": chart_paths,
        "comparison_rows": len(comparison_df) if comparison_df is not None else 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compute repeated-run stability metrics for model outputs."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to repeated model_outputs CSV or JSONL.",
    )
    parser.add_argument(
        "--pairwise",
        type=Path,
        default=None,
        help="Optional V2 pairwise comparison CSV for counterfactual vs random analysis.",
    )
    parser.add_argument(
        "--tables-dir",
        type=Path,
        default=None,
        help="Directory for stability tables (default: results/tables).",
    )
    parser.add_argument(
        "--charts-dir",
        type=Path,
        default=None,
        help="Directory for stability charts (default: results/charts).",
    )
    parser.add_argument(
        "--output-suffix",
        default=None,
        help="Optional suffix for output filenames (e.g. baseline).",
    )
    args = parser.parse_args(argv)

    result = run_stability_analysis(
        args.input,
        pairwise_path=args.pairwise,
        tables_dir=args.tables_dir,
        charts_dir=args.charts_dir,
        output_suffix=args.output_suffix,
    )

    print(f"Outputs loaded:          {result['outputs_loaded']}")
    print(f"Within-prompt rows:      {result['within_prompt_rows']}")
    print(f"Group summary rows:      {result['group_summary_rows']}")
    for name, path in result["tables"].items():
        print(f"  {name}: {path}")
    for name, path in result["charts"].items():
        print(f"  chart_{name}: {path}")
    if args.pairwise is not None:
        print(f"Comparison rows:         {result['comparison_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
