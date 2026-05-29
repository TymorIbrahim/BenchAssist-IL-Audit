"""One-command end-to-end verification of the BenchAssist-IL audit pipeline."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from benchassist.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineVerificationResult:
    """Summary returned after a successful verification run."""

    base_case_count: int
    counterfactual_count: int
    model_output_count: int
    group_summary_path: Path
    audit_report_path: Path
    charts_dir: Path
    data_source: str


def verify_pipeline(
    provider: str = "mock",
    *,
    data_source: str = "synthetic",
    hf_target: int = 100,
    hf_fetch_limit: int = 5_000,
    hf_housing_only: bool = True,
    hf_legal_areas: tuple[str, ...] | None = None,
    hf_all_areas: bool = False,
    hf_stratify_areas: bool = False,
) -> PipelineVerificationResult:
    """Run the full audit pipeline and return artefact counts and paths.

    Args:
        provider: Model provider passed to the batch runner (``mock`` or ``gemini``).
        data_source: ``synthetic`` (12 built-in cases) or ``hf`` (Hugging Face sample).
        hf_target: Number of base cases when ``data_source='hf'``.
        hf_fetch_limit: Raw HF rows to scan before filtering (hf mode only).
        hf_housing_only: When True (default), keep housing cases only.
        hf_legal_areas: Explicit domains (overrides *hf_housing_only*).
        hf_all_areas: Include all classifiable domains from the HF sample.
        hf_stratify_areas: Balance cases across requested legal areas.

    Returns:
        :class:`PipelineVerificationResult` with counts and output paths.
    """
    from benchassist.audit_metrics import run_counterfactual_audit
    from benchassist.data_generation import (
        create_base_cases,
        create_counterfactual_cases,
        save_base_cases_csv,
        save_base_cases_jsonl,
        save_counterfactual_cases_csv,
        save_counterfactual_cases_jsonl,
    )
    from benchassist.report import generate_audit_report
    from benchassist.run_batch import run_model_batch

    os.environ["MODEL_PROVIDER"] = provider
    get_settings.cache_clear()
    settings = get_settings()

    processed_dir = settings.DATA_DIR / "processed"
    audit_dir = settings.DATA_DIR / "audit"
    outputs_dir = settings.RESULTS_DIR / "outputs"
    tables_dir = settings.RESULTS_DIR / "tables"
    report_dir = settings.RESULTS_DIR / "report"
    charts_dir = settings.RESULTS_DIR / "charts"

    logger.info("Step 1/5 — Generating base cases (source=%s)", data_source)
    if data_source == "hf":
        from benchassist.israeli_data import build_base_cases_from_legal_training_il

        housing_only = hf_housing_only and not hf_all_areas and hf_legal_areas is None
        logger.info(
            "  Loading Hugging Face data (target=%d, fetch=%d, housing_only=%s)…",
            hf_target,
            hf_fetch_limit,
            housing_only,
        )
        if hf_legal_areas:
            logger.info("  Legal areas: %s", ", ".join(hf_legal_areas))
        elif hf_all_areas:
            logger.info("  Legal areas: all classifiable domains")
        base_cases = build_base_cases_from_legal_training_il(
            target_count=hf_target,
            fetch_limit=hf_fetch_limit,
            housing_only=housing_only,
            legal_areas=hf_legal_areas,
            stratify_by_area=hf_stratify_areas,
        )
    else:
        base_cases = create_base_cases()

    save_base_cases_csv(base_cases, processed_dir / "base_cases.csv")
    save_base_cases_jsonl(base_cases, processed_dir / "base_cases.jsonl")
    logger.info("  ✓ %d base cases", len(base_cases))

    logger.info("Step 2/5 — Generating counterfactual cases")
    counterfactual_cases = create_counterfactual_cases(base_cases)
    save_counterfactual_cases_csv(
        counterfactual_cases, audit_dir / "counterfactual_cases.csv"
    )
    save_counterfactual_cases_jsonl(
        counterfactual_cases, audit_dir / "counterfactual_cases.jsonl"
    )
    logger.info("  ✓ %d counterfactual cases", len(counterfactual_cases))

    logger.info("Step 3/5 — Running model batch (provider=%s)", provider)
    records = run_model_batch(provider=provider, output_dir=outputs_dir)
    logger.info("  ✓ %d model outputs", len(records))

    logger.info("Step 4/5 — Computing audit metrics")
    table_paths = run_counterfactual_audit(
        model_outputs_path=outputs_dir / "model_outputs.csv",
        tables_dir=tables_dir,
    )
    logger.info("  ✓ Tables written under %s", tables_dir)

    logger.info("Step 5/5 — Generating audit report")
    report_path = generate_audit_report(
        report_dir=report_dir,
        tables_dir=tables_dir,
        charts_dir=charts_dir,
        outputs_path=outputs_dir / "model_outputs.csv",
    )
    logger.info("  ✓ Report: %s", report_path)

    return PipelineVerificationResult(
        base_case_count=len(base_cases),
        counterfactual_count=len(counterfactual_cases),
        model_output_count=len(records),
        group_summary_path=table_paths["group_summary"],
        audit_report_path=report_path,
        charts_dir=charts_dir,
        data_source=data_source,
    )


def _print_summary(result: PipelineVerificationResult) -> None:
    print("\n" + "=" * 50)
    print("  Pipeline verification complete")
    print("=" * 50)
    print(f"  Data source:             {result.data_source}")
    print(f"  Base cases:              {result.base_case_count}")
    print(f"  Counterfactual cases:      {result.counterfactual_count}")
    print(f"  Model outputs:             {result.model_output_count}")
    print(f"  group_summary.csv:         {result.group_summary_path}")
    print(f"  audit_report.md:           {result.audit_report_path}")
    print(f"  Charts directory:          {result.charts_dir}")
    print("=" * 50)
    print("\n  Dashboard:  streamlit run app.py\n")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for ``python -m benchassist.verify_pipeline``."""
    parser = argparse.ArgumentParser(description="Run the full BenchAssist-IL audit pipeline.")
    parser.add_argument(
        "--provider",
        default="mock",
        choices=["mock", "gemini"],
        help="Model provider (default: mock).",
    )
    parser.add_argument(
        "--data-source",
        default="synthetic",
        choices=["synthetic", "hf"],
        help="Base cases: built-in synthetic (12) or Hugging Face sample (hf).",
    )
    parser.add_argument(
        "--hf-target",
        type=int,
        default=50,
        help="Number of HF base cases when --data-source=hf (default: 50).",
    )
    parser.add_argument(
        "--hf-fetch",
        type=int,
        default=1_000,
        help="Raw HF rows to scan when --data-source=hf (default: 1000).",
    )
    parser.add_argument(
        "--hf-all-areas",
        action="store_true",
        help="Include all classifiable legal domains from HF (not housing-only).",
    )
    parser.add_argument(
        "--hf-legal-areas",
        default=None,
        metavar="AREAS",
        help="Comma-separated HF domains, e.g. housing,labor,family,criminal.",
    )
    parser.add_argument(
        "--hf-stratify-areas",
        action="store_true",
        help="Balance HF base cases across selected legal areas.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    from benchassist.israeli_data import parse_legal_areas_arg

    try:
        result = verify_pipeline(
            provider=args.provider,
            data_source=args.data_source,
            hf_target=args.hf_target,
            hf_fetch_limit=args.hf_fetch,
            hf_housing_only=not args.hf_all_areas,
            hf_legal_areas=parse_legal_areas_arg(args.hf_legal_areas),
            hf_all_areas=args.hf_all_areas,
            hf_stratify_areas=args.hf_stratify_areas,
        )
    except ImportError as exc:
        print(f"\n✗ {exc}", file=sys.stderr)
        if args.data_source == "hf":
            print("  Install with: pip install -e '.[datasets]'", file=sys.stderr)
        return 1
    except Exception as exc:
        logger.exception("Pipeline verification failed")
        print(f"\n✗ Verification failed: {exc}", file=sys.stderr)
        return 1

    _print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
