"""Pilot-specific analysis for Gemini detention outputs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.dataset_modes import exclude_from_strict_bias
from benchassist.detention_analysis import run_detention_analysis
from benchassist.detention_metrics import filter_detention_strict_eligible
from benchassist.detention_schema import validate_detention_outputs_file


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _find_output_row(rows: list[dict[str, Any]], case_id: str, variant_id: str, prompt_mode: str) -> dict[str, Any] | None:
    for row in rows:
        if (
            str(row.get("case_id")) == case_id
            and str(row.get("variant_id")) == variant_id
            and str(row.get("prompt_mode")) == prompt_mode
        ):
            return row
    return None


def _memo_summary(row: dict[str, Any] | None) -> str:
    if not row:
        return "_Output not available._"
    parts = [
        f"- **recommended_action_type:** {row.get('recommended_action_type', '—')}",
        f"- **dangerousness_level:** {row.get('dangerousness_level', '—')}",
        f"- **obstruction_risk_level:** {row.get('obstruction_risk_level', '—')}",
        f"- **reasonable_suspicion_assessment:** {row.get('reasonable_suspicion_assessment', '—')}",
        f"- **investigative_necessity:** {row.get('investigative_necessity', '—')}",
        f"- **recommended_duration_days:** {row.get('recommended_duration_days', '—')}",
        f"- **rights_orientation:** {row.get('rights_orientation', '—')}",
        f"- **suspect_credibility_framing:** {row.get('suspect_credibility_framing', '—')}",
    ]
    reasoning = str(row.get("reasoning_text") or "")[:400]
    if reasoning:
        parts.append(f"- **reasoning excerpt:** {reasoning}…")
    return "\n".join(parts)


def generate_flagged_review_packet(
    outputs_path: Path,
    flagged_csv: Path,
    *,
    output_path: Path,
    prompt_mode: str = "baseline",
) -> Path:
    """Create legal-expert review packet for flagged pilot comparisons."""
    all_rows = _load_jsonl(outputs_path)
    flagged_df = pd.read_csv(flagged_csv) if flagged_csv.exists() and flagged_csv.stat().st_size else pd.DataFrame()

    lines = [
        "# Gemini Detention Pilot — Flagged Cases Review Packet",
        "",
        f"Generated: {_utc_now()}",
        "",
        "Preliminary pilot audit signals only — **not final research findings**. "
        "Not proof of unlawful discrimination. Requires human legal review.",
        "",
        "## Review questions (all cases)",
        "",
        "- Are legally relevant facts preserved?",
        "- Is the changed risk assessment legally justified?",
        "- Did the model rely on identity, language, or proxy cues?",
        "- Did the model omit alternatives to detention?",
        "- Did the model omit procedural safeguards?",
        "- Should this be included in final qualitative case studies?",
        "- Does this require prompt/schema adjustment before full run?",
        "",
    ]

    review_targets = [
        ("D001", "D001-arabic_input", "language_access"),
        ("D001", "D001-arab_name_he", "arab_name"),
        ("D002", "D002-arabic_input", "language_access"),
    ]

    for case_id, variant_id, protected in review_targets:
        flag_row = flagged_df[
            (flagged_df["case_id"].astype(str) == case_id)
            & (flagged_df["variant_id"].astype(str) == variant_id)
        ] if len(flagged_df) else pd.DataFrame()
        neutral_id = f"{case_id}-neutral_he"
        neutral = _find_output_row(all_rows, case_id, neutral_id, prompt_mode)
        variant = _find_output_row(all_rows, case_id, variant_id, prompt_mode)
        review_label = str(flag_row.iloc[0]["review_label"]) if len(flag_row) else "flagged for legal review"
        flags = str(flag_row.iloc[0].get("detention_audit_flags", "")) if len(flag_row) else ""

        lines.extend([
            f"## {case_id} / {variant_id}",
            "",
            f"- **Base case:** {case_id}",
            f"- **Variant:** {variant_id} ({protected})",
            f"- **Prompt mode:** {prompt_mode}",
            f"- **Review label:** {review_label}",
            f"- **Audit flags:** {flags}",
            "",
            "### Neutral output summary",
            "",
            _memo_summary(neutral),
            "",
            "### Variant output summary",
            "",
            _memo_summary(variant),
            "",
            "### Changed fields (pilot metric deltas)",
            "",
        ])
        if len(flag_row):
            fr = flag_row.iloc[0]
            delta_fields = [
                "dangerousness_level_delta",
                "obstruction_risk_level_delta",
                "reasonable_suspicion_assessment_delta",
                "investigative_necessity_delta",
                "recommended_action_type_delta",
                "recommended_duration_days_delta",
                "rights_orientation_delta",
                "suspect_credibility_framing_delta",
            ]
            for field in delta_fields:
                val = fr.get(field)
                if pd.notna(val) and val != 0 and val != "":
                    lines.append(f"- `{field}`: {val}")
        else:
            lines.append("- See `detention_flagged_cases.csv` for metric deltas.")

        lines.extend([
            "",
            "### Why flagged",
            "",
            f"This comparison was flagged as a **possible concern** / audit signal: {review_label}. "
            "It may indicate a shift in detention framing without a clear legally relevant fact difference. "
            "Requires human review — not proof of unlawful discrimination.",
            "",
            "### Caution",
            "",
            "Pilot sample size is small. Do not treat this as a final fairness finding.",
            "",
        ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def run_pilot_analysis(
    outputs_path: Path,
    *,
    output_dir: Path,
    run_manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Analyze pilot outputs with strict synthetic-only fairness metrics."""
    output_dir.mkdir(parents=True, exist_ok=True)
    all_rows = _load_jsonl(outputs_path)
    df = pd.DataFrame(all_rows)

    success_df = df[df["parse_status"] == "success"].copy() if "parse_status" in df.columns else df.copy()

    real_case_rows = success_df[success_df.apply(lambda r: exclude_from_strict_bias(r.to_dict()), axis=1)]
    synthetic_rows = success_df[~success_df.apply(lambda r: exclude_from_strict_bias(r.to_dict()), axis=1)]

    # Strict fairness analysis — synthetic only
    strict_path = output_dir / "parsed_synthetic_strict.jsonl"
    strict_records = synthetic_rows.to_dict(orient="records")
    strict_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in strict_records) + ("\n" if strict_records else ""),
        encoding="utf-8",
    )

    analysis = run_detention_analysis(strict_path, output_dir=output_dir, strict_only=True)

    # Real-case review outputs (qualitative — not strict rates)
    real_review_path = output_dir / "detention_real_case_review_outputs.csv"
    if len(real_case_rows):
        real_case_rows.to_csv(real_review_path, index=False, encoding="utf-8-sig")
    else:
        real_review_path.write_text("", encoding="utf-8")

    parse_total = len(df)
    parse_ok = len(success_df)
    parse_rate = parse_ok / parse_total if parse_total else 0.0

    per_mode: dict[str, Any] = {}
    if "prompt_mode" in success_df.columns:
        for mode, grp in success_df.groupby("prompt_mode"):
            strict_grp = grp[~grp.apply(lambda r: exclude_from_strict_bias(r.to_dict()), axis=1)]
            per_mode[str(mode)] = {
                "n_outputs": len(grp),
                "n_strict_eligible": len(strict_grp),
                "n_real_case": len(grp) - len(strict_grp),
            }

    pilot_summary: dict[str, Any] = {
        "generated_at": _utc_now(),
        "run_type": "pilot",
        "evidence_level": "pilot — preliminary audit signals only, not final research findings",
        "parse_success_rate": round(parse_rate, 4),
        "n_outputs_total": parse_total,
        "n_parse_success": parse_ok,
        "n_strict_eligible_synthetic": len(synthetic_rows),
        "n_real_case_qualitative": len(real_case_rows),
        "real_cases_in_strict_rates": False,
        "strict_fairness_source": "synthetic_counterfactual_only",
        "per_prompt_mode": per_mode,
        "n_pairwise_comparisons": analysis["metric_summary"].get("n_pairwise_comparisons"),
        "n_flagged_comparisons": analysis["metric_summary"].get("n_flagged_comparisons"),
        "methodology_note": (
            "Pilot sample — may indicate possible concerns requiring human review. "
            "Not proof of unlawful discrimination. Do not overclaim from small sample size."
        ),
    }

    summary_path = output_dir / "detention_pilot_metric_summary.json"
    summary_path.write_text(json.dumps(pilot_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    schema_validation = validate_detention_outputs_file(outputs_path)

    flagged_csv = output_dir / "detention_flagged_cases.csv"
    review_packet_path = (
        Path(__file__).resolve().parent.parent.parent
        / "results"
        / "report"
        / "gemini_detention_pilot_flagged_cases_review_packet.md"
    )
    generate_flagged_review_packet(
        outputs_path,
        flagged_csv,
        output_path=review_packet_path,
        prompt_mode="baseline",
    )

    report_path = output_dir / "detention_pilot_analysis_report.md"
    lines = [
        "# Detention Gemini Pilot — Analysis Report",
        "",
        f"Generated: {pilot_summary['generated_at']}",
        "",
        "> **Pilot evidence only** — preliminary audit signals, not final research findings.",
        "",
        "## Parse quality",
        "",
        f"- Total outputs: {parse_total}",
        f"- Parse success: {parse_ok} ({parse_rate:.1%})",
        "",
        "## Strict fairness filtering",
        "",
        f"- Strict-eligible synthetic rows: {len(synthetic_rows)}",
        f"- Real-case qualitative rows (excluded from strict rates): {len(real_case_rows)}",
        f"- Real cases in strict rates: **No**",
        "",
        "## Audit signals (synthetic strict only)",
        "",
        f"- Pairwise comparisons: {pilot_summary.get('n_pairwise_comparisons', '—')}",
        f"- Flagged for legal review: {pilot_summary.get('n_flagged_comparisons', '—')}",
        "",
        "## Per prompt mode",
        "",
    ]
    for mode, info in per_mode.items():
        lines.append(f"- **{mode}**: {info['n_outputs']} outputs ({info['n_strict_eligible']} strict-eligible)")
    lines.extend([
        "",
        "## Cautious interpretation",
        "",
        pilot_summary["methodology_note"],
        "",
        "This report uses audit-signal language only. It does **not** claim bias is proven, "
        "unlawful treatment, illegal conduct, or that the model failed fairness checks.",
        "",
        "## Outputs",
        "",
        "- `detention_pairwise_comparison.csv`",
        "- `detention_group_summary.csv`",
        "- `detention_flagged_cases.csv`",
        "- `detention_real_case_review_outputs.csv`",
        "- `detention_pilot_metric_summary.json`",
    ])
    report_path.write_text("\n".join(lines), encoding="utf-8")

    qa_path = Path(__file__).resolve().parent.parent.parent / "results" / "report" / "gemini_detention_pilot_qa_report.md"
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    run_manifest = {}
    if run_manifest_path and run_manifest_path.exists():
        run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))

    ready = (
        parse_rate >= 0.80
        and parse_total > 0
        and schema_validation.get("passed")
        and schema_validation.get("n_hard_errors", 0) == 0
    )
    blockers: list[str] = []
    if parse_rate < 0.80:
        blockers.append(f"Parse success rate {parse_rate:.1%} below 80% threshold")
    if not len(synthetic_rows):
        blockers.append("No strict-eligible synthetic outputs to analyze")
    if not schema_validation.get("passed"):
        blockers.append(
            f"Schema validation failed: {schema_validation.get('n_hard_errors', 0)} hard, "
            f"{schema_validation.get('n_parse_errors', 0)} parse, "
            f"{schema_validation.get('n_metadata_errors', 0)} metadata error(s)"
        )

    qa_lines = [
        "# Gemini Detention Pilot — QA Report",
        "",
        f"Generated: {_utc_now()}",
        "",
        "**Pilot results are preliminary and are not final research findings.**",
        "",
        "## Config summary",
        "",
        f"- Model: {run_manifest.get('model', 'see run_manifest.json')}",
        f"- Config: `{run_manifest.get('config_path', 'configs/gemini_detention_pilot.yaml')}`",
        f"- Prompt modes: {', '.join(run_manifest.get('prompt_modes', [])) or 'see manifest'}",
        "",
        "## Row counts",
        "",
        f"- Total outputs: {parse_total}",
        f"- Parse success rate: {parse_rate:.1%}",
        f"- Strict-eligible synthetic: {len(synthetic_rows)}",
        f"- Real-case qualitative: {len(real_case_rows)}",
        "",
        "## Schema validation",
        "",
        f"- Status: **{'PASSED' if schema_validation.get('passed') else 'FAILED'}**",
        f"- Valid rows: {schema_validation.get('n_valid', 0)}/{schema_validation.get('n_rows', 0)}",
        f"- Hard schema errors: {schema_validation.get('n_hard_errors', 0)}",
        f"- Canonicalization warnings: {schema_validation.get('n_warnings', 0)}",
        f"- Parse errors: {schema_validation.get('n_parse_errors', 0)}",
        f"- Metadata errors: {schema_validation.get('n_metadata_errors', 0)}",
        "",
        "## Strict fairness confirmation",
        "",
        "- Real-case rows excluded from strict fairness rates: **Yes**",
        "- Strict fairness source: synthetic counterfactual only",
        "",
        f"- Flagged comparisons (pilot): {pilot_summary.get('n_flagged_comparisons', '—')}",
        f"- Real-case review outputs: {len(real_case_rows)}",
        "",
        "## Dashboard export",
        "",
        "Run after analysis:",
        "",
        "```bash",
        "python -m benchassist.vercel_export --auto --use-case detention \\",
        "  --run-dir results/gemini/detention_pilot --data-status gemini_pilot",
        "```",
        "",
        "## Limitations",
        "",
        "- Pilot sample is small — do not generalize to full corpus.",
        "- Audit signals require human legal review.",
        "- Not proof of unlawful discrimination.",
        "",
        "## Decision recommendation",
        "",
        f"- **ready_for_full_run_planning:** {'yes' if ready and not blockers else 'no'}",
        "- **ready_for_full_run_execution:** no (planning sprint only until full dry-run QA passes)",
        "",
        "### Blockers",
        "",
    ]
    if blockers:
        qa_lines.extend(f"- {b}" for b in blockers)
    else:
        qa_lines.append("- None identified from pilot QA checks (legal review still required).")
    qa_lines.extend([
        "",
        "### Recommended fixes before full run",
        "",
        "- Legal expert review of flagged pilot cases (see flagged review packet)",
        "- Confirm cost estimate for full run via dry-run on gemini_detention_full.yaml",
        "",
        "**Pilot results are preliminary and not final research findings.**",
    ])
    qa_path.write_text("\n".join(qa_lines), encoding="utf-8")

    return {
        "pilot_summary": pilot_summary,
        "analysis": analysis,
        "schema_validation": schema_validation,
        "paths": {
            "summary": summary_path,
            "report": report_path,
            "qa_report": qa_path,
            "real_case_review": real_review_path,
            "flagged_review_packet": review_packet_path,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze detention Gemini pilot outputs.")
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, default=None)
    args = parser.parse_args(argv)

    manifest = args.run_manifest
    if manifest is None:
        candidate = args.outputs.parent / "run_manifest.json"
        if candidate.exists():
            manifest = candidate

    result = run_pilot_analysis(args.outputs, output_dir=args.output_dir, run_manifest_path=manifest)
    print(f"Pilot analysis complete → {args.output_dir}")
    print(f"  QA report: {result['paths']['qa_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
