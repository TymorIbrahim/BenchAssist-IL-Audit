"""Fast concurrent Gemini runner for detention audit — uses asyncio + ThreadPoolExecutor."""

from __future__ import annotations

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchassist.dataset_modes import exclude_from_strict_bias
from benchassist.detention_gemini_config import (
    DetentionGeminiConfig,
    load_completed_keys,
    load_detention_gemini_config,
    request_key,
    select_pilot_rows,
    write_jsonl,
)
from benchassist.detention_gemini_runner import load_dry_run_manifest
from benchassist.detention_prompting import build_detention_prompt
from benchassist.detention_schema import parse_detention_memo_with_meta, validate_detention_output_row


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl_safe(path: Path, record: dict[str, Any], lock: asyncio.Lock) -> None:
    """Thread-safe append to JSONL file."""
    import threading
    path.parent.mkdir(parents=True, exist_ok=True)
    # Use a simple file-level write (append mode is atomic on most OS)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _process_single_request(
    client: Any,
    row: dict[str, Any],
    prompt_mode: str,
    config: DetentionGeminiConfig,
) -> dict[str, Any]:
    """Process a single Gemini API request (runs in thread pool)."""
    rk = request_key(row, prompt_mode)
    case_text = str(row.get("prompt_input") or row.get("input_text") or "")
    bundle = build_detention_prompt(
        case_text,
        prompt_mode=prompt_mode,
        case_id=str(row.get("case_id", "")),
        schema_version=config.schema_version,
    )

    raw_text = ""
    parse_status = "error"
    parse_error: str | None = None
    parsed: dict[str, Any] | None = None
    parse_meta: dict[str, Any] = {}

    try:
        raw_text = client.generate(bundle.messages, temperature=config.temperature)
        memo, parse_meta = parse_detention_memo_with_meta(raw_text, schema_version=config.schema_version)
        parsed = memo.model_dump()
        check_row = {**row, **parsed, "schema_version": config.schema_version}
        if parse_meta.get("validation_warnings"):
            check_row["validation_warnings"] = parse_meta["validation_warnings"]
        row_result = validate_detention_output_row(check_row, schema_version=config.schema_version)
        if row_result["hard_errors"] or row_result["parse_errors"]:
            parse_status = "schema_error"
            parse_error = "; ".join(row_result["hard_errors"] + row_result["parse_errors"])
        else:
            parse_status = "success"
    except Exception as exc:
        parse_error = str(exc)

    out_record: dict[str, Any] = {
        **row,
        "request_key": rk,
        "timestamp": _utc_now(),
        "prompt_mode": prompt_mode,
        "model_name": config.model,
        "provider": config.provider,
        "use_case": config.use_case,
        "parse_status": parse_status,
        "parse_error": parse_error,
        "parsed_ok": parse_status == "success",
        "raw_output": raw_text,
        "full_prompt_sent_to_model": "\n\n".join(
            f"--- {m['role'].upper()} ---\n{m['content']}" for m in bundle.messages
        ),
        "prompt_reconstruction_status": "exact_prompt_logged",
        "schema_version": config.schema_version,
    }
    if exclude_from_strict_bias(row):
        out_record["use_for_strict_bias_rates"] = False
        out_record["exclude_from_strict_bias_rates"] = True
    if parsed:
        out_record.update(parsed)
    if parse_meta.get("raw_legal_area"):
        out_record["raw_legal_area"] = parse_meta["raw_legal_area"]
    if parse_meta.get("validation_warnings"):
        out_record["validation_warnings"] = parse_meta["validation_warnings"]

    return {
        "out_record": out_record,
        "raw_record": {
            "request_key": rk,
            "timestamp": _utc_now(),
            "case_id": row.get("case_id"),
            "variant_id": row.get("variant_id"),
            "prompt_mode": prompt_mode,
            "raw_response": raw_text,
        },
        "parse_status": parse_status,
        "parse_error": parse_error,
        "request_key": rk,
        "case_id": row.get("case_id"),
        "variant_id": row.get("variant_id"),
        "prompt_mode": prompt_mode,
    }


async def run_fast_audit(config: DetentionGeminiConfig, *, resume: bool = False, max_workers: int = 15) -> dict[str, Any]:
    """Run Gemini audit with concurrent workers."""
    dry = load_dry_run_manifest(config)
    if not dry.get("checks_passed"):
        raise RuntimeError("Dry-run manifest reports checks_passed=false")

    if config.parsed_outputs_path.exists() and config.parsed_outputs_path.stat().st_size > 0:
        if not resume and not config.safety.overwrite_existing:
            raise RuntimeError(f"Refusing to overwrite existing outputs. Use --resume.")

    # Load input rows
    if config.selected_inputs_path.exists():
        rows = []
        for line in config.selected_inputs_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    else:
        rows = select_pilot_rows(config)
        write_jsonl(config.selected_inputs_path, rows)

    completed = load_completed_keys(config.parsed_outputs_path) if resume else set()

    # Build work items
    work_items: list[tuple[dict[str, Any], str]] = []
    for prompt_mode in config.prompt_modes:
        for row in rows:
            rk = request_key(row, prompt_mode)
            if rk in completed:
                continue
            work_items.append((row, prompt_mode))

    skipped = len(rows) * len(config.prompt_modes) - len(work_items)
    total = len(work_items)
    print(f"Fast runner: {total} requests to process ({skipped} skipped/resumed), {max_workers} concurrent workers")

    from benchassist.model_client import GeminiModelClient
    client = GeminiModelClient(model_name=config.model, temperature=config.temperature)

    stats = {
        "started_at": _utc_now(),
        "total_planned": len(rows) * len(config.prompt_modes),
        "completed": 0,
        "skipped_resume": skipped,
        "parse_success": 0,
        "parse_errors": 0,
    }

    semaphore = asyncio.Semaphore(max_workers)
    lock = asyncio.Lock()
    executor = ThreadPoolExecutor(max_workers=max_workers)
    loop = asyncio.get_event_loop()
    start_time = time.time()

    async def process_one(row: dict[str, Any], prompt_mode: str, idx: int) -> None:
        async with semaphore:
            result = await loop.run_in_executor(
                executor, _process_single_request, client, row, prompt_mode, config
            )

        # Write results (file I/O)
        async with lock:
            with open(config.parsed_outputs_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(result["out_record"], ensure_ascii=False) + "\n")
            with open(config.raw_responses_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(result["raw_record"], ensure_ascii=False) + "\n")

            if result["parse_status"] == "success":
                stats["parse_success"] += 1
            else:
                stats["parse_errors"] += 1
                with open(config.parse_errors_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({
                        "timestamp": _utc_now(),
                        "request_key": result["request_key"],
                        "case_id": result["case_id"],
                        "variant_id": result["variant_id"],
                        "prompt_mode": result["prompt_mode"],
                        "error": result["parse_error"],
                    }, ensure_ascii=False) + "\n")

            stats["completed"] += 1
            done = stats["completed"]

        # Progress log every 50 requests
        if done % 50 == 0 or done == total:
            elapsed = time.time() - start_time
            rate = done / elapsed if elapsed > 0 else 0
            eta = (total - done) / rate if rate > 0 else 0
            err_rate = stats["parse_errors"] / max(done, 1)
            print(f"  [{done}/{total}] {rate:.1f} req/s | errors: {stats['parse_errors']} ({err_rate:.1%}) | ETA: {eta:.0f}s")

    # Launch all tasks
    tasks = [process_one(row, mode, i) for i, (row, mode) in enumerate(work_items)]
    await asyncio.gather(*tasks)

    executor.shutdown(wait=False)

    stats["finished_at"] = _utc_now()
    stats["parse_success_rate"] = stats["parse_success"] / max(stats["completed"], 1)
    elapsed = time.time() - start_time
    stats["elapsed_seconds"] = round(elapsed, 1)
    stats["requests_per_second"] = round(stats["completed"] / max(elapsed, 1), 2)

    run_manifest = {
        "generated_at": _utc_now(),
        "config_path": str(config.config_path),
        "dry_run_manifest": str(config.dry_run_manifest_path),
        "run_type": config.run_type,
        "schema_version": config.schema_version,
        "model": config.model,
        "prompt_modes": config.prompt_modes,
        "stats": stats,
        "outputs": {
            "parsed_outputs": str(config.parsed_outputs_path),
            "raw_responses": str(config.raw_responses_path),
            "parse_errors": str(config.parse_errors_path),
        },
        "methodology": {
            "strict_fairness_source": config.methodology.strict_fairness_source,
            "real_cases_in_strict_rates": config.methodology.real_cases_in_strict_rates,
        },
        "caution": "Audit signals only — not proof of unlawful discrimination. Requires human legal review.",
    }
    config.run_manifest_path.write_text(json.dumps(run_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nDone! {stats['completed']} requests in {elapsed:.0f}s ({stats['requests_per_second']} req/s)")
    print(f"  Parse success rate: {stats['parse_success_rate']:.1%}")
    print(f"  Outputs: {config.parsed_outputs_path}")
    return run_manifest


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Fast concurrent Gemini detention audit runner.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=15, help="Max concurrent API requests (default: 15)")
    args = parser.parse_args()

    config = load_detention_gemini_config(args.config)
    manifest = asyncio.run(run_fast_audit(config, resume=args.resume, max_workers=args.workers))

    if manifest["stats"].get("stopped_early"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
