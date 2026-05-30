"""One-command pipeline helpers: status, offline demo, and real-run planning."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def print_real_run_plan() -> None:
    """Print suggested real (Gemini) commands without calling APIs."""
    print(
        """
Suggested real-model commands (require API keys; not run automatically):

# Baseline V2
python -m benchassist.run_batch \\
  --provider gemini \\
  --model-name gemini-2.5-flash-lite \\
  --schema-version v2 \\
  --prompt-mode baseline

# Fairness-aware V2
python -m benchassist.run_batch \\
  --provider gemini \\
  --model-name gemini-2.5-flash-lite \\
  --schema-version v2 \\
  --prompt-mode fairness_aware

# Demographic-blind V2
python -m benchassist.run_batch \\
  --provider gemini \\
  --model-name gemini-2.5-flash-lite \\
  --schema-version v2 \\
  --prompt-mode demographic_blind

# Grounded V3
python -m benchassist.run_batch \\
  --provider gemini \\
  --model-name gemini-2.5-flash-lite \\
  --schema-version v3 \\
  --prompt-mode grounded \\
  --top-k-sources 5

# V2 metrics (after each run)
python -m benchassist.audit_metrics --version v2 \\
  --input results/outputs/model_outputs_gemini-2.5-flash-lite_v2_baseline.csv \\
  --output-suffix gemini_flash_lite_baseline

# Counterfactual validity
python -m benchassist.counterfactual_validity \\
  --base-cases data/processed/base_cases.csv \\
  --counterfactuals data/audit/counterfactual_cases.csv \\
  --output-suffix current

# Narrative robustness (after baseline pairwise exists)
python -m benchassist.narrative_robustness \\
  --pairwise results/tables/v2_pairwise_comparison_gemini_flash_lite_baseline.csv \\
  --validity results/tables/counterfactual_validity_current.csv \\
  --output-suffix gemini_flash_lite_baseline

# Stereotype audit
python -m benchassist.stereotype_audit \\
  --outputs results/outputs/model_outputs_gemini-2.5-flash-lite_v2_baseline.csv \\
  --output-suffix gemini_flash_lite_baseline

# Qualitative cases
python -m benchassist.qualitative_cases \\
  --outputs results/outputs/model_outputs_gemini-2.5-flash-lite_v2_baseline.csv \\
  --pairwise results/tables/v2_pairwise_comparison_gemini_flash_lite_baseline.csv \\
  --flagged results/tables/v2_flagged_cases_gemini_flash_lite_baseline.csv \\
  --output-suffix gemini_flash_lite_baseline

# Hallucination audit (after grounded outputs exist)
python -m benchassist.hallucination_audit \\
  --input results/outputs/model_outputs_gemini-2.5-flash-lite_v3_grounded.csv \\
  --output-suffix gemini_grounded

# Final report
python -m benchassist.final_report --auto

# Submission package (after reports/tables exist)
python -m benchassist.submission_package --auto
""".strip()
    )


def pipeline_status(
    *,
    results_dir: Path | None = None,
    data_dir: Path | None = None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Return presence checks for key artefacts (no API calls)."""
    from benchassist.config import get_settings

    settings = get_settings()
    data = data_dir or settings.DATA_DIR
    results = results_dir or settings.RESULTS_DIR
    root = project_root or Path(__file__).resolve().parent.parent.parent
    tables = results / "tables"
    outputs = results / "outputs"
    report = results / "report"
    submission_dir = results / "submission_package"
    submission_zip = results / "submission_package.zip"

    checks: dict[str, bool] = {
        "base_cases.csv": (data / "processed" / "base_cases.csv").exists(),
        "counterfactual_cases.csv": (data / "audit" / "counterfactual_cases.csv").exists(),
        "narrative_framing_variants.csv": (data / "audit" / "narrative_framing_variants.csv").exists(),
        "any_model_outputs": any(outputs.glob("*.csv")) if outputs.is_dir() else False,
        "any_v2_pairwise": any(tables.glob("v2_pairwise_comparison*.csv")) if tables.is_dir() else False,
        "final_audit_report.md": (report / "final_audit_report.md").exists(),
        "PROJECT_OVERVIEW.md": (root / "PROJECT_OVERVIEW.md").exists(),
        "DATA_DICTIONARY.md": (root / "DATA_DICTIONARY.md").exists(),
        "LEGAL_EXPERT_RUNBOOK.md": (root / "LEGAL_EXPERT_RUNBOOK.md").exists(),
        "SUBMISSION_PACKAGE.md": (root / "SUBMISSION_PACKAGE.md").exists(),
        "submission_package/": submission_dir.is_dir(),
        "submission_package.zip": submission_zip.is_file(),
    }
    return {
        "data_dir": str(data),
        "results_dir": str(results),
        "project_root": str(root),
        "checks": checks,
        "output_files": sorted(p.name for p in outputs.glob("*.csv"))[:20] if outputs.is_dir() else [],
        "table_files": sorted(p.name for p in tables.glob("*.csv"))[:30] if tables.is_dir() else [],
    }


def print_pipeline_status(status: dict[str, Any]) -> None:
    print(f"Data dir:    {status['data_dir']}")
    print(f"Results dir: {status['results_dir']}")
    print("Checks:")
    for key, ok in status["checks"].items():
        print(f"  [{'x' if ok else ' '}] {key}")
    if status.get("output_files"):
        print("Recent outputs (sample):")
        for name in status["output_files"][:10]:
            print(f"  - {name}")
    if status.get("table_files"):
        print("Recent tables (sample):")
        for name in status["table_files"][:10]:
            print(f"  - {name}")


def run_demo_grounded(*, limit: int = 10, top_k_sources: int = 5, output_suffix: str = "mock_grounded") -> None:
    """Run a small offline grounded mock batch and hallucination audit."""
    from benchassist.config import get_settings
    from benchassist.hallucination_audit import run_hallucination_audit
    from benchassist.output_naming import resolve_model_output_basename
    from benchassist.run_batch import run_model_batch

    prefix = "qa_mock_v3_grounded"
    records = run_model_batch(
        provider="mock",
        limit=limit,
        schema_version="v3",
        prompt_mode="grounded",
        top_k_sources=top_k_sources,
        output_prefix=prefix,
    )
    basename = resolve_model_output_basename(
        provider="mock",
        model_name="mock-benchassist",
        schema_version="v3",
        prompt_mode="grounded",
        output_prefix=prefix,
    )
    csv_path = get_settings().RESULTS_DIR / "outputs" / f"{basename}.csv"
    run_hallucination_audit(csv_path, output_suffix=output_suffix or "qa_mock_grounded")
    print(f"✓ Grounded demo complete ({len(records)} outputs)")


def run_demo_pipeline(
    *,
    limit: int = 10,
    output_suffix: str = "qa_pipeline",
    top_k_sources: int = 5,
) -> None:
    """Run an offline mock audit chain (no external APIs)."""
    from benchassist.audit_metrics_v2 import run_v2_counterfactual_audit
    from benchassist.config import get_settings
    from benchassist.counterfactual_validity import run_validity_audit
    from benchassist.data_generation import write_counterfactual_audit_files
    from benchassist.final_report import discover_report_inputs, write_final_audit_report
    from benchassist.hallucination_audit import run_hallucination_audit
    from benchassist.human_review import generate_human_review_template, write_human_review_rubric
    from benchassist.narrative_robustness import run_narrative_robustness
    from benchassist.qualitative_cases import run_qualitative_cases
    from benchassist.run_batch import run_model_batch
    from benchassist.statistical_analysis import run_statistical_analysis
    from benchassist.stereotype_audit import run_stereotype_audit

    suffix = output_suffix.strip().replace("/", "-")
    settings = get_settings()
    tables = settings.RESULTS_DIR / "tables"
    outputs = settings.RESULTS_DIR / "outputs"

    print("Step 1/10 — Ensure counterfactual data (variant_set=all)")
    write_counterfactual_audit_files(variant_set="all")

    print("Step 2/10 — Mock V2 baseline batch")
    run_model_batch(
        provider="mock",
        limit=limit,
        schema_version="v2",
        prompt_mode="baseline",
        output_prefix="qa_mock_v2_baseline",
    )
    baseline_csv = outputs / "qa_mock_v2_baseline.csv"

    print("Step 3/10 — V2 audit metrics")
    audit_result = run_v2_counterfactual_audit(
        model_outputs_path=baseline_csv,
        tables_dir=tables,
        output_suffix=f"{suffix}_baseline",
    )
    pairwise_path = audit_result["tables"]["pairwise"]

    print("Step 4/10 — Counterfactual validity")
    validity_result = run_validity_audit(
        base_cases_path=settings.DATA_DIR / "processed" / "base_cases.csv",
        counterfactuals_path=settings.DATA_DIR / "audit" / "counterfactual_cases.csv",
        output_suffix=suffix,
    )
    validity_per_path = validity_result["paths"]["per_variant"]

    print("Step 5/10 — Narrative robustness")
    run_narrative_robustness(
        pairwise_path=pairwise_path,
        validity_path=validity_per_path,
        output_suffix=suffix,
    )

    print("Step 6/10 — Stereotype audit")
    run_stereotype_audit(baseline_csv, output_suffix=f"{suffix}_baseline")

    print("Step 7/10 — Statistical analysis (fast bootstrap)")
    run_statistical_analysis(
        pairwise_path=pairwise_path,
        output_suffix=f"{suffix}_baseline",
        bootstrap_samples=200,
        seed=42,
    )

    print("Step 8/10 — Qualitative cases")
    qual = run_qualitative_cases(
        outputs_path=baseline_csv,
        pairwise_path=pairwise_path,
        flagged_path=audit_result["tables"].get("flagged"),
        top_n=5,
        output_suffix=f"{suffix}_baseline",
    )

    print("Step 9/10 — Mock V3 grounded + hallucination audit")
    run_model_batch(
        provider="mock",
        limit=limit,
        schema_version="v3",
        prompt_mode="grounded",
        top_k_sources=top_k_sources,
        output_prefix="qa_mock_v3_grounded",
    )
    run_hallucination_audit(
        outputs / "qa_mock_v3_grounded.csv",
        output_suffix=f"{suffix}_grounded",
    )

    print("Step 10/10 — Human review template + final report")
    write_human_review_rubric()
    generate_human_review_template(
        qual["paths"]["csv"],
        output_path=tables / f"human_review_template_{suffix}.csv",
        validity_path=validity_per_path,
    )
    write_final_audit_report(discover_report_inputs())

    print(f"✓ Demo pipeline complete (suffix={suffix})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BenchAssist-IL pipeline helpers.")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run offline mock audit pipeline (V2 baseline + audits + final report).",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print artefact presence checks (no API calls).",
    )
    parser.add_argument(
        "--prompt-mode",
        default="grounded",
        help="Legacy flag for small grounded-only demo.",
    )
    parser.add_argument(
        "--schema-version",
        default="v3",
        help="Legacy flag for small grounded-only demo.",
    )
    parser.add_argument("--limit", type=int, default=10, help="Case limit for --demo.")
    parser.add_argument(
        "--output-suffix",
        default="qa_pipeline",
        help="Suffix for demo pipeline artefacts (default: qa_pipeline).",
    )
    parser.add_argument(
        "--top-k-sources",
        type=int,
        default=5,
        help="Sources to retrieve in grounded mode.",
    )
    parser.add_argument(
        "--print-real-run-plan",
        action="store_true",
        help="Print suggested Gemini commands (no API calls).",
    )
    parser.add_argument(
        "--grounded-only",
        action="store_true",
        help="Run only mock V3 grounded + hallucination audit (legacy behavior).",
    )
    args = parser.parse_args(argv)

    if args.print_real_run_plan:
        print_real_run_plan()
        return 0

    if args.status:
        print_pipeline_status(pipeline_status())
        return 0

    if args.demo:
        if args.grounded_only:
            run_demo_grounded(limit=args.limit, top_k_sources=args.top_k_sources)
        else:
            run_demo_pipeline(
                limit=args.limit,
                output_suffix=args.output_suffix,
                top_k_sources=args.top_k_sources,
            )
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
