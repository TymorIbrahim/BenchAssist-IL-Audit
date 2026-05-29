"""CLI batch runner for BenchAssist-IL.

Provides a :mod:`typer`-based command-line interface. Running without a
sub-command executes the counterfactual model batch (see :func:`run_model_batch`).

Sub-commands cover individual pipeline stages and legacy workflows.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import typer
from tqdm import tqdm

from benchassist.config import get_settings
from benchassist.schemas import CaseSummary, CounterfactualCase, CounterfactualPair

app = typer.Typer(
    name="benchassist",
    help="BenchAssist-IL: Israeli judicial decision-support assistant audit toolkit CLI.",
    add_completion=False,
    invoke_without_command=True,
)

logger = logging.getLogger(__name__)

_PARSED_OUTPUT_FIELDS = (
    "legal_area",
    "urgency",
    "recommended_direction",
    "recommended_action",
    "reasoning",
    "evidence_needed",
    "confidence",
    "limitations",
)


def _setup_logging() -> None:
    """Configure root logger from settings."""
    settings = get_settings()
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


def _apply_cli_env_overrides(
    provider: str | None = None,
    temperature: float | None = None,
) -> None:
    """Apply CLI overrides to environment variables and refresh settings cache."""
    if provider is not None:
        os.environ["MODEL_PROVIDER"] = provider
    if temperature is not None:
        os.environ["TEMPERATURE"] = str(temperature)
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Helper paths
# ---------------------------------------------------------------------------


def _processed_dir() -> Path:
    return get_settings().DATA_DIR / "processed"


def _outputs_dir() -> Path:
    return get_settings().RESULTS_DIR / "outputs"


def _tables_dir() -> Path:
    return get_settings().RESULTS_DIR / "tables"


def _report_dir() -> Path:
    return get_settings().RESULTS_DIR / "report"


def _audit_dir() -> Path:
    return get_settings().DATA_DIR / "audit"


# ---------------------------------------------------------------------------
# Model batch runner
# ---------------------------------------------------------------------------


def _empty_parsed_fields() -> dict[str, None]:
    return {field: None for field in _PARSED_OUTPUT_FIELDS}


def _build_run_record(
    case: CounterfactualCase,
    *,
    raw_output: str,
    parsed: Any,
    parse_error: str | None,
    model_name: str,
    timestamp: str,
) -> dict[str, Any]:
    """Flatten a model run into a serialisable output row."""
    record: dict[str, Any] = {
        "run_id": str(uuid.uuid4()),
        "case_id": case.case_id,
        "variant_id": case.variant_id,
        "variant_type": case.variant_type,
        "demographic_cue": case.demographic_cue,
        "language": case.language,
        "input_text": case.input_text,
        "raw_output": raw_output,
        "parse_error": parse_error,
        "model_name": model_name,
        "timestamp": timestamp,
    }
    if parsed is not None:
        for field in _PARSED_OUTPUT_FIELDS:
            record[field] = getattr(parsed, field)
    else:
        record.update(_empty_parsed_fields())
    return record


def _save_model_outputs(records: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path]:
    """Write batch results to JSONL and CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "model_outputs.jsonl"
    csv_path = output_dir / "model_outputs.csv"

    with open(jsonl_path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    df = pd.DataFrame(records)
    if "evidence_needed" in df.columns:
        df["evidence_needed"] = df["evidence_needed"].apply(
            lambda value: (
                json.dumps(value, ensure_ascii=False)
                if isinstance(value, list)
                else value
            )
        )
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    return jsonl_path, csv_path


def run_model_batch(
    provider: str = "mock",
    limit: int | None = None,
    output_dir: Path | None = None,
    temperature: float | None = None,
) -> list[dict[str, Any]]:
    """Run counterfactual cases through the model and save structured outputs.

    Ensures base and counterfactual datasets exist, loads audit cases, invokes
    the configured model client, parses responses, and writes
    ``model_outputs.jsonl`` and ``model_outputs.csv``.

    Args:
        provider: ``mock`` or ``gemini``.
        limit: Optional cap on the number of cases processed.
        output_dir: Directory for output files (default: ``results/outputs``).
        temperature: Optional sampling temperature override.

    Returns:
        List of output row dicts written to disk.
    """
    from benchassist.data_generation import (
        ensure_base_case_files,
        ensure_counterfactual_case_files,
        load_counterfactual_cases,
    )
    from benchassist.model_client import generate_with_retry, get_model_client
    from benchassist.prompt_builder import build_counterfactual_messages

    _apply_cli_env_overrides(provider=provider, temperature=temperature)
    settings = get_settings()

    ensure_base_case_files()
    ensure_counterfactual_case_files()

    cases = load_counterfactual_cases()
    if limit is not None:
        cases = cases[:limit]

    client = get_model_client(provider=provider)
    model_name = settings.MODEL_NAME
    out_dir = output_dir or _outputs_dir()

    import time

    records: list[dict[str, Any]] = []
    gemini_pacing_s = 4.0 if provider == "gemini" else 0.0
    for case in tqdm(cases, desc="Model batch"):
        messages = build_counterfactual_messages(case)
        try:
            raw_output, parsed, parse_error = generate_with_retry(client, messages)
        except Exception as exc:
            logger.error("Model call failed for %s: %s", case.variant_id, exc)
            raw_output, parsed, parse_error = "", None, str(exc)
        timestamp = datetime.now(timezone.utc).isoformat()
        records.append(
            _build_run_record(
                case,
                raw_output=raw_output,
                parsed=parsed,
                parse_error=parse_error,
                model_name=model_name,
                timestamp=timestamp,
            )
        )
        if gemini_pacing_s:
            time.sleep(gemini_pacing_s)

    jsonl_path, csv_path = _save_model_outputs(records, out_dir)
    logger.info("Wrote %d records to %s and %s", len(records), jsonl_path, csv_path)
    return records


# ---------------------------------------------------------------------------
# Default CLI (batch run)
# ---------------------------------------------------------------------------


@app.callback()
def main(
    ctx: typer.Context,
    provider: str = typer.Option(
        "mock",
        "--provider",
        help="Model provider: mock or gemini.",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Maximum number of counterfactual cases to run.",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        help="Directory for model_outputs.jsonl and model_outputs.csv.",
    ),
    temperature: Optional[float] = typer.Option(
        None,
        "--temperature",
        help="Sampling temperature override for generative models.",
    ),
) -> None:
    """Run the counterfactual model batch (default when no sub-command is given)."""
    if ctx.invoked_subcommand is not None:
        return

    _setup_logging()
    if provider not in {"mock", "gemini"}:
        typer.echo(f"✗ Unknown provider {provider!r}. Use 'mock' or 'gemini'.", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Running model batch (provider={provider}, limit={limit or 'all'}) …")
    records = run_model_batch(
        provider=provider,
        limit=limit,
        output_dir=output_dir,
        temperature=temperature,
    )
    resolved_out = output_dir or _outputs_dir()
    typer.echo(f"✓ {len(records)} records written:")
    typer.echo(f"  → {resolved_out / 'model_outputs.jsonl'}")
    typer.echo(f"  → {resolved_out / 'model_outputs.csv'}")


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------


@app.command()
def generate(
    n: int = typer.Option(10, "--n", "-n", help="Number of base cases to generate."),
) -> None:
    """Generate synthetic base cases and save to data/processed/."""
    _setup_logging()
    from benchassist.data_generation import generate_base_cases, save_cases

    typer.echo(f"Generating {n} base cases …")
    cases = generate_base_cases(n)
    out_path = _processed_dir() / "base_cases.json"
    save_cases(cases, out_path)
    typer.echo(f"✓ Saved {len(cases)} cases to {out_path}")


@app.command()
def generate_housing() -> None:
    """Generate the 12 housing base-case dataset (CSV + JSONL)."""
    _setup_logging()
    from benchassist.data_generation import (
        create_base_cases,
        save_base_cases_csv,
        save_base_cases_jsonl,
    )

    cases = create_base_cases()
    out_dir = _processed_dir()

    csv_path = out_dir / "base_cases.csv"
    jsonl_path = out_dir / "base_cases.jsonl"

    save_base_cases_csv(cases, csv_path)
    save_base_cases_jsonl(cases, jsonl_path)

    typer.echo(f"✓ {len(cases)} housing base cases saved:")
    typer.echo(f"  → {csv_path}")
    typer.echo(f"  → {jsonl_path}")


@app.command("counterfactual-cases")
def counterfactual_cases_cmd() -> None:
    """Generate housing counterfactual variants (CSV + JSONL) under data/audit/."""
    _setup_logging()
    from benchassist.data_generation import write_counterfactual_audit_files

    audit_dir = _audit_dir()
    variants = write_counterfactual_audit_files()
    typer.echo(f"✓ {len(variants)} counterfactual cases saved:")
    typer.echo(f"  → {audit_dir / 'counterfactual_cases.csv'}")
    typer.echo(f"  → {audit_dir / 'counterfactual_cases.jsonl'}")


@app.command()
def counterfactuals() -> None:
    """Load base cases, create counterfactual variants, save."""
    _setup_logging()
    from benchassist.data_generation import (
        create_counterfactual_variants,
        load_cases,
        save_cases,
    )

    base_path = _processed_dir() / "base_cases.json"
    if not base_path.exists():
        typer.echo("✗ Base cases not found. Run 'generate' first.", err=True)
        raise typer.Exit(code=1)

    cases: list[CaseSummary] = load_cases(base_path, model=CaseSummary)
    typer.echo(f"Loaded {len(cases)} base cases. Creating counterfactual variants …")
    pairs = create_counterfactual_variants(cases)
    out_path = _processed_dir() / "counterfactual_pairs.json"
    save_cases(pairs, out_path)
    typer.echo(f"✓ Saved {len(pairs)} counterfactual pairs to {out_path}")


@app.command()
def run(
    mock: bool = typer.Option(False, "--mock", help="Force mock model regardless of config."),
) -> None:
    """Run cases (and counterfactual pairs) through the model client."""
    _setup_logging()
    from benchassist.data_generation import load_cases
    from benchassist.model_client import generate_with_retry, get_model_client
    from benchassist.prompt_builder import build_messages

    settings = get_settings()
    provider = "mock" if mock else settings.MODEL_PROVIDER
    client = get_model_client(provider=provider)
    typer.echo(f"Using provider: {provider} (model: {settings.MODEL_NAME})")

    base_path = _processed_dir() / "base_cases.json"
    if not base_path.exists():
        typer.echo("✗ Base cases not found. Run 'generate' first.", err=True)
        raise typer.Exit(code=1)

    base_cases: list[CaseSummary] = load_cases(base_path, model=CaseSummary)
    base_memos: list[dict] = []
    for case in tqdm(base_cases, desc="Base cases"):
        messages = build_messages(case)
        raw, parsed, parse_error = generate_with_retry(client, messages)
        base_memos.append(
            parsed.model_dump() if parsed else {"raw_output": raw, "parse_error": parse_error}
        )

    out_base = _outputs_dir() / "base_results.json"
    out_base.parent.mkdir(parents=True, exist_ok=True)
    with open(out_base, "w", encoding="utf-8") as fh:
        json.dump(base_memos, fh, indent=2, ensure_ascii=False)
    typer.echo(f"✓ {len(base_memos)} base results → {out_base}")

    pairs_path = _processed_dir() / "counterfactual_pairs.json"
    if pairs_path.exists():
        raw_pairs: list[CounterfactualPair] = load_cases(pairs_path, model=CounterfactualPair)
        variant_memos: list[dict] = []
        paired_base_memos: list[dict] = []
        for pair in tqdm(raw_pairs, desc="Counterfactual variants"):
            raw_b, b_parsed, b_err = generate_with_retry(
                client, build_messages(pair.base)
            )
            paired_base_memos.append(
                b_parsed.model_dump()
                if b_parsed
                else {"raw_output": raw_b, "parse_error": b_err}
            )
            raw_v, v_parsed, v_err = generate_with_retry(
                client, build_messages(pair.variant)
            )
            variant_memos.append(
                v_parsed.model_dump()
                if v_parsed
                else {"raw_output": raw_v, "parse_error": v_err}
            )

        out_var = _outputs_dir() / "variant_results.json"
        out_paired_base = _outputs_dir() / "paired_base_results.json"
        with open(out_var, "w", encoding="utf-8") as fh:
            json.dump(variant_memos, fh, indent=2, ensure_ascii=False)
        with open(out_paired_base, "w", encoding="utf-8") as fh:
            json.dump(paired_base_memos, fh, indent=2, ensure_ascii=False)
        typer.echo(f"✓ {len(variant_memos)} variant results → {out_var}")
    else:
        typer.echo("ℹ No counterfactual pairs found – skipping variant run.")


@app.command()
def audit() -> None:
    """Compute counterfactual audit metrics from model_outputs.csv."""
    _setup_logging()
    from benchassist.audit_metrics import run_counterfactual_audit

    model_outputs = _outputs_dir() / "model_outputs.csv"
    if not model_outputs.exists():
        typer.echo(
            "✗ model_outputs.csv not found. Run the model batch first.", err=True
        )
        raise typer.Exit(code=1)

    paths = run_counterfactual_audit(model_outputs_path=model_outputs)
    typer.echo("✓ Audit tables saved:")
    for name, path in paths.items():
        typer.echo(f"  → {path}")

    flagged = paths["flagged_cases"]
    import pandas as pd

    flagged_count = len(pd.read_csv(flagged))
    typer.echo(f"\n  Flagged variant rows: {flagged_count}")


@app.command()
def report() -> None:
    """Generate the markdown audit report and charts."""
    _setup_logging()
    from benchassist.report import generate_audit_report

    tables_dir = _tables_dir()
    if not (tables_dir / "group_summary.csv").exists():
        typer.echo("✗ Audit tables not found. Run 'audit' first.", err=True)
        raise typer.Exit(code=1)

    report_path = generate_audit_report(report_dir=_report_dir())
    typer.echo(f"✓ Audit report: {report_path}")
    typer.echo(f"  → Charts in {get_settings().RESULTS_DIR / 'charts'}")


@app.command()
def pipeline(
    n: int = typer.Option(10, "--n", "-n", help="Number of base cases."),
    mock: bool = typer.Option(False, "--mock", help="Force mock model."),
) -> None:
    """Run the full pipeline end-to-end: generate → counterfactuals → run → audit → report."""
    _setup_logging()
    typer.echo("═" * 50)
    typer.echo("  BenchAssist-IL  ·  Full Pipeline")
    typer.echo("═" * 50)

    typer.echo("\n▶ Step 1/5 – Generating base cases")
    from benchassist.data_generation import (
        create_counterfactual_variants,
        generate_base_cases,
        save_cases,
    )

    cases = generate_base_cases(n)
    save_cases(cases, _processed_dir() / "base_cases.json")
    typer.echo(f"  ✓ {len(cases)} base cases saved")

    typer.echo("\n▶ Step 2/5 – Creating counterfactual variants")
    pairs = create_counterfactual_variants(cases)
    save_cases(pairs, _processed_dir() / "counterfactual_pairs.json")
    typer.echo(f"  ✓ {len(pairs)} pairs saved")

    typer.echo("\n▶ Step 3/5 – Running model inference")
    from benchassist.model_client import generate_with_retry, get_model_client
    from benchassist.prompt_builder import build_messages

    settings = get_settings()
    provider = "mock" if mock else settings.MODEL_PROVIDER
    client = get_model_client(provider=provider)
    typer.echo(f"  Provider: {provider} (model: {settings.MODEL_NAME})")

    base_memos = []
    for case in tqdm(cases, desc="  Base"):
        raw, parsed, parse_error = generate_with_retry(
            client, build_messages(case)
        )
        base_memos.append(
            parsed.model_dump() if parsed else {"raw_output": raw, "parse_error": parse_error}
        )
    out_base = _outputs_dir() / "base_results.json"
    out_base.parent.mkdir(parents=True, exist_ok=True)
    with open(out_base, "w", encoding="utf-8") as fh:
        json.dump(base_memos, fh, indent=2, ensure_ascii=False)

    paired_base_memos = []
    variant_memos = []
    for pair in tqdm(pairs, desc="  Pairs"):
        raw_b, b_parsed, b_err = generate_with_retry(
            client, build_messages(pair.base)
        )
        raw_v, v_parsed, v_err = generate_with_retry(
            client, build_messages(pair.variant)
        )
        paired_base_memos.append(
            b_parsed.model_dump()
            if b_parsed
            else {"raw_output": raw_b, "parse_error": b_err}
        )
        variant_memos.append(
            v_parsed.model_dump()
            if v_parsed
            else {"raw_output": raw_v, "parse_error": v_err}
        )

    for data, name in [
        (paired_base_memos, "paired_base_results.json"),
        (variant_memos, "variant_results.json"),
    ]:
        path = _outputs_dir() / name
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

    typer.echo(f"  ✓ {len(base_memos)} base + {len(variant_memos)} variant results saved")

    typer.echo("\n▶ Step 4/5 – Computing audit metrics")
    from benchassist.audit_metrics import compute_all_metrics, load_paired_results

    memo_pairs = load_paired_results(
        _outputs_dir() / "paired_base_results.json",
        _outputs_dir() / "variant_results.json",
    )
    metrics = compute_all_metrics(memo_pairs)
    tables_dir = _tables_dir()
    tables_dir.mkdir(parents=True, exist_ok=True)
    with open(tables_dir / "audit_metrics.json", "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2, ensure_ascii=False)

    rd = metrics["recommendation_divergence"]
    typer.echo(f"  ✓ Recommendation divergence: {rd['divergence_rate']:.1%}")

    typer.echo("\n▶ Step 5/5 – Generating report")
    from benchassist.audit_metrics import run_counterfactual_audit
    from benchassist.report import generate_audit_report

    run_counterfactual_audit()
    report_path = generate_audit_report(report_dir=_report_dir())
    typer.echo(f"  ✓ Report: {report_path}")

    typer.echo("\n" + "═" * 50)
    typer.echo("  Pipeline complete ✓")
    typer.echo("═" * 50)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
