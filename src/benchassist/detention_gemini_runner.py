"""Shared safe Gemini runner for detention pilot and full audit."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from benchassist.dataset_modes import exclude_from_strict_bias
from benchassist.detention_gemini_config import (
    DetentionGeminiConfig,
    load_completed_keys,
    request_key,
    select_pilot_rows,
    write_jsonl,
)
from benchassist.detention_prompting import build_detention_prompt
from benchassist.detention_schema import parse_detention_memo_with_meta, validate_detention_output_row


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _safe_request_log(row: dict[str, Any], prompt_mode: str, *, model: str) -> dict[str, Any]:
    return {
        "timestamp": _utc_now(),
        "request_key": request_key(row, prompt_mode),
        "case_id": row.get("case_id"),
        "variant_id": row.get("variant_id"),
        "prompt_mode": prompt_mode,
        "model": model,
        "dataset_mode": row.get("dataset_mode"),
        "exclude_from_strict_bias_rates": exclude_from_strict_bias(row),
        "use_for_strict_bias_rates": not exclude_from_strict_bias(row),
    }


def load_dry_run_manifest(config: DetentionGeminiConfig) -> dict[str, Any]:
    if not config.dry_run_manifest_path.exists():
        raise FileNotFoundError(
            f"Dry-run manifest missing: {config.dry_run_manifest_path}. "
            "Run dry-run planner with --dry-run before executing."
        )
    return json.loads(config.dry_run_manifest_path.read_text(encoding="utf-8"))


def run_detention_gemini_audit(config: DetentionGeminiConfig, *, resume: bool = False) -> dict[str, Any]:
    """Run Gemini detention audit (pilot or full) with resume support."""
    dry = load_dry_run_manifest(config)
    if not dry.get("checks_passed"):
        raise RuntimeError("Dry-run manifest reports checks_passed=false — fix issues before execution.")

    if config.parsed_outputs_path.exists() and config.parsed_outputs_path.stat().st_size > 0:
        if not resume and not config.safety.overwrite_existing:
            raise RuntimeError(
                f"Refusing to overwrite existing outputs at {config.parsed_outputs_path}. Use --resume."
            )

    if config.selected_inputs_path.exists():
        rows = []
        for line in config.selected_inputs_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    else:
        rows = select_pilot_rows(config)
        write_jsonl(config.selected_inputs_path, rows)

    completed = load_completed_keys(config.parsed_outputs_path) if resume else set()

    try:
        from benchassist.model_client import GeminiModelClient
    except ImportError as exc:
        raise ImportError("google-genai required. pip install google-genai") from exc

    client = GeminiModelClient(model_name=config.model, temperature=config.temperature)
    delay = config.rate_limit.min_delay_seconds

    stats = {
        "started_at": _utc_now(),
        "total_planned": len(rows) * len(config.prompt_modes),
        "completed": 0,
        "skipped_resume": 0,
        "parse_success": 0,
        "parse_errors": 0,
    }

    for prompt_mode in config.prompt_modes:
        for row in rows:
            rk = request_key(row, prompt_mode)
            if rk in completed:
                stats["skipped_resume"] += 1
                continue

            case_text = str(row.get("prompt_input") or row.get("input_text") or "")
            bundle = build_detention_prompt(
                case_text,
                prompt_mode=prompt_mode,
                case_id=str(row.get("case_id", "")),
                schema_version=config.schema_version,
            )

            _append_jsonl(config.request_log_path, _safe_request_log(row, prompt_mode, model=config.model))

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
                    stats["parse_success"] += 1
            except Exception as exc:
                parse_error = str(exc)
                stats["parse_errors"] += 1
                _append_jsonl(
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

            _append_jsonl(
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

            _append_jsonl(config.parsed_outputs_path, out_record)
            stats["completed"] += 1
            completed.add(rk)

            parse_rate = stats["parse_errors"] / max(stats["completed"], 1)
            if (
                not resume
                and parse_rate > config.safety.stop_on_parse_error_rate_above
                and stats["completed"] >= 3
            ):
                stats["stopped_early"] = True
                stats["stop_reason"] = (
                    f"Parse error rate {parse_rate:.1%} exceeds threshold "
                    f"{config.safety.stop_on_parse_error_rate_above:.0%}"
                )
                break

            time.sleep(delay)
        if stats.get("stopped_early"):
            break

    stats["finished_at"] = _utc_now()
    stats["parse_success_rate"] = stats["parse_success"] / max(stats["completed"], 1)

    label = "Full" if config.is_full_run else "Pilot"
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
            "request_log_safe": str(config.request_log_path),
        },
        "methodology": {
            "strict_fairness_source": config.methodology.strict_fairness_source,
            "real_cases_in_strict_rates": config.methodology.real_cases_in_strict_rates,
        },
        "caution": (
            f"{label} audit signals only — not proof of unlawful discrimination. "
            "Requires human legal review."
        ),
    }
    config.run_manifest_path.write_text(json.dumps(run_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return run_manifest
