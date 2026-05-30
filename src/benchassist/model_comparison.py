"""Compare V2 group summary metrics across multiple model runs."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from benchassist.config import get_settings
from benchassist.output_naming import sanitize_output_token

_COMPARISON_METRICS: tuple[str, ...] = (
    "action_type_flip_rate",
    "legal_framing_bias_flag_rate",
    "remedy_weaker_rate",
    "evidence_burden_higher_rate",
    "credibility_more_skeptical_rate",
    "rights_orientation_weaker_rate",
    "avg_remedy_strength_delta",
    "avg_evidence_burden_delta",
    "avg_credibility_skepticism_delta",
    "avg_rights_orientation_delta",
)

_CHART_SPECS: tuple[tuple[str, str, str], ...] = (
    (
        "legal_framing_bias_flag_rate",
        "model_comparison_legal_framing_bias_rate.png",
        "Legal Framing Bias Flag Rate by Model",
    ),
    (
        "action_type_flip_rate",
        "model_comparison_action_flip_rate.png",
        "Action Type Flip Rate by Model",
    ),
    (
        "remedy_weaker_rate",
        "model_comparison_remedy_weaker_rate.png",
        "Remedy Weaker Rate by Model",
    ),
    (
        "evidence_burden_higher_rate",
        "model_comparison_evidence_burden_higher_rate.png",
        "Evidence Burden Higher Rate by Model",
    ),
)

_RUN_PLAN_COMMANDS: tuple[str, ...] = (
    (
        "python -m benchassist.run_batch --provider gemini "
        "--model-name gemini-2.5-flash-lite --schema-version v2 "
        "--prompt-mode baseline --limit 50"
    ),
    (
        "python -m benchassist.run_batch --provider gemini "
        "--model-name gemini-2.5-flash-lite --schema-version v2 "
        "--prompt-mode fairness_aware --limit 50"
    ),
    (
        "python -m benchassist.run_batch --provider gemini "
        "--model-name gemini-2.5-flash-lite --schema-version v2 "
        "--prompt-mode demographic_blind --limit 50"
    ),
    (
        "python -m benchassist.run_batch --provider gemini "
        "--model-name gemini-2.5-flash --schema-version v2 "
        "--prompt-mode baseline --limit 15"
    ),
    (
        "python -m benchassist.run_batch --provider gemini "
        "--model-name gemini-2.5-flash-lite --schema-version v2 "
        "--prompt-mode baseline --limit 10 --repetitions 3"
    ),
    (
        "python -m benchassist.audit_metrics --version v2 "
        "--input results/outputs/model_outputs_gemini-2.5-flash-lite_v2_baseline.csv "
        "--output-suffix gemini_flash_lite_baseline"
    ),
    (
        "python -m benchassist.audit_metrics --version v2 "
        "--input results/outputs/model_outputs_gemini-2.5-flash_v2_baseline.csv "
        "--output-suffix gemini_flash_baseline"
    ),
    (
        "python -m benchassist.model_comparison "
        "--summary results/tables/v2_group_summary_gemini_flash_lite_baseline.csv "
        "--summary results/tables/v2_group_summary_gemini_flash_baseline.csv"
    ),
)


def _load_group_summary(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Group summary not found: {path}")
    return pd.read_csv(path)


def _infer_metadata_from_path(path: Path) -> dict[str, str]:
    """Infer model label and prompt mode from a v2 group summary filename."""
    stem = path.stem
    suffix = stem
    if stem.startswith("v2_group_summary"):
        suffix = stem.removeprefix("v2_group_summary").lstrip("_")

    provider = ""
    model_name = ""
    prompt_mode = "baseline"

    if suffix:
        if suffix.startswith("gemini"):
            provider = "gemini"
            if "flash_lite" in suffix or "flash-lite" in suffix:
                model_name = "gemini-2.5-flash-lite"
            elif "flash" in suffix:
                model_name = "gemini-2.5-flash"
        elif suffix.startswith("mock"):
            provider = "mock"
            model_name = "mock-benchassist"
        elif suffix.startswith("openai") or suffix.startswith("gpt"):
            provider = "openai"
            model_name = suffix.replace("_", "-")

        for mode in ("fairness_aware", "demographic_blind", "baseline"):
            if suffix.endswith(mode) or f"_{mode}" in suffix:
                prompt_mode = mode
                break

    model_label = model_name or suffix or stem
    if provider and model_name:
        model_label = model_name
    elif not model_label:
        model_label = stem

    return {
        "source_file": path.name,
        "provider": provider,
        "model_name": model_name,
        "model_label": sanitize_output_token(model_label),
        "prompt_mode": prompt_mode,
    }


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


def build_model_comparison_long(
    summaries: list[tuple[Path, pd.DataFrame]],
) -> pd.DataFrame:
    """Combine multiple group summaries into a long-format comparison table."""
    frames: list[pd.DataFrame] = []
    for path, summary in summaries:
        aggregated = _aggregate_by_variant_type(summary)
        if aggregated.empty:
            continue
        meta = _infer_metadata_from_path(path)
        for key, value in meta.items():
            aggregated[key] = value
        frames.append(aggregated)

    if not frames:
        return pd.DataFrame(columns=["variant_type", "model_label", *_COMPARISON_METRICS])

    combined = pd.concat(frames, ignore_index=True, sort=False)
    ordered_cols = [
        "source_file",
        "provider",
        "model_name",
        "model_label",
        "prompt_mode",
        "variant_type",
        *_COMPARISON_METRICS,
    ]
    present = [col for col in ordered_cols if col in combined.columns]
    remaining = [col for col in combined.columns if col not in present]
    return combined[present + remaining].round(4)


def build_model_comparison_pivot(long_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot long comparison data so each model/metric pair becomes a column."""
    if long_df.empty:
        return pd.DataFrame(columns=["variant_type"])

    rows: list[dict[str, Any]] = []
    for variant_type, group in long_df.groupby("variant_type", sort=True):
        row: dict[str, Any] = {"variant_type": variant_type}
        for _, model_row in group.iterrows():
            label = str(model_row.get("model_label") or model_row.get("model_name") or "model")
            for metric in _COMPARISON_METRICS:
                if metric in model_row.index:
                    row[f"{label}__{metric}"] = model_row[metric]
        rows.append(row)
    return pd.DataFrame(rows)


def generate_model_comparison_charts(
    long_df: pd.DataFrame,
    charts_dir: Path,
) -> dict[str, Path]:
    """Generate grouped bar charts comparing models across variant types."""
    charts_dir.mkdir(parents=True, exist_ok=True)
    if long_df.empty:
        return {}

    models = (
        long_df[["model_label"]]
        .drop_duplicates()
        .sort_values("model_label")["model_label"]
        .tolist()
    )
    variant_types = sorted(long_df["variant_type"].unique().tolist())
    saved: dict[str, Path] = {}

    for metric, filename, title in _CHART_SPECS:
        if metric not in long_df.columns:
            continue

        x_positions = range(len(variant_types))
        bar_width = 0.8 / max(len(models), 1)
        fig, ax = plt.subplots(figsize=(max(9, len(variant_types) * 0.8), 5))

        for model_index, model_label in enumerate(models):
            model_df = long_df[long_df["model_label"] == model_label]
            values = []
            for variant_type in variant_types:
                match = model_df.loc[model_df["variant_type"] == variant_type, metric]
                values.append(float(match.iloc[0]) if not match.empty else 0.0)
            offsets = [
                pos + (model_index - (len(models) - 1) / 2) * bar_width
                for pos in x_positions
            ]
            ax.bar(offsets, values, width=bar_width, label=model_label)

        ax.set_title(title)
        ax.set_xlabel("Variant type")
        ax.set_ylabel(metric.replace("_", " ").title())
        ax.set_xticks(list(x_positions))
        ax.set_xticklabels(variant_types, rotation=35, ha="right")
        ax.legend(title="Model", fontsize=8)
        fig.tight_layout()
        path = charts_dir / filename
        fig.savefig(path, dpi=150)
        plt.close(fig)
        saved[metric] = path

    return saved


def print_run_plan() -> None:
    """Print suggested multi-model Gemini commands (does not execute them)."""
    print("# Suggested multi-model comparison run plan")
    print("# Copy and run manually; requires GEMINI_API_KEY or GOOGLE_API_KEY in .env\n")
    for index, command in enumerate(_RUN_PLAN_COMMANDS, start=1):
        print(f"# Step {index}")
        print(command)
        print()


def run_model_comparison(
    summary_paths: list[Path],
    *,
    output_path: Path | None = None,
    pivot_output_path: Path | None = None,
    charts_dir: Path | None = None,
) -> dict[str, Any]:
    """Load summaries, write comparison tables, and generate charts."""
    settings = get_settings()
    summaries = [(path, _load_group_summary(path)) for path in summary_paths]
    long_df = build_model_comparison_long(summaries)
    pivot_df = build_model_comparison_pivot(long_df)

    tables_dir = settings.RESULTS_DIR / "tables"
    resolved_output = output_path or tables_dir / "model_comparison.csv"
    resolved_pivot = pivot_output_path or tables_dir / "model_comparison_pivot.csv"
    resolved_charts = charts_dir or settings.RESULTS_DIR / "charts"

    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_pivot.parent.mkdir(parents=True, exist_ok=True)
    long_df.to_csv(resolved_output, index=False, encoding="utf-8-sig")
    pivot_df.to_csv(resolved_pivot, index=False, encoding="utf-8-sig")
    chart_paths = generate_model_comparison_charts(long_df, resolved_charts)

    return {
        "summary_paths": summary_paths,
        "comparison_rows": len(long_df),
        "output_path": resolved_output,
        "pivot_output_path": resolved_pivot,
        "chart_paths": chart_paths,
        "comparison": long_df,
        "pivot": pivot_df,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare V2 group summary metrics across model runs."
    )
    parser.add_argument(
        "--summary",
        type=Path,
        action="append",
        default=[],
        help="Path to a v2_group_summary CSV (repeat for multiple models).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path for the long-format comparison table.",
    )
    parser.add_argument(
        "--pivot-output",
        type=Path,
        default=None,
        help="Output CSV path for the pivot comparison table.",
    )
    parser.add_argument(
        "--charts-dir",
        type=Path,
        default=None,
        help="Directory for comparison charts (default: results/charts).",
    )
    parser.add_argument(
        "--print-run-plan",
        action="store_true",
        help="Print suggested Gemini run commands and exit.",
    )
    args = parser.parse_args(argv)

    if args.print_run_plan:
        print_run_plan()
        return 0

    if len(args.summary) < 1:
        parser.error("Provide at least one --summary path, or use --print-run-plan.")

    result = run_model_comparison(
        args.summary,
        output_path=args.output,
        pivot_output_path=args.pivot_output,
        charts_dir=args.charts_dir,
    )
    print(f"Loaded summaries:        {len(result['summary_paths'])}")
    print(f"Comparison rows:         {result['comparison_rows']}")
    print(f"  → {result['output_path']}")
    print(f"  → {result['pivot_output_path']}")
    for metric, path in result["chart_paths"].items():
        print(f"  → {path} ({metric})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
