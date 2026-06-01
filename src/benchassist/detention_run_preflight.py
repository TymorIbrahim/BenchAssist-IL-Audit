"""Unified preflight for minimal detention Gemini runs — corpus + dry-run + go/no-go report."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchassist.detention_corpus_preflight import validate_synthetic_corpus
from benchassist.detention_full_run_plan import run_full_run_plan
from benchassist.detention_gemini_config import load_detention_gemini_config, project_root


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_go_no_go_report(
    path: Path,
    *,
    config_path: Path,
    corpus: dict[str, Any],
    plan: dict[str, Any],
) -> None:
    ready_key = (
        "READY_FOR_MINIMAL_ADDRESS_GEMINI_RUN"
        if plan.get("run_type") == "expanded_minimal_address"
        else "READY_FOR_EXPANDED_GEMINI_RUN"
    )
    ready = corpus.get("passed") and plan.get("checks_passed")
    lines = [
        "# Detention Gemini Run — Preflight Go/No-Go",
        "",
        f"Generated: {_utc_now()}",
        "",
        f"## Executive recommendation",
        "",
        f"**{ready_key}: {'YES' if ready else 'NO'}**",
        "",
        "Human approval still required before executing the real Gemini run.",
        "",
        "## 1. Synthetic corpus",
        "",
        f"| Check | Status |",
        f"|-------|--------|",
    ]
    for c in corpus.get("checks", []):
        mark = "PASS" if c["ok"] else "FAIL"
        lines.append(f"| {c['name']} | {mark} |")
    counts = corpus.get("counts") or {}
    if counts:
        lines.extend([
            "",
            f"- Rows: **{counts.get('row_count', '—')}**",
            f"- Base cases: **{counts.get('base_case_count', '—')}**",
            f"- Strict-eligible: **{counts.get('strict_eligible_count', '—')}**",
            f"- Address-proxy: **{counts.get('address_proxy_count', '—')}**",
        ])
    lines.extend([
        "",
        "## 2. Dry-run planner",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Config | `{config_path}` |",
        f"| `checks_passed` | **{plan.get('checks_passed')}** |",
        f"| Schema | `{plan.get('schema_version', '—')}` |",
        f"| Output dir | `{plan.get('output_dir', '—')}` |",
        f"| Total requests | **{plan.get('request_plan', {}).get('total_requests', '—')}** |",
        f"| Strict pairwise (est.) | **{plan.get('pairwise_plan', {}).get('expected_pairwise_comparisons', '—')}** |",
        "",
        f"Manifest: `{plan.get('output_dir', '')}/dry_run_manifest.json`",
        "",
        "## 3. Flagging & dashboard alignment",
        "",
        "- Primary flag: **dangerousness_level** change only (`docs/detention_flagging_policy.md`).",
        "- Dashboard: 7-tab slim audit; export with `data_status` from config.",
        "- Full text: internal expert review only — use `--demo-redact-case-text` for public demos.",
        "",
        "## Commands (after YES)",
        "",
        "```bash",
        "# Execute (requires API key; resume-safe):",
        plan.get("future_execution_command", "python -m benchassist.detention_gemini_full --config … --resume"),
        "",
        "# After run completes:",
        f"python -m benchassist.detention_post_run --config {config_path}",
        "```",
        "",
        plan.get("caution", "Audit signals require human legal review."),
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_detention_preflight(
    config_path: Path,
    *,
    resume: bool = False,
    report_path: Path | None = None,
) -> dict[str, Any]:
    config = load_detention_gemini_config(config_path)
    require_address = config.is_expanded_minimal_address_run
    corpus = validate_synthetic_corpus(
        config.synthetic_input,
        config_path=config_path,
        require_address_proxy=require_address,
    )
    plan = run_full_run_plan(config, resume=resume)

    root = project_root()
    slug = config.run_slug
    if report_path is None:
        report_path = root / "results" / "report" / f"gemini_{slug}_preflight_go_no_go.md"

    _write_go_no_go_report(report_path, config_path=config_path, corpus=corpus, plan=plan)

    ready = corpus["passed"] and plan["checks_passed"]
    result = {
        "ready": ready,
        "corpus": corpus,
        "plan": plan,
        "report_path": str(report_path),
        "ready_label": (
            "READY_FOR_MINIMAL_ADDRESS_GEMINI_RUN"
            if config.is_expanded_minimal_address_run
            else "READY_FOR_EXPANDED_GEMINI_RUN"
        ),
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detention Gemini preflight (corpus + dry-run, no API calls).")
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root() / "configs" / "gemini_detention_expanded_minimal_address.yaml",
    )
    parser.add_argument("--resume", action="store_true", help="Allow existing partial outputs in output_dir.")
    parser.add_argument("--report", type=Path, default=None, help="Override go/no-go markdown path.")
    args = parser.parse_args(argv)

    result = run_detention_preflight(args.config, resume=args.resume, report_path=args.report)
    print(f"Preflight complete. {result['ready_label']}: {'YES' if result['ready'] else 'NO'}")
    print(f"  Report: {result['report_path']}")
    print(f"  Corpus checks: {'PASS' if result['corpus']['passed'] else 'FAIL'}")
    print(f"  Dry-run checks: {'PASS' if result['plan']['checks_passed'] else 'FAIL'}")
    if not result["ready"]:
        failed = [c for c in result["corpus"]["checks"] + result["plan"]["checks"] if not c["ok"]]
        for c in failed[:8]:
            print(f"    - {c['name']}: {c['detail']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
