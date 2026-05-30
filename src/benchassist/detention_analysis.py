"""Detention mock/real analysis pipeline — metrics and reports."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.dataset_modes import exclude_from_strict_bias
from benchassist.detention_metrics import (
    compute_detention_group_summary,
    compute_detention_overview_metrics,
    compute_detention_pairwise_comparisons,
    extract_detention_flagged_cases,
    filter_detention_strict_eligible,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_outputs(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if path.suffix.lower() == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    else:
        rows = pd.read_csv(path).to_dict(orient="records")
    return pd.DataFrame(rows)


def run_detention_analysis(
    outputs_path: Path,
    *,
    output_dir: Path,
    strict_only: bool = False,
) -> dict[str, Any]:
    """Run detention metrics and write analysis artefacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    df = _load_outputs(outputs_path)

    if strict_only:
        analysis_df = filter_detention_strict_eligible(df)
    else:
        analysis_df = df.copy()

    pairwise = compute_detention_pairwise_comparisons(analysis_df)
    group_summary = compute_detention_group_summary(pairwise)
    flagged = extract_detention_flagged_cases(pairwise)
    overview = compute_detention_overview_metrics(analysis_df, pairwise)

    paths = {
        "pairwise": output_dir / "detention_pairwise_comparison.csv",
        "group": output_dir / "detention_group_summary.csv",
        "flagged": output_dir / "detention_flagged_cases.csv",
        "metric_json": output_dir / "detention_metric_summary.json",
        "report_md": output_dir / "detention_analysis_report.md",
    }

    pairwise.to_csv(paths["pairwise"], index=False, encoding="utf-8-sig")
    group_summary.to_csv(paths["group"], index=False, encoding="utf-8-sig")
    flagged.to_csv(paths["flagged"], index=False, encoding="utf-8-sig")

    metric_summary = {
        **overview,
        "generated_at": _utc_now(),
        "strict_only": strict_only,
        "source_outputs": str(outputs_path),
        "n_outputs_total": len(df),
        "n_outputs_analyzed": len(analysis_df),
        "methodology_note": (
            "Screening signals only — may indicate possible concerns for legal review. "
            "Not proof of unlawful discrimination. Mock outputs are not research findings."
        ),
    }
    paths["metric_json"].write_text(json.dumps(metric_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Detention Analysis Report (Mock/Local QA)",
        "",
        f"Generated: {metric_summary['generated_at']}",
        "",
        "## Summary",
        "",
        f"- Total outputs: {metric_summary['n_outputs_total']}",
        f"- Strict-eligible analyzed: {metric_summary['n_outputs_analyzed']}",
        f"- Pairwise comparisons: {metric_summary['n_pairwise_comparisons']}",
        f"- Flagged comparisons: {metric_summary['n_flagged_comparisons']}",
        "",
        "## Methodology",
        "",
        metric_summary["methodology_note"],
        "",
        "This report uses cautious audit language only. It does **not** claim bias is proven, "
        "discriminatory, illegal, or that the model failed fairness.",
        "",
        "## Flagged variant types",
        "",
    ]
    if len(flagged):
        for vt in sorted(flagged["variant_type"].unique()):
            lines.append(f"- {vt}")
    else:
        lines.append("- None flagged in this mock run.")
    lines.extend(["", "## Outputs", ""] + [f"- `{p.name}`" for p in paths.values()])
    paths["report_md"].write_text("\n".join(lines), encoding="utf-8")

    return {"paths": paths, "metric_summary": metric_summary, "pairwise": pairwise, "flagged": flagged}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run detention audit analysis.")
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--strict-only", action="store_true")
    args = parser.parse_args(argv)

    result = run_detention_analysis(
        args.outputs,
        output_dir=args.output_dir,
        strict_only=args.strict_only,
    )
    ms = result["metric_summary"]
    print(
        f"Detention analysis: {ms['n_pairwise_comparisons']} pairwise, "
        f"{ms['n_flagged_comparisons']} flagged → {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
