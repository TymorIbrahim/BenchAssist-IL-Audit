"""Dry-run planner for detention Gemini pilot — no API calls."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchassist.config import resolve_gemini_api_key, get_settings
from benchassist.dataset_modes import exclude_from_strict_bias
from benchassist.detention_gemini_config import (
    DetentionGeminiConfig,
    estimate_prompt_chars,
    load_detention_gemini_config,
    project_root,
    select_pilot_rows,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mask_key_present() -> dict[str, Any]:
    key = resolve_gemini_api_key(get_settings())
    return {
        "api_key_present": bool(key),
        "api_key_source": (
            "GEMINI_API_KEY"
            if get_settings().GEMINI_API_KEY
            else ("GOOGLE_API_KEY" if get_settings().GOOGLE_API_KEY else None)
        ),
        "api_key_value": None,
        "note": "API key verified in environment — value never logged or printed.",
    }


def _check_output_collision(config: DetentionGeminiConfig, *, resume: bool) -> dict[str, Any]:
    final_markers = [
        config.parsed_outputs_path,
        config.run_manifest_path,
    ]
    existing = [str(p.relative_to(project_root())) for p in final_markers if p.exists() and p.stat().st_size > 0]
    if existing and not resume and not config.safety.overwrite_existing:
        return {
            "ok": False,
            "message": "Output files already exist — use --resume or choose a new output_dir. No --force overwrite.",
            "existing_files": existing,
        }
    return {"ok": True, "message": "No blocking output collision (or resume allowed).", "existing_files": existing}


def run_dry_run(
    config: DetentionGeminiConfig,
    *,
    resume: bool = False,
) -> dict[str, Any]:
    """Execute dry-run planning; write manifest and markdown report."""
    checks: list[dict[str, Any]] = []
    all_ok = True

    def add(name: str, ok: bool, detail: str, **extra: Any) -> None:
        nonlocal all_ok
        if not ok:
            all_ok = False
        checks.append({"name": name, "ok": ok, "detail": detail, **extra})

    add("use_case", config.use_case == "detention", f"use_case={config.use_case}")
    add("model", bool(config.model), f"model={config.model}")
    add(
        "model_is_target",
        config.model == "gemini-2.5-flash-lite",
        f"Expected gemini-2.5-flash-lite; got {config.model}",
    )

    key_info = _mask_key_present()
    add("api_key", key_info["api_key_present"], key_info["note"], key_info=key_info)

    add("synthetic_input", config.synthetic_input.exists(), str(config.synthetic_input))
    add("real_case_input", config.real_case_input.exists(), str(config.real_case_input))

    rows: list[dict[str, Any]] = []
    try:
        rows = select_pilot_rows(config)
        add("pilot_row_selection", len(rows) > 0, f"{len(rows)} pilot rows selected")
    except Exception as exc:
        add("pilot_row_selection", False, str(exc))

    synthetic_rows = [r for r in rows if not exclude_from_strict_bias(r) or str(r.get("dataset_mode", "")).startswith("synthetic")]
    strict_eligible = [r for r in rows if not exclude_from_strict_bias(r)]
    real_rows = [r for r in rows if exclude_from_strict_bias(r)]

    add(
        "strict_fairness_policy",
        config.metadata.get("real_cases_in_strict_rates") is False,
        "Real cases excluded from strict fairness rates by policy.",
    )
    add(
        "real_case_strict_exclusion",
        all(exclude_from_strict_bias(r) for r in real_rows) if real_rows else True,
        f"{len(real_rows)} real-case rows marked strict-excluded.",
    )

    collision = _check_output_collision(config, resume=resume)
    add("output_collision", collision["ok"], collision["message"], existing=collision.get("existing_files"))

    add("overwrite_disabled", not config.safety.overwrite_existing, "overwrite_existing=false — existing results protected.")
    add("dry_run_required", config.safety.dry_run_required, "Pilot runner will require this manifest.")

    n_modes = len(config.prompt_modes)
    total_requests = len(rows) * n_modes
    est_input_chars = sum(estimate_prompt_chars(r) for r in rows) * n_modes
    est_input_tokens = est_input_chars // 4
    est_output_tokens = total_requests * config.cost_estimates.output_tokens_per_call
    est_cost = (
        est_input_tokens / 1_000_000 * config.cost_estimates.input_cost_per_million
        + est_output_tokens / 1_000_000 * config.cost_estimates.output_cost_per_million
    )

    per_mode = {m: len(rows) for m in config.prompt_modes}

    manifest: dict[str, Any] = {
        "generated_at": _utc_now(),
        "config_path": str(config.config_path) if config.config_path else None,
        "checks_passed": all_ok,
        "checks": checks,
        "model": config.model,
        "provider": config.provider,
        "prompt_modes": config.prompt_modes,
        "output_dir": str(config.output_dir),
        "row_counts": {
            "pilot_total": len(rows),
            "synthetic_selected": len(rows) - len(real_rows),
            "real_case_selected": len(real_rows),
            "strict_eligible": len(strict_eligible),
            "strict_excluded": len(rows) - len(strict_eligible),
            "per_prompt_mode": per_mode,
        },
        "request_plan": {
            "total_requests": total_requests,
            "estimated_input_tokens": est_input_tokens,
            "estimated_output_tokens": est_output_tokens,
            "estimated_cost_usd": round(est_cost, 4),
            "cost_caution": config.cost_estimates.caution,
        },
        "rate_limit": {
            "requests_per_minute": config.rate_limit.requests_per_minute,
            "min_delay_seconds": config.rate_limit.min_delay_seconds,
            "estimated_minutes": round(total_requests * config.rate_limit.min_delay_seconds / 60, 1),
        },
        "metadata": config.metadata,
        "strict_fairness_source": config.metadata.get("strict_fairness_source"),
        "real_cases_in_strict_rates": config.metadata.get("real_cases_in_strict_rates"),
        "resume_supported": config.safety.resume_supported,
        "caution": (
            "Dry-run only — no Gemini API calls made. Pilot results are preliminary audit signals, "
            "not proof of unlawful discrimination."
        ),
    }

    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.dry_run_manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    from benchassist.detention_gemini_config import write_jsonl

    write_jsonl(config.selected_inputs_path, rows)

    report_path = project_root() / "results" / "report" / "gemini_detention_pilot_dry_run_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Gemini Detention Pilot — Dry-Run Report",
        "",
        f"Generated: {manifest['generated_at']}",
        "",
        f"**Checks passed:** {'Yes' if all_ok else 'No'}",
        "",
        "## Configuration",
        "",
        f"- Model: `{config.model}`",
        f"- Prompt modes: {', '.join(config.prompt_modes)}",
        f"- Output dir: `{config.output_dir}`",
        f"- Run type: {config.metadata.get('run_type', 'pilot')}",
        "",
        "## Row plan",
        "",
        f"- Total pilot rows: **{len(rows)}**",
        f"- Synthetic: {len(rows) - len(real_rows)}",
        f"- Real-case (qualitative/reliability): {len(real_rows)}",
        f"- Strict-eligible synthetic: {len(strict_eligible)}",
        f"- Strict-excluded: {len(rows) - len(strict_eligible)}",
        "",
        "## Request plan",
        "",
        f"- Total Gemini requests: **{total_requests}** ({len(rows)} rows × {n_modes} modes)",
        f"- Estimated input tokens: ~{est_input_tokens:,}",
        f"- Estimated output tokens: ~{est_output_tokens:,}",
        f"- Estimated cost (approx): ${est_cost:.4f}",
        f"- Estimated wall time (rate limit): ~{manifest['rate_limit']['estimated_minutes']} min",
        "",
        "## Safety checks",
        "",
    ]
    for c in checks:
        mark = "✓" if c["ok"] else "✗"
        lines.append(f"- {mark} **{c['name']}**: {c['detail']}")
    lines.extend([
        "",
        "## Methodology",
        "",
        "- Synthetic controlled counterfactuals → strict fairness audit signals only.",
        "- Real Israeli public legal examples → realism / legal reliability / qualitative review.",
        "- Real-case rows are **excluded** from strict fairness rates.",
        "",
        "## Next step",
        "",
        "If all checks pass and you have legal-expert approval:",
        "",
        "```bash",
        "python -m benchassist.detention_gemini_pilot \\",
        f"  --config {config.config_path or 'configs/gemini_detention_pilot.yaml'} \\",
        "  --resume",
        "```",
        "",
        "**Do not run the full audit until pilot QA passes.**",
        "",
        manifest["caution"],
    ])
    report_path.write_text("\n".join(lines), encoding="utf-8")

    manifest["report_path"] = str(report_path)
    config.dry_run_manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detention Gemini pilot dry-run planner (no API calls).")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true", help="Required flag — confirms planning mode.")
    parser.add_argument("--resume", action="store_true", help="Allow existing partial outputs.")
    args = parser.parse_args(argv)

    if not args.dry_run:
        print("Refusing to proceed without --dry-run. This command plans only — it never calls Gemini.")
        return 2

    config = load_detention_gemini_config(args.config)
    manifest = run_dry_run(config, resume=args.resume)

    print(f"Dry-run complete. Checks passed: {manifest['checks_passed']}")
    print(f"  Manifest: {config.dry_run_manifest_path}")
    print(f"  Report:   {manifest.get('report_path')}")
    print(f"  Pilot rows: {manifest['row_counts']['pilot_total']}")
    print(f"  Total requests: {manifest['request_plan']['total_requests']}")
    key_check = next((c for c in manifest["checks"] if c["name"] == "api_key"), {})
    ki = key_check.get("key_info", {})
    print(f"  API key verified: {ki.get('api_key_present', False)} (value not printed)")
    if not manifest["checks_passed"]:
        print("  WARNING: Some checks failed — fix before running pilot.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
