"""Dry-run planner for full Gemini detention audit — no API calls."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchassist.config import get_settings, resolve_gemini_api_key
from benchassist.dataset_modes import exclude_from_strict_bias
from benchassist.detention_gemini_config import (
    DetentionGeminiConfig,
    estimate_prompt_chars,
    load_detention_gemini_config,
    project_root,
    select_pilot_rows,
    verify_pilot_qa_passed,
    write_jsonl,
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
    final_markers = [config.parsed_outputs_path, config.run_manifest_path]
    existing: list[str] = []
    root = project_root()
    for p in final_markers:
        if p.exists() and p.stat().st_size > 0:
            try:
                existing.append(str(p.relative_to(root)))
            except ValueError:
                existing.append(str(p))
    if existing and not resume and not config.safety.overwrite_existing:
        return {
            "ok": False,
            "message": "Full-run output files already exist — use --resume or new output_dir. No --force.",
            "existing_files": existing,
        }
    return {"ok": True, "message": "No blocking full-run output collision.", "existing_files": existing}


def _access_control_policy_ok(root: Path) -> dict[str, Any]:
    policy_path = root / "web_dashboard" / "public" / "data" / "data_access_policy.json"
    if not policy_path.exists():
        return {"ok": False, "detail": "data_access_policy.json not found in dashboard export"}
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    ok = bool(policy.get("requires_access_control")) and policy.get("strict_bias_rates_include_real_cases") is False
    return {
        "ok": ok,
        "detail": f"requires_access_control={policy.get('requires_access_control')}, "
        f"strict_bias_rates_include_real_cases={policy.get('strict_bias_rates_include_real_cases')}",
        "contains_unredacted_public_legal_text": policy.get("contains_unredacted_public_legal_text"),
    }


def run_full_run_plan(
    config: DetentionGeminiConfig,
    *,
    resume: bool = False,
) -> dict[str, Any]:
    """Plan full Gemini detention run; write manifest, plan report, and checklist."""
    checks: list[dict[str, Any]] = []
    all_ok = True

    def add(name: str, ok: bool, detail: str, **extra: Any) -> None:
        nonlocal all_ok
        if not ok:
            all_ok = False
        checks.append({"name": name, "ok": ok, "detail": detail, **extra})

    root = project_root()
    pilot_qa = verify_pilot_qa_passed(root)
    add("pilot_qa_passed", pilot_qa["passed"], f"{len([c for c in pilot_qa['checks'] if c['ok']])}/{len(pilot_qa['checks'])} pilot QA checks")

    add("use_case", config.use_case == "detention", f"use_case={config.use_case}")
    add("run_type_full", config.is_full_run, f"run_type={config.run_type}")
    add("model", config.model == "gemini-2.5-flash-lite", f"model={config.model}")

    key_info = _mask_key_present()
    add("api_key", key_info["api_key_present"], key_info["note"], key_info=key_info)

    add("synthetic_input", config.synthetic_input.exists(), str(config.synthetic_input))
    add("real_case_input", config.real_case_input.exists(), str(config.real_case_input))

    rows: list[dict[str, Any]] = []
    try:
        rows = select_pilot_rows(config)
        add("row_selection", len(rows) > 0, f"{len(rows)} full-run input rows selected")
    except Exception as exc:
        add("row_selection", False, str(exc))

    strict_eligible = [r for r in rows if not exclude_from_strict_bias(r)]
    real_rows = [r for r in rows if exclude_from_strict_bias(r)]

    add(
        "strict_fairness_policy",
        not config.methodology.real_cases_in_strict_rates,
        "Real cases excluded from strict fairness rates by methodology config.",
    )
    add(
        "real_case_strict_exclusion",
        all(exclude_from_strict_bias(r) for r in real_rows) if real_rows else True,
        f"{len(real_rows)} real-case rows marked strict-excluded.",
    )

    collision = _check_output_collision(config, resume=resume)
    add("output_collision", collision["ok"], collision["message"], existing=collision.get("existing_files"))

    add("overwrite_disabled", not config.safety.overwrite_existing, "overwrite_existing=false")
    add("dry_run_required", config.safety.dry_run_required, "Full runner requires dry_run_manifest checks_passed=true")
    add("resume_supported", config.safety.resume_supported, "Resume supported for partial runs")
    add(
        "parse_error_stop_threshold",
        config.safety.stop_on_parse_error_rate_above <= 0.10,
        f"stop_on_parse_error_rate_above={config.safety.stop_on_parse_error_rate_above}",
    )
    add("grounded_disabled", not config.grounded_enabled, "Grounded mode disabled unless fully QA-tested")

    access = _access_control_policy_ok(root)
    add("dashboard_access_control_policy", access["ok"], access["detail"])
    add(
        "full_text_export_warning",
        config.dashboard.full_text_internal_only and config.dashboard.access_control_required,
        "Full-text internal-only + access-control flags set in dashboard config.",
    )

    n_modes = len(config.prompt_modes)
    total_requests = len(rows) * n_modes
    est_input_chars = sum(estimate_prompt_chars(r) for r in rows) * n_modes
    est_input_tokens = est_input_chars // 4
    est_output_tokens = total_requests * config.cost_estimates.output_tokens_per_call
    est_cost = (
        est_input_tokens / 1_000_000 * config.cost_estimates.input_cost_per_million
        + est_output_tokens / 1_000_000 * config.cost_estimates.output_cost_per_million
    )
    est_minutes_low = total_requests * config.rate_limit.min_delay_seconds / 60
    est_minutes_high = est_minutes_low * 1.15

    per_mode = {m: len(rows) for m in config.prompt_modes}

    manifest: dict[str, Any] = {
        "generated_at": _utc_now(),
        "config_path": str(config.config_path) if config.config_path else None,
        "checks_passed": all_ok,
        "checks": checks,
        "pilot_qa": pilot_qa,
        "model": config.model,
        "provider": config.provider,
        "prompt_modes": config.prompt_modes,
        "output_dir": str(config.output_dir),
        "row_counts": {
            "input_total": len(rows),
            "synthetic_rows": len(rows) - len(real_rows),
            "real_case_rows": len(real_rows),
            "strict_eligible_synthetic": len(strict_eligible),
            "strict_excluded": len(rows) - len(strict_eligible),
            "per_prompt_mode": per_mode,
        },
        "request_plan": {
            "total_requests": total_requests,
            "estimated_input_tokens": est_input_tokens,
            "estimated_output_tokens": est_output_tokens,
            "estimated_cost_usd": round(est_cost, 4),
            "estimated_runtime_minutes_low": round(est_minutes_low, 1),
            "estimated_runtime_minutes_high": round(est_minutes_high, 1),
            "cost_caution": config.cost_estimates.caution,
        },
        "rate_limit": {
            "requests_per_minute": config.rate_limit.requests_per_minute,
            "min_delay_seconds": config.rate_limit.min_delay_seconds,
        },
        "methodology": {
            "strict_fairness_source": config.methodology.strict_fairness_source,
            "real_cases_in_strict_rates": config.methodology.real_cases_in_strict_rates,
            "real_cases_use": config.methodology.real_cases_use,
        },
        "dashboard": {
            "export_after_run": config.dashboard.export_after_run,
            "data_status": config.dashboard.data_status,
            "full_text_internal_only": config.dashboard.full_text_internal_only,
            "access_control_required": config.dashboard.access_control_required,
            "full_text_export_warning": (
                "Full unredacted legal text is being exported for internal expert review. "
                "Deploy only behind access control. Do not rely on URL secrecy."
            ),
        },
        "future_execution_command": (
            "python -m benchassist.detention_gemini_full "
            f"--config {config.config_path or 'configs/gemini_detention_full.yaml'} --resume"
        ),
        "caution": (
            "Dry-run only — no Gemini API calls made. Audit signals require human legal review. "
            "Not proof of unlawful discrimination."
        ),
    }

    config.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(config.selected_inputs_path, rows)
    config.dry_run_manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report_dir = root / "results" / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    plan_path = report_dir / "gemini_detention_full_run_plan.md"
    checklist_path = report_dir / "gemini_detention_full_run_checklist.md"

    plan_lines = [
        "# Gemini Detention Full Run — Planning Report",
        "",
        f"Generated: {manifest['generated_at']}",
        "",
        f"**Checks passed:** {'Yes' if all_ok else 'No'}",
        "",
        "**Pilot results are preliminary. Full-run planning does not execute Gemini.**",
        "",
        "## Configuration",
        "",
        f"- Model: `{config.model}`",
        f"- Config: `{config.config_path}`",
        f"- Prompt modes: {', '.join(config.prompt_modes)}",
        f"- Output dir: `{config.output_dir}`",
        f"- Parse-error stop threshold: {config.safety.stop_on_parse_error_rate_above:.0%}",
        "",
        "## Row plan",
        "",
        f"- Total input rows: **{len(rows)}**",
        f"- Synthetic (strict-eligible subset): {len(rows) - len(real_rows)}",
        f"- Strict-eligible synthetic: **{len(strict_eligible)}**",
        f"- Real-case qualitative/reliability: **{len(real_rows)}**",
        "",
        "## Request plan",
        "",
        f"- Total Gemini requests: **{total_requests}** ({len(rows)} rows × {n_modes} modes)",
        f"- Per mode: {', '.join(f'{m}={len(rows)}' for m in config.prompt_modes)}",
        f"- Estimated input tokens: ~{est_input_tokens:,}",
        f"- Estimated output tokens: ~{est_output_tokens:,}",
        f"- Estimated cost (approx): ${est_cost:.2f}",
        f"- Estimated runtime: ~{est_minutes_low:.0f}–{est_minutes_high:.0f} min (rate limit only)",
        "",
        "## Methodology",
        "",
        "- Strict fairness metrics: synthetic controlled counterfactual only.",
        "- Real Israeli cases: realism, legal reliability, grounding, qualitative review.",
        "- Real-case rows **excluded** from strict fairness rates.",
        "",
        "## Safety checks",
        "",
    ]
    for c in checks:
        mark = "✓" if c["ok"] else "✗"
        plan_lines.append(f"- {mark} **{c['name']}**: {c['detail']}")

    plan_lines.extend([
        "",
        "## Future execution (DO NOT RUN until human approval)",
        "",
        "```bash",
        manifest["future_execution_command"],
        "```",
        "",
        manifest["caution"],
    ])
    plan_path.write_text("\n".join(plan_lines), encoding="utf-8")

    schema_ok = any(c["name"] == "pilot_schema_validation" and c["ok"] for c in pilot_qa["checks"])
    ready_execution = all_ok and pilot_qa["passed"] and collision["ok"]
    checklist_lines = [
        "# Gemini Detention Full Run — Readiness Checklist",
        "",
        f"Generated: {manifest['generated_at']}",
        "",
        "## Pre-execution checklist",
        "",
        f"- [{'x' if pilot_qa['passed'] else ' '}] Pilot QA passed",
        f"- [{'x' if schema_ok else ' '}] Schema validation passed on pilot outputs",
        f"- [{'x' if pilot_qa['passed'] else ' '}] Enum canonicalization tested (pilot fix sprint)",
        f"- [{'x' if config.synthetic_input.exists() else ' '}] Synthetic dataset available",
        f"- [{'x' if config.real_case_input.exists() else ' '}] Real-case corpus available",
        f"- [{'x' if not config.methodology.real_cases_in_strict_rates else ' '}] Strict filtering confirmed (real cases excluded from strict rates)",
        f"- [{'x' if access['ok'] else ' '}] Dashboard access-control policy present",
        f"- [{'x' if collision['ok'] else ' '}] No full-run output conflict (or resume planned)",
        f"- [{'x' if key_info['api_key_present'] else ' '}] API key presence verified (value not printed)",
        f"- [{'x' if all_ok else ' '}] Full dry-run checks passed",
        "",
        "## Planned run parameters",
        "",
        f"- Estimated request count: **{total_requests}**",
        f"- Prompt modes: {', '.join(config.prompt_modes)}",
        f"- Strict-eligible synthetic rows: {len(strict_eligible)}",
        f"- Real-case qualitative outputs (max): {len(real_rows) * n_modes}",
        f"- Parse-error stop threshold: {config.safety.stop_on_parse_error_rate_above:.0%}",
        f"- Resume behavior: {'available' if config.safety.resume_supported else 'not configured'}",
        "",
        "## Human approval",
        "",
        "- [ ] Legal expert review of pilot flagged cases completed",
        "- [ ] Full-run cost and runtime reviewed",
        "- [ ] Access-control deployment plan confirmed if exporting full text",
        "",
        f"**Ready for full Gemini execution: {'YES' if ready_execution else 'NO'}**",
        "",
        "Planning only — this sprint does not execute the full audit.",
        "",
        manifest["caution"],
    ]
    checklist_path.write_text("\n".join(checklist_lines), encoding="utf-8")

    manifest["report_paths"] = {
        "plan": str(plan_path),
        "checklist": str(checklist_path),
    }
    config.dry_run_manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Full Gemini detention run planner (no API calls).")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true", help="Required — planning mode only.")
    parser.add_argument("--resume", action="store_true", help="Allow existing partial full-run outputs.")
    args = parser.parse_args(argv)

    if not args.dry_run:
        print("Refusing to proceed without --dry-run. This command plans only — it never calls Gemini.")
        return 2

    config = load_detention_gemini_config(args.config)
    if not config.is_full_run:
        print(f"Refusing: config run_type is '{config.run_type}', expected 'full'.")
        return 2

    manifest = run_full_run_plan(config, resume=args.resume)

    print(f"Full-run dry-run complete. Checks passed: {manifest['checks_passed']}")
    print(f"  Manifest:   {config.dry_run_manifest_path}")
    print(f"  Plan:       {manifest['report_paths']['plan']}")
    print(f"  Checklist:  {manifest['report_paths']['checklist']}")
    rc = manifest["row_counts"]
    print(f"  Input rows: {rc['input_total']} (strict-eligible synthetic: {rc['strict_eligible_synthetic']})")
    print(f"  Requests:   {manifest['request_plan']['total_requests']}")
    key_check = next((c for c in manifest["checks"] if c["name"] == "api_key"), {})
    print(f"  API key verified: {key_check.get('key_info', {}).get('api_key_present', False)} (value not printed)")
    if not manifest["checks_passed"]:
        print("  WARNING: Some checks failed — fix before full execution.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
