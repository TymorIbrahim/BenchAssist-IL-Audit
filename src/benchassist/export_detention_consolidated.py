"""Export one consolidated CSV for the detention expanded-full audit dataset."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_RUN_DIR = PROJECT_ROOT / "results" / "gemini" / "detention_expanded_full"
DEFAULT_SYNTHETIC = PROJECT_ROOT / "data" / "synthetic" / "detention_core_cases.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "export" / "detention_expanded_full_consolidated_audit_data.csv"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def export_detention_consolidated_csv(
    *,
    run_dir: Path = DEFAULT_RUN_DIR,
    synthetic_path: Path = DEFAULT_SYNTHETIC,
    output_path: Path = DEFAULT_OUTPUT,
) -> Path:
    analysis_dir = run_dir / "analysis"
    pairwise_path = analysis_dir / "detention_pairwise_comparison.csv"
    manifest_path = run_dir / "run_manifest.json"
    metrics_path = analysis_dir / "detention_full_metric_summary.json"

    if not pairwise_path.exists():
        raise FileNotFoundError(f"Missing pairwise comparisons: {pairwise_path}")
    if not synthetic_path.exists():
        raise FileNotFoundError(f"Missing synthetic corpus: {synthetic_path}")

    pairwise = pd.read_csv(pairwise_path)
    synthetic = pd.read_csv(synthetic_path)

    syn_cols = [
        "base_case_id",
        "variant_id",
        "dataset_mode",
        "variant_category",
        "counterfactual_strength",
        "use_for_strict_bias_rates",
        "exclude_from_strict_bias_rates",
        "title",
        "legal_area",
        "normalized_domain",
        "language",
        "source_note",
    ]
    syn_subset = synthetic[[c for c in syn_cols if c in synthetic.columns]].copy()
    syn_subset = syn_subset.rename(columns={"base_case_id": "synthetic_base_case_id"})

    merged = pairwise.merge(
        syn_subset,
        left_on=["case_id", "variant_id"],
        right_on=["synthetic_base_case_id", "variant_id"],
        how="left",
    )
    if "synthetic_base_case_id" in merged.columns:
        merged = merged.drop(columns=["synthetic_base_case_id"])

    manifest: dict = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    metrics: dict = {}
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    merged.insert(0, "export_generated_at", _utc_now())
    merged.insert(1, "project_name", "BenchAssist-IL Detention Audit")
    merged.insert(2, "data_status", "gemini_expanded_full")
    merged.insert(3, "run_type", manifest.get("run_type", metrics.get("run_type", "expanded_full")))
    merged.insert(4, "model", manifest.get("model", "gemini-2.5-flash-lite"))
    merged.insert(5, "prompt_modes", ",".join(manifest.get("prompt_modes", ["baseline", "fairness_aware", "demographic_blind"])))
    merged.insert(6, "source_synthetic_csv", str(synthetic_path.relative_to(PROJECT_ROOT)))
    merged.insert(7, "source_pairwise_csv", str(pairwise_path.relative_to(PROJECT_ROOT)))
    merged.insert(8, "source_run_manifest", str(manifest_path.relative_to(PROJECT_ROOT)) if manifest_path.exists() else "")
    merged.insert(9, "methodology_note", manifest.get("caution", metrics.get("evidence_level", "")))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export consolidated detention audit CSV.")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--synthetic", type=Path, default=DEFAULT_SYNTHETIC)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    out = export_detention_consolidated_csv(
        run_dir=args.run_dir,
        synthetic_path=args.synthetic,
        output_path=args.output,
    )
    df = pd.read_csv(out)
    print(f"Wrote {len(df)} rows to {out}")


if __name__ == "__main__":
    main()
