"""Fast concurrent Gemini runner for detention audit.

Uses asyncio + ThreadPoolExecutor to send up to CONCURRENCY requests
in parallel, reducing total run time from ~3 hours to ~15 minutes.
Fully compatible with the existing sequential runner's output format.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
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

CONCURRENCY = 20  # Max parallel requests


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl_sync(path: Path, record: dict[str, Any], lock: asyncio.Lock | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


async def _process_one(
    row: dict[str, Any],
    prompt_mode: str,
    config: DetentionGeminiConfig,
    client: Any,
    semaphore: asyncio.Semaphore,
    executor: ThreadPoolExecutor,
    stats: dict[str, int],
    lock: asyncio.Lock,
) -> None:
    """Process a single request with concurrency control."""
    rk = request_key(row, prompt_mode)
    case_text = str(row.get("prompt_input") or row.get("input_text") or "")
    bundle = build_detention_prompt(
        case_text,
        prompt_mode=prompt_mode,
        case_id=str(row.get("case_id", "")),
        schema_version=config.schema_version,
    )

    async with semaphore:
        loop = asyncio.get_event_loop()

        raw_text = ""
        parse_status = "error"
        parse_error: str | None = None
        parsed: dict[str, Any] | None = None
        parse_meta: dict[str, Any] = {}

        try:
            raw_text = await loop.run_in_executor(
                executor,
                lambda: client.generate(bundle.messages, temperature=config.temperature),
            )
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
                async with lock:
                    stats["parse_success"] += 1
        except Exception as exc:
            parse_error = str(exc)
            async with lock:
                stats["parse_errors"] += 1
            _append_jsonl_sync(
                config.parse_errors_path,
                {
                    "timestamp": _utc_now(),
                    "request_key": rk,
                    "case_id": row.get("case_id"),
                    "variant_id": row.get("variant_id"),
                    "prompt_mode": prompt_mode,
                    "error": parse_error,
                },
            )

        # Write raw response
        _append_jsonl_sync(
            config.raw_responses_path,
            {
                "request_key": rk,
                "timestamp": _utc_now(),
                "case_id": row.get("case_id"),
                "variant_id": row.get("variant_id"),
                "prompt_mode": prompt_mode,
                "raw_response": raw_text,
            },
        )

        # Write parsed output
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

        _append_jsonl_sync(config.parsed_outputs_path, out_record)

        async with lock:
            stats["completed"] += 1
            total = stats["total_planned"]
            done = stats["completed"] + stats["skipped_resume"]
            if stats["completed"] % 50 == 0 or stats["completed"] == total:
                elapsed = time.time() - stats["_start_time"]
                rate = stats["completed"] / elapsed if elapsed > 0 else 0
                remaining = (total - done) / rate if rate > 0 else 0
                print(
                    f"  [{done}/{total}] "
                    f"{stats['completed']} completed, "
                    f"{stats['parse_errors']} errors, "
                    f"{rate:.1f} req/s, "
                    f"~{remaining/60:.1f}min remaining",
                    flush=True,
                )


async def run_fast(config: DetentionGeminiConfig, *, resume: bool = False) -> dict[str, Any]:
    """Run the Gemini audit with concurrent requests."""
    dry = load_dry_run_manifest(config)
    if not dry.get("checks_passed"):
        raise RuntimeError("Dry-run checks_passed=false")

    if config.selected_inputs_path.exists():
        rows = []
        for line in config.selected_inputs_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    else:
        rows = select_pilot_rows(config)
        write_jsonl(config.selected_inputs_path, rows)

    completed = load_completed_keys(config.parsed_outputs_path) if resume else set()

    from benchassist.model_client import GeminiModelClient
    client = GeminiModelClient(model_name=config.model, temperature=config.temperature)

    # Build work items
    work: list[tuple[dict, str]] = []
    skipped = 0
    for prompt_mode in config.prompt_modes:
        for row in rows:
            rk = request_key(row, prompt_mode)
            if rk in completed:
                skipped += 1
                continue
            work.append((row, prompt_mode))

    total_planned = len(work) + skipped
    print(f"Total planned: {total_planned}, already done: {skipped}, remaining: {len(work)}")
    print(f"Concurrency: {CONCURRENCY} parallel requests")
    print(flush=True)

    stats = {
        "started_at": _utc_now(),
        "total_planned": total_planned,
        "completed": 0,
        "skipped_resume": skipped,
        "parse_success": 0,
        "parse_errors": 0,
        "_start_time": time.time(),
    }

    semaphore = asyncio.Semaphore(CONCURRENCY)
    lock = asyncio.Lock()

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        tasks = [
            _process_one(row, pm, config, client, semaphore, executor, stats, lock)
            for row, pm in work
        ]
        await asyncio.gather(*tasks)

    stats["finished_at"] = _utc_now()
    stats["parse_success_rate"] = stats["parse_success"] / max(stats["completed"], 1)
    del stats["_start_time"]

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
        "caution": "Audit signals only -- not proof of unlawful discrimination. Requires human legal review.",
    }
    config.run_manifest_path.write_text(json.dumps(run_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDone! {stats['completed']} completed, {stats['parse_errors']} errors, "
          f"parse success rate: {stats['parse_success_rate']:.1%}")
    return run_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Fast concurrent Gemini detention runner")
    parser.add_argument("--config", required=True, help="YAML config path")
    parser.add_argument("--resume", action="store_true", help="Resume from partial run")
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY, help="Max parallel requests")
    args = parser.parse_args()

    config = load_detention_gemini_config(Path(args.config))

    # Override module-level concurrency
    import benchassist.detention_gemini_fast as _self
    _self.CONCURRENCY = args.concurrency

    asyncio.run(run_fast(config, resume=args.resume))


if __name__ == "__main__":
    main()
