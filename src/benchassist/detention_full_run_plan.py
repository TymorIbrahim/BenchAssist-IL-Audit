"""Dry-run planner for full Gemini detention audit — no API calls."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.config import get_settings, resolve_gemini_api_key
from benchassist.address_variants import is_address_proxy_row
from benchassist.dataset_modes import exclude_from_strict_bias, is_real_case_row
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


def _estimate_pairwise_comparisons(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Estimate neutral-vs-variant pairwise comparisons for strict-eligible rows."""
    from collections import defaultdict

    by_base: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if exclude_from_strict_bias(row):
            continue
        base = str(row.get("base_case_id") or row.get("case_id") or "")
        if base:
            by_base[base].append(row)

    per_base: dict[str, int] = {}
    total = 0
    for base, variants in sorted(by_base.items()):
        has_neutral = any(str(v.get("variant_type")) == "neutral_he" for v in variants)
        if not has_neutral:
            per_base[base] = 0
            continue
        non_neutral = [v for v in variants if str(v.get("variant_type")) != "neutral_he"]
        per_base[base] = len(non_neutral)
        total += len(non_neutral)

    return {
        "expected_pairwise_comparisons": total,
        "base_cases_with_neutral": sum(1 for n in per_base.values() if n > 0),
        "base_cases_total": len(by_base),
    }


def _corpus_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    bases = {str(r.get("base_case_id")) for r in rows if r.get("base_case_id")}
    variants = {str(r.get("variant_id")) for r in rows if r.get("variant_id")}
    strict = [r for r in rows if not exclude_from_strict_bias(r)]
    excluded = [r for r in rows if exclude_from_strict_bias(r)]
    return {
        "base_case_count": len(bases),
        "variant_count": len(variants),
        "strict_eligible_count": len(strict),
        "strict_excluded_count": len(excluded),
    }


def _report_paths(root: Path, config: DetentionGeminiConfig) -> tuple[Path, Path]:
    slug = config.run_slug or "detention_run"
    report_dir = root / "results" / "report"
    plan_path = report_dir / f"gemini_{slug}_run_plan.md"
    checklist_path = report_dir / f"gemini_{slug}_run_checklist.md"
    return plan_path, checklist_path


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
    real_rows = [r for r in rows if is_real_case_row(r)]
    strict_excluded = [r for r in rows if exclude_from_strict_bias(r)]
    address_proxy_rows = [r for r in rows if is_address_proxy_row(r)]

    add(
        "schema_version",
        bool(config.schema_version),
        f"schema_version={config.schema_version}",
    )
    from benchassist.detention_schema import SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2

    if config.is_expanded_minimal_address_run:
        add(
            "minimal_schema_config",
            config.schema_version == SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2,
            f"expanded_minimal_address requires {SCHEMA_VERSION_MINIMAL_DANGEROUSNESS_V2}",
        )
    else:
        add(
            "minimal_schema_config",
            True,
            f"run_type={config.run_type} (minimal schema check applies only to expanded_minimal_address)",
        )

    flagging_doc = root / "docs" / "detention_flagging_policy.md"
    add("flagging_policy_doc", flagging_doc.exists(), str(flagging_doc))
    add(
        "address_proxy_strict_exclusion",
        not config.methodology.address_proxy_in_strict_rates,
        f"address_proxy_in_strict_rates={config.methodology.address_proxy_in_strict_rates}",
    )
    add(
        "address_proxy_rows_present",
        len(address_proxy_rows) > 0 if config.is_expanded_minimal_address_run else True,
        f"{len(address_proxy_rows)} address-proxy rows in selected inputs",
    )

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
    add(
        "strict_schema_validation",
        config.safety.strict_schema_validation,
        "Schema canonicalization + strict validation enabled for runner outputs.",
    )

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
    corpus = _corpus_counts(rows)
    pairwise_est = _estimate_pairwise_comparisons(rows)

    old_full_pairwise: int | None = None
    old_pairwise_path = root / "results" / "gemini" / "detention_full" / "analysis" / "detention_pairwise_comparison.csv"
    if old_pairwise_path.exists():
        try:
            old_full_pairwise = len(pd.read_csv(old_pairwise_path))
        except Exception:
            old_full_pairwise = None

    manifest: dict[str, Any] = {
        "generated_at": _utc_now(),
        "config_path": str(config.config_path) if config.config_path else None,
        "run_type": config.run_type,
        "expanded_run": config.is_expanded_full_run,
        "checks_passed": all_ok,
        "checks": checks,
        "pilot_qa": pilot_qa,
        "model": config.model,
        "provider": config.provider,
        "schema_version": config.schema_version,
        "flagging_policy": "dangerousness_level_change_only",
        "flagging_policy_doc": "docs/detention_flagging_policy.md",
        "prompt_modes": config.prompt_modes,
        "output_dir": str(config.output_dir),
        "row_counts": {
            "input_total": len(rows),
            "synthetic_rows": len(rows) - len(real_rows),
            "real_case_rows": len(real_rows),
            "strict_excluded_synthetic": len(strict_excluded) - len(real_rows),
            "base_case_count": corpus["base_case_count"],
            "variant_count": corpus["variant_count"],
            "strict_eligible_synthetic": len(strict_eligible),
            "strict_excluded": len(strict_excluded),
            "address_proxy_rows": len(address_proxy_rows),
            "address_proxy_excluded_from_strict": all(exclude_from_strict_bias(r) for r in address_proxy_rows)
            if address_proxy_rows
            else True,
            "per_prompt_mode": per_mode,
        },
        "pairwise_plan": {
            **pairwise_est,
            "expected_address_proxy_comparisons": len(address_proxy_rows) * len(config.prompt_modes),
            "address_proxy_analysis_bucket": "address_proxy_audit",
            "per_prompt_mode_note": "Analysis dedupes across prompt modes for headline pairwise counts.",
            "legacy_detention_full_pairwise_count": old_full_pairwise,
            "legacy_mismatch_warning": (
                old_full_pairwise is not None
                and old_full_pairwise != pairwise_est["expected_pairwise_comparisons"]
                and config.is_expanded_full_run
            ),
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
            "address_proxy_in_strict_rates": config.methodology.address_proxy_in_strict_rates,
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
    plan_path, checklist_path = _report_paths(root, config)

    run_label = (
        "Expanded Minimal Address"
        if config.is_expanded_minimal_address_run
        else ("Expanded Full" if config.is_expanded_full_run else "Full")
    )
    plan_lines = [
        f"# Gemini Detention {run_label} Run — Planning Report",
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
        f"- Base cases: **{corpus['base_case_count']}**",
        f"- Variants: **{corpus['variant_count']}**",
        f"- Synthetic rows: {len(rows) - len(real_rows)}",
        f"- Strict-eligible synthetic: **{len(strict_eligible)}**",
        f"- Strict-excluded (stress/proxy/narrative/real/address): **{len(rows) - len(strict_eligible)}**",
        f"- Address-proxy rows (separate audit bucket): **{len(address_proxy_rows)}**",
        f"- Real-case qualitative/reliability: **{len(real_rows)}**",
        "",
        "## Pairwise comparison plan",
        "",
        f"- Expected strict pairwise comparisons (neutral vs variant): **{pairwise_est['expected_pairwise_comparisons']}**",
        f"- Base cases with neutral baseline: **{pairwise_est['base_cases_with_neutral']}**",
    ]
    if old_full_pairwise is not None and config.is_expanded_full_run:
        plan_lines.extend([
            f"- Legacy `detention_full` pairwise count: **{old_full_pairwise}** (12-base run — will not be silently reused)",
        ])
    plan_lines.extend([
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
        "- Address proxy variants: proxy-cautious audit signals only — analyzed separately; not proof of discrimination.",
        "- Real Israeli cases: realism, legal reliability, grounding, qualitative review.",
        "- Real-case rows **excluded** from strict fairness rates.",
        "",
        "## Safety checks",
        "",
    ])
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
    ready_label = (
        "READY_FOR_MINIMAL_ADDRESS_GEMINI_RUN"
        if config.is_expanded_minimal_address_run
        else "READY_FOR_EXPANDED_GEMINI_RUN"
        if config.is_expanded_full_run
        else "Ready for full Gemini execution"
    )
    checklist_lines = [
        f"# Gemini Detention {run_label} Run — Readiness Checklist",
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
        f"- Expected pairwise comparisons: **{pairwise_est['expected_pairwise_comparisons']}**",
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
        f"**{ready_label}: {'YES' if ready_execution else 'NO'}**",
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
        print(f"Refusing: config run_type is '{config.run_type}', expected full or expanded run type.")
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
