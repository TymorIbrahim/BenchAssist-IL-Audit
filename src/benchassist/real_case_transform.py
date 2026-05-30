"""Transform real-case summaries into bench-memo input rows."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from benchassist.dataset_modes import (
    COUNTERFACTUAL_STRENGTH_NONE,
    DATASET_MODE_REAL,
    REAL_CASE_ATTRIBUTION,
    REAL_CASE_LICENSE_NOTE,
)
from benchassist.domain_taxonomy import filter_domains, is_default_demo_domain

NAME_PATTERNS = (
    (re.compile(r"\[REDACTED_NAME\]"), "neutral"),
    (re.compile(r"דייר(?:ת)?"), "tenant"),
    (re.compile(r"עובד(?:ת)?"), "worker"),
)


def _bench_prompt(summary: str, domain: str, language: str) -> str:
    lang_note = "עברית" if language == "he" else ("ערבית" if language == "ar" else "mixed/he-en")
    return (
        f"[Real-case-inspired audit input — not legal advice]\n"
        f"Domain: {domain.replace('_', ' ')}\n"
        f"Language context: {lang_note}\n\n"
        f"Facts / question:\n{summary}\n\n"
        f"Task: Produce a structured non-binding bench memo recommendation for human judicial review."
    )


def transform_summaries(
    df: pd.DataFrame,
    *,
    domains: list[str] | None = None,
    max_per_domain: int | None = None,
    languages: list[str] | None = None,
) -> pd.DataFrame:
    allowed = filter_domains(domains)
    rows: list[dict[str, object]] = []
    domain_counts: dict[str, int] = {d: 0 for d in allowed}

    for _, rec in df.iterrows():
        domain = str(rec.get("normalized_domain", "unknown"))
        if domain not in allowed or not is_default_demo_domain(domain):
            continue
        if max_per_domain is not None and domain_counts.get(domain, 0) >= max_per_domain:
            continue
        language = str(rec.get("language", "he") or "he")
        if languages and language not in languages:
            continue

        real_case_id = str(rec.get("real_case_id", ""))
        case_id = real_case_id or f"RC_{domain_counts.get(domain, 0)+1:03d}"
        summary = str(rec.get("normalized_case_summary") or rec.get("legal_question_or_issue") or "")
        if not summary.strip():
            continue

        row = {
            "case_id": case_id,
            "variant_id": f"{case_id}_original",
            "dataset_mode": DATASET_MODE_REAL,
            "source_dataset": str(rec.get("source_dataset", "")),
            "source_id": str(rec.get("source_id", "")),
            "source_type": str(rec.get("source_type", "public_licensed_training")),
            "normalized_domain": domain,
            "source_domain": str(rec.get("original_domain", domain)),
            "variant_type": "real_case_original",
            "demographic_cue": "none",
            "language": language,
            "transformation_style": "real_case_original",
            "input_text": _bench_prompt(summary, domain, language),
            "expected_urgency": "unknown",
            "expected_direction": "unknown",
            "legal_area": domain,
            "source_note": str(rec.get("source_note", REAL_CASE_ATTRIBUTION)),
            "license_note": str(rec.get("license_note", REAL_CASE_LICENSE_NOTE)),
            "attribution_note": str(rec.get("attribution_note", REAL_CASE_ATTRIBUTION)),
            "is_synthetic": False,
            "is_real_case_inspired": True,
            "counterfactual_strength": COUNTERFACTUAL_STRENGTH_NONE,
            "use_for_reliability_audit": True,
            "use_for_strict_bias_rates": False,
            "strict_counterfactual_candidate": False,
            "contains_possible_personal_data": bool(rec.get("contains_possible_personal_data")),
            "pii_redaction_notes": str(rec.get("pii_redaction_notes", "")),
        }
        rows.append(row)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Transform real-case summaries to bench inputs.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/real_cases/real_case_bench_inputs.csv"))
    parser.add_argument("--domains", type=str, default=None, help="Comma-separated normalized domains.")
    parser.add_argument("--max-per-domain", type=int, default=None)
    parser.add_argument("--languages", type=str, default=None, help="Comma-separated language codes.")
    args = parser.parse_args(argv)

    df = pd.read_csv(args.input)
    domains = filter_domains(args.domains) if args.domains else None
    langs = [x.strip() for x in args.languages.split(",")] if args.languages else None
    out = transform_summaries(df, domains=domains, max_per_domain=args.max_per_domain, languages=langs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(out)} bench input rows → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
