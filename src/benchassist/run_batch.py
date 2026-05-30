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
from benchassist.output_naming import (
    build_run_group_id,
    resolve_model_output_basename,
)
from benchassist.schemas import CaseSummary, CounterfactualCase, CounterfactualPair

app = typer.Typer(
    name="benchassist",
    help="BenchAssist-IL: Israeli judicial decision-support assistant audit toolkit CLI.",
    add_completion=False,
    invoke_without_command=True,
)

logger = logging.getLogger(__name__)

_PARSED_OUTPUT_FIELDS_V1 = (
    "legal_area",
    "urgency",
    "recommended_direction",
    "recommended_action",
    "reasoning",
    "evidence_needed",
    "confidence",
    "limitations",
)

_PARSED_OUTPUT_FIELDS_V2 = (
    "legal_area",
    "urgency",
    "recommended_action_type",
    "remedy_strength_score",
    "evidence_burden_level",
    "party_credibility_framing",
    "rights_orientation",
    "procedural_posture",
    "reasoning_text",
    "evidence_needed",
    "risk_flags",
    "confidence",
    "limitations",
)

_PARSED_OUTPUT_FIELDS_V3 = _PARSED_OUTPUT_FIELDS_V2 + (
    "cited_source_ids",
    "source_usage_summary",
    "unsupported_legal_claims",
    "legal_hallucination_risk",
)

# Backward-compatible alias
_PARSED_OUTPUT_FIELDS = _PARSED_OUTPUT_FIELDS_V1


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
    model_name: str | None = None,
) -> None:
    """Apply CLI overrides to environment variables and refresh settings cache."""
    if provider is not None:
        os.environ["MODEL_PROVIDER"] = provider
    if temperature is not None:
        os.environ["TEMPERATURE"] = str(temperature)
    if model_name is not None:
        os.environ["MODEL_NAME"] = model_name
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


def _schema_fields(schema_version: str) -> tuple[str, ...]:
    version = schema_version.strip().lower()
    if version == "v3":
        return _PARSED_OUTPUT_FIELDS_V3
    if version == "v2":
        return _PARSED_OUTPUT_FIELDS_V2
    return _PARSED_OUTPUT_FIELDS_V1


def _empty_parsed_fields(schema_version: str = "v1") -> dict[str, None]:
    fields = _schema_fields(schema_version)
    empty: dict[str, None] = {"case_summary": None}
    empty.update({field: None for field in fields})
    return empty


def _build_run_record(
    case: CounterfactualCase,
    *,
    raw_output: str,
    parsed: Any,
    parse_error: str | None,
    provider: str,
    model_name: str,
    temperature: float,
    run_group_id: str,
    timestamp: str,
    schema_version: str = "v1",
    prompt_mode: str = "baseline",
    repetition_index: int = 1,
    blinded_input_text: str = "",
    blinding_metadata: dict | None = None,
    retrieved_source_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Flatten a model run into a serialisable output row."""
    from benchassist.schemas import BenchMemoOutputV2, BenchMemoOutputV3

    record: dict[str, Any] = {
        "run_id": str(uuid.uuid4()),
        "run_group_id": run_group_id,
        "case_id": case.case_id,
        "variant_id": case.variant_id,
        "variant_type": case.variant_type,
        "demographic_cue": case.demographic_cue,
        "language": case.language,
        "input_text": case.input_text,
        "blinded_input_text": blinded_input_text or case.input_text,
        "blinding_metadata": json.dumps(blinding_metadata or {}, ensure_ascii=False),
        "raw_output": raw_output,
        "parse_error": parse_error,
        "provider": provider,
        "model_name": model_name,
        "temperature": temperature,
        "timestamp": timestamp,
        "schema_version": schema_version,
        "prompt_mode": prompt_mode,
        "repetition_index": repetition_index,
        "retrieved_source_ids": json.dumps(
            retrieved_source_ids or [], ensure_ascii=False
        ),
    }
    parsed_fields = _schema_fields(schema_version)
    if parsed is not None:
        record["case_summary"] = getattr(parsed, "case_summary", None)
        for field in parsed_fields:
            value = getattr(parsed, field, None)
            if field in {"evidence_needed", "risk_flags", "cited_source_ids", "unsupported_legal_claims"}:
                if isinstance(value, list):
                    value = json.dumps(value, ensure_ascii=False)
            record[field] = value
    else:
        record.update(_empty_parsed_fields(schema_version))
    if isinstance(parsed, (BenchMemoOutputV2, BenchMemoOutputV3)):
        record["reasoning"] = parsed.reasoning_text
        record["recommended_direction"] = parsed.recommended_action_type
        record["recommended_action"] = parsed.recommended_action_type

    # Dataset layer metadata (preserved for real-case-inspired runs)
    meta_fields = (
        "dataset_mode",
        "source_type",
        "source_dataset",
        "source_id",
        "source_domain",
        "normalized_domain",
        "source_license",
        "is_synthetic",
        "is_real_case_inspired",
        "counterfactual_strength",
        "use_for_strict_bias_rates",
        "use_for_reliability_audit",
        "legal_area",
        "license_note",
        "attribution_note",
        "source_note",
    )
    for field in meta_fields:
        if hasattr(case, field):
            val = getattr(case, field)
            if val in (None, ""):
                continue
            existing = record.get(field)
            if existing not in (None, "") and field in parsed_fields:
                continue
            record[field] = val
    return record


def _save_model_outputs(
    records: list[dict[str, Any]],
    output_dir: Path,
    *,
    basename: str = "model_outputs",
) -> tuple[Path, Path]:
    """Write batch results to JSONL and CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / f"{basename}.jsonl"
    csv_path = output_dir / f"{basename}.csv"

    with open(jsonl_path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    df = pd.DataFrame(records)
    for list_column in (
        "evidence_needed",
        "risk_flags",
        "cited_source_ids",
        "unsupported_legal_claims",
        "retrieved_source_ids",
    ):
        if list_column in df.columns:
            df[list_column] = df[list_column].apply(
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
    model_name: str | None = None,
    schema_version: str = "v1",
    prompt_mode: str = "baseline",
    output_prefix: str | None = None,
    repetitions: int = 1,
    mock_unstable: bool = False,
    top_k_sources: int = 5,
    input_cases: Path | None = None,
) -> list[dict[str, Any]]:
    """Run counterfactual cases through the model and save structured outputs.

    Ensures base and counterfactual datasets exist, loads audit cases, invokes
    the configured model client, parses responses, and writes output CSV/JSONL.

    Args:
        provider: ``mock``, ``gemini``, or ``openai``.
        limit: Optional cap on the number of cases processed.
        output_dir: Directory for output files (default: ``results/outputs``).
        temperature: Optional sampling temperature override.
        model_name: Optional model name override for the provider.
        schema_version: ``v1`` (default), ``v2``, or ``v3`` (requires grounded mode).
        prompt_mode: ``baseline``, ``fairness_aware``, ``demographic_blind``, or ``grounded``.
        top_k_sources: Sources to retrieve for grounded mode (default 5).
        output_prefix: Optional basename override for output files.
        repetitions: Number of repeated runs per input case (default 1).
        mock_unstable: Simulate deterministic mock variation across repetitions.
        input_cases: Optional CSV/JSONL of cases (synthetic or real-case-inspired).

    Returns:
        List of output row dicts written to disk.
    """
    from benchassist.data_generation import (
        ensure_base_case_files,
        ensure_counterfactual_case_files,
        load_cases_from_path,
        load_counterfactual_cases,
    )
    from benchassist.model_client import generate_with_retry, get_model_client
    from benchassist.prompt_builder import build_prompt_bundle

    _apply_cli_env_overrides(
        provider=provider,
        temperature=temperature,
        model_name=model_name,
    )
    settings = get_settings()

    if input_cases is not None:
        cases = load_cases_from_path(input_cases)
    else:
        ensure_base_case_files()
        ensure_counterfactual_case_files()
        cases = load_counterfactual_cases()
    if limit is not None:
        cases = cases[:limit]

    resolved_provider = provider.strip().lower()
    resolved_schema = schema_version.strip().lower()
    resolved_prompt_mode = prompt_mode.strip().lower()
    run_repetitions = max(1, repetitions)
    resolved_temperature = (
        settings.TEMPERATURE if temperature is None else temperature
    )
    if resolved_provider == "mock":
        resolved_model_name = model_name or "mock-benchassist"
    elif resolved_provider == "gemini":
        resolved_model_name = model_name or settings.MODEL_NAME
        if resolved_model_name == "mock-benchassist":
            resolved_model_name = "gemini-2.5-flash-lite"
    elif resolved_provider == "openai":
        resolved_model_name = model_name or settings.MODEL_NAME
        if resolved_model_name == "mock-benchassist":
            resolved_model_name = "gpt-4o-mini"
    else:
        resolved_model_name = model_name or settings.MODEL_NAME

    client = get_model_client(
        provider=resolved_provider,
        model_name=resolved_model_name,
        schema_version=resolved_schema,
        prompt_mode=resolved_prompt_mode,
        mock_unstable=mock_unstable,
        temperature=resolved_temperature,
    )
    if hasattr(client, "model_name"):
        resolved_model_name = client.model_name

    run_started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    run_group_id = build_run_group_id(
        model_name=resolved_model_name,
        schema_version=resolved_schema,
        prompt_mode=resolved_prompt_mode,
        timestamp=run_started_at,
    )

    out_dir = output_dir or _outputs_dir()
    basename = resolve_model_output_basename(
        provider=resolved_provider,
        model_name=resolved_model_name,
        schema_version=resolved_schema,
        prompt_mode=resolved_prompt_mode,
        output_prefix=output_prefix,
    )

    import time

    records: list[dict[str, Any]] = []
    gemini_pacing_s = 4.0 if resolved_provider == "gemini" else 0.0
    for case in tqdm(cases, desc="Model batch"):
        prompt_bundle = build_prompt_bundle(
            case,
            schema_version=resolved_schema,
            prompt_mode=resolved_prompt_mode,
            top_k_sources=top_k_sources,
        )
        messages = prompt_bundle.messages
        for repetition_index in range(1, run_repetitions + 1):
            if hasattr(client, "set_repetition_index"):
                client.set_repetition_index(repetition_index)
            try:
                raw_output, parsed, parse_error = generate_with_retry(client, messages)
            except Exception as exc:
                logger.error(
                    "Model call failed for %s (rep %d): %s",
                    case.variant_id,
                    repetition_index,
                    exc,
                )
                raw_output, parsed, parse_error = "", None, str(exc)
            timestamp = datetime.now(timezone.utc).isoformat()
            records.append(
                _build_run_record(
                    case,
                    raw_output=raw_output,
                    parsed=parsed,
                    parse_error=parse_error,
                    provider=resolved_provider,
                    model_name=resolved_model_name,
                    temperature=resolved_temperature,
                    run_group_id=run_group_id,
                    timestamp=timestamp,
                    schema_version=resolved_schema,
                    prompt_mode=resolved_prompt_mode,
                    repetition_index=repetition_index,
                    blinded_input_text=prompt_bundle.blinded_input_text,
                    blinding_metadata=prompt_bundle.blinding_metadata,
                    retrieved_source_ids=list(prompt_bundle.retrieved_source_ids),
                )
            )
            if gemini_pacing_s:
                time.sleep(gemini_pacing_s)

    jsonl_path, csv_path = _save_model_outputs(
        records, out_dir, basename=basename
    )
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
        help="Model provider: mock, gemini, or openai.",
    ),
    model_name: Optional[str] = typer.Option(
        None,
        "--model-name",
        help="Provider model name override (e.g. gemini-2.5-flash-lite).",
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
    schema_version: str = typer.Option(
        "v1",
        "--schema-version",
        help="Output schema version: v1 (default) or v2.",
    ),
    prompt_mode: str = typer.Option(
        "baseline",
        "--prompt-mode",
        help="Prompt mode: baseline (default), fairness_aware, or demographic_blind (requires v2).",
    ),
    output_prefix: Optional[str] = typer.Option(
        None,
        "--output-prefix",
        help="Override output file basename (default derives from schema/prompt mode).",
    ),
    repetitions: int = typer.Option(
        1,
        "--repetitions",
        min=1,
        help="Number of repeated model runs per input case (default: 1).",
    ),
    mock_unstable: bool = typer.Option(
        False,
        "--mock-unstable",
        help="Simulate small deterministic mock output variation across repetitions.",
    ),
    top_k_sources: int = typer.Option(
        5,
        "--top-k-sources",
        min=1,
        help="Number of toy legal sources to retrieve for grounded mode.",
    ),
    input_cases: Optional[Path] = typer.Option(
        None,
        "--input-cases",
        help="Optional CSV/JSONL input cases file (synthetic or real-case-inspired).",
    ),
) -> None:
    """Run the counterfactual model batch (default when no sub-command is given)."""
    if ctx.invoked_subcommand is not None:
        return

    _setup_logging()
    allowed_providers = {"mock", "gemini", "openai"}
    if provider not in allowed_providers:
        typer.echo(
            f"✗ Unknown provider {provider!r}. Use one of: "
            f"{', '.join(sorted(allowed_providers))}.",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        from benchassist.prompt_builder import _resolve_schema_and_prompt

        _resolve_schema_and_prompt(schema_version, prompt_mode)
        basename = resolve_model_output_basename(
            provider=provider,
            model_name=(
                model_name
                if model_name
                else (
                    "mock-benchassist"
                    if provider == "mock"
                    else get_settings().MODEL_NAME
                )
            ),
            schema_version=schema_version,
            prompt_mode=prompt_mode,
            output_prefix=output_prefix,
        )
    except ValueError as exc:
        typer.echo(f"✗ {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"Running model batch (provider={provider}, model={model_name or 'default'}, "
        f"schema={schema_version}, prompt_mode={prompt_mode}, "
        f"repetitions={repetitions}, limit={limit or 'all'}) …"
    )
    records = run_model_batch(
        provider=provider,
        limit=limit,
        output_dir=output_dir,
        temperature=temperature,
        model_name=model_name,
        schema_version=schema_version,
        prompt_mode=prompt_mode,
        output_prefix=output_prefix,
        repetitions=repetitions,
        mock_unstable=mock_unstable,
        top_k_sources=top_k_sources,
        input_cases=input_cases,
    )
    resolved_out = output_dir or _outputs_dir()
    typer.echo(f"✓ {len(records)} records written:")
    typer.echo(f"  → {resolved_out / f'{basename}.jsonl'}")
    typer.echo(f"  → {resolved_out / f'{basename}.csv'}")


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


@app.command("audit-metrics")
def audit_metrics(
    version: str = typer.Option(
        "v1",
        "--version",
        "-V",
        help="Audit metrics version: v1 (default) or v2.",
    ),
    input_path: Optional[Path] = typer.Option(
        None,
        "--input",
        "-i",
        help="Path to model_outputs.csv or model_outputs.jsonl.",
    ),
    tables_dir: Optional[Path] = typer.Option(
        None,
        "--tables-dir",
        help="Directory for output tables (default: results/tables).",
    ),
    output_suffix: Optional[str] = typer.Option(
        None,
        "--output-suffix",
        help="Optional suffix for V2 output table filenames (e.g. baseline, fairness_aware).",
    ),
) -> None:
    """Compute counterfactual audit metrics (v1 or v2 legal-framing metrics)."""
    _setup_logging()
    settings = get_settings()
    resolved_input = input_path or (_outputs_dir() / "model_outputs.csv")
    resolved_tables = tables_dir or (_tables_dir())

    if not resolved_input.exists():
        typer.echo(f"✗ Model outputs not found: {resolved_input}", err=True)
        raise typer.Exit(code=1)

    version_normalized = version.strip().lower()
    if version_normalized == "v2":
        from benchassist.audit_metrics_v2 import run_v2_counterfactual_audit

        result = run_v2_counterfactual_audit(
            model_outputs_path=resolved_input,
            tables_dir=resolved_tables,
            output_suffix=output_suffix,
        )
        typer.echo("✓ V2 audit tables saved:")
        for name, path in result["tables"].items():
            typer.echo(f"  → {path}")
        typer.echo("\n✓ V2 charts saved:")
        for name, path in result["charts"].items():
            typer.echo(f"  → {path}")
        typer.echo(
            f"\n  Outputs loaded:       {result['outputs_loaded']}\n"
            f"  Pairwise comparisons: {result['pairwise_rows']}\n"
            f"  Flagged cases:        {result['flagged_rows']}"
        )
        return

    if version_normalized != "v1":
        typer.echo(f"✗ Unknown version {version!r}. Use 'v1' or 'v2'.", err=True)
        raise typer.Exit(code=1)

    from benchassist.audit_metrics import run_counterfactual_audit

    paths = run_counterfactual_audit(
        model_outputs_path=resolved_input,
        tables_dir=resolved_tables,
    )
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
