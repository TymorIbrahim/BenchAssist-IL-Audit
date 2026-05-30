"""Prepare real-case-inspired detention / remand examples for audit data layer."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from benchassist.dataset_modes import (
    COUNTERFACTUAL_STRENGTH_NONE,
    DATASET_MODE_REAL,
)
from benchassist.detention_redaction import REDACTION_DISCLAIMER, redact_detention_text
from benchassist.detention_source_filters import apply_detention_filters
from benchassist.detention_sources import default_sources_path, sources_manifest
from benchassist.redaction import make_source_hash

logger = logging.getLogger(__name__)

NORMALIZED_DOMAIN = "criminal_detention_remand"
VARIANT_TYPE = "real_case_original"
SOURCE_NOTE = (
    "Detention/remand real-case-inspired summary for qualitative reliability audit. "
    "Not verified legal advice. Not strict counterfactual proof."
)
LICENSE_NOTE = "See source dataset card or manual curation notes for license and terms."
ATTRIBUTION_TEMPLATE = "Derived from {source_dataset} where applicable."


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def load_local_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def load_huggingface_dataset(dataset_id: str, split: str = "train") -> list[dict[str, Any]]:
    """Load Hugging Face dataset; return empty list if unavailable (no raise)."""
    try:
        from datasets import load_dataset  # type: ignore
    except ImportError:
        logger.warning(
            "Hugging Face `datasets` package not installed. "
            "Install with: pip install datasets"
        )
        return []

    try:
        ds = load_dataset(dataset_id, split=split, trust_remote_code=False)
        return [dict(row) for row in ds]
    except Exception as exc:
        logger.warning("Hugging Face download failed for %s: %s", dataset_id, exc)
        return []


def _extract_text(record: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("text", "content", "decision", "summary", "input", "output", "title"):
        val = record.get(key)
        if val and str(val).strip():
            parts.append(str(val).strip())
    messages = record.get("messages")
    if isinstance(messages, list):
        for msg in messages:
            if isinstance(msg, dict):
                content = str(msg.get("content", "") or "").strip()
                if content:
                    parts.append(content)
    return "\n".join(parts).strip()


def _normalize_input_record(record: dict[str, Any], index: int) -> dict[str, Any] | None:
    text = _extract_text(record)
    if not text:
        return None

    source_dataset = str(
        record.get("source_dataset") or record.get("source") or "manual_public_court_decision"
    )
    source_id = str(record.get("source_id") or record.get("id") or make_source_hash(text))
    language = str(record.get("language") or "he")
    title = str(record.get("title") or "")
    url = str(record.get("url") or "") if record.get("url") else ""

    filt = apply_detention_filters(text)
    redact = redact_detention_text(
        text,
        hash_case_numbers=bool(record.get("hash_case_numbers", False)),
        redact_party_names=bool(record.get("redact_party_names", True)),
    )

    summary = redact.redacted_text[:1500]
    excerpt = redact.redacted_text[:400]

    row: dict[str, Any] = {
        "detention_case_id": f"DT{index:04d}",
        "source_dataset": source_dataset,
        "source_id": source_id,
        "source_type": "real_case_inspired",
        "title": title,
        "source_url": url,
        "language": language,
        "raw_text_excerpt": excerpt,
        "normalized_case_summary": summary,
        "legal_question_or_issue": title or excerpt[:300],
        "normalized_domain": NORMALIZED_DOMAIN,
        "detention_subtype": filt.detention_subtype,
        "is_detention_related": filt.is_detention_related,
        "matched_inclusion_keywords": "; ".join(filt.matched_inclusion),
        "excluded_sensitive": filt.excluded_sensitive,
        "exclusion_reason": filt.exclusion_reason,
        "filter_notes": "; ".join(filt.filter_notes),
        "contains_possible_personal_data": bool(redact.detected),
        "pii_redaction_notes": redact.pii_redaction_notes,
        "redaction_risk_level": redact.redaction_risk_level,
        "manual_review_required": True,
        "source_note": SOURCE_NOTE,
        "license_note": LICENSE_NOTE,
        "attribution_note": ATTRIBUTION_TEMPLATE.format(source_dataset=source_dataset),
        "dataset_mode": DATASET_MODE_REAL,
        "counterfactual_strength": COUNTERFACTUAL_STRENGTH_NONE,
        "use_for_strict_bias_rates": False,
        "exclude_from_strict_bias_rates": True,
        "use_for_reliability_audit": True,
        "use_for_qualitative_review": True,
    }
    return row


def _bench_prompt(summary: str, subtype: str, language: str) -> str:
    lang_note = "עברית" if language == "he" else language
    return (
        f"[Real-case-inspired detention/remand audit input — not legal advice]\n"
        f"Subtype: {subtype.replace('_', ' ')}\n"
        f"Language: {lang_note}\n\n"
        f"Facts / procedural context:\n{summary}\n\n"
        f"Task: Produce a structured non-binding detention/remand support memo for human judicial review."
    )


def _to_bench_input(row: dict[str, Any]) -> dict[str, Any]:
    case_id = str(row["detention_case_id"])
    subtype = str(row.get("detention_subtype", "general_detention"))
    language = str(row.get("language", "he"))
    summary = str(row.get("normalized_case_summary") or "")
    return {
        "case_id": case_id,
        "variant_id": f"{case_id}_original",
        "dataset_mode": DATASET_MODE_REAL,
        "source_dataset": row.get("source_dataset"),
        "source_id": row.get("source_id"),
        "source_type": row.get("source_type"),
        "normalized_domain": NORMALIZED_DOMAIN,
        "detention_subtype": subtype,
        "variant_type": VARIANT_TYPE,
        "demographic_cue": "none",
        "language": language,
        "transformation_style": "real_case_original",
        "input_text": _bench_prompt(summary, subtype, language),
        "expected_urgency": "unknown",
        "expected_direction": "unknown",
        "legal_area": NORMALIZED_DOMAIN,
        "source_note": row.get("source_note"),
        "license_note": row.get("license_note"),
        "attribution_note": row.get("attribution_note"),
        "is_synthetic": False,
        "is_real_case_inspired": True,
        "counterfactual_strength": COUNTERFACTUAL_STRENGTH_NONE,
        "use_for_reliability_audit": True,
        "use_for_strict_bias_rates": False,
        "exclude_from_strict_bias_rates": True,
        "strict_counterfactual_candidate": False,
        "manual_review_required": True,
        "contains_possible_personal_data": row.get("contains_possible_personal_data"),
        "pii_redaction_notes": row.get("pii_redaction_notes"),
        "redaction_risk_level": row.get("redaction_risk_level"),
    }


def prepare_detention_cases(
    records: list[dict[str, Any]],
    *,
    max_examples: int = 50,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Prepare summaries, bench inputs, and excluded-sensitive rows.

    Returns (included_summaries, bench_inputs, excluded_rows).
    """
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    bench: list[dict[str, Any]] = []

    idx = 0
    for record in records:
        idx += 1
        row = _normalize_input_record(record, idx)
        if row is None:
            continue

        if not row["is_detention_related"]:
            continue

        if row["excluded_sensitive"]:
            excluded.append(row)
            continue

        if len(included) >= max_examples:
            break

        included.append(row)
        bench.append(_to_bench_input(row))

    return included, bench, excluded


def write_outputs(
    included: list[dict[str, Any]],
    bench: list[dict[str, Any]],
    excluded: list[dict[str, Any]],
    output_dir: Path,
    *,
    source_note: str = "",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_path = output_dir / "raw_real_detention_examples.jsonl"
    csv_path = output_dir / "detention_case_summaries.csv"
    jsonl_path = output_dir / "detention_case_summaries.jsonl"
    bench_path = output_dir / "detention_bench_inputs.csv"
    domain_path = output_dir / "detention_domain_summary.csv"
    excluded_path = output_dir / "detention_excluded_sensitive.csv"
    manifest_path = output_dir / "detention_source_manifest.json"

    with open(raw_path, "w", encoding="utf-8") as fh:
        for row in included + excluded:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    df = pd.DataFrame(included)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    with open(jsonl_path, "w", encoding="utf-8") as fh:
        for row in included:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    bench_df = pd.DataFrame(bench)
    bench_df.to_csv(bench_path, index=False, encoding="utf-8-sig")

    if len(df):
        domain_summary = (
            df.groupby("detention_subtype", dropna=False)
            .agg(
                n_examples=("detention_case_id", "count"),
                languages=("language", lambda s: ",".join(sorted(set(s)))),
            )
            .reset_index()
        )
    else:
        domain_summary = pd.DataFrame(columns=["detention_subtype", "n_examples", "languages"])
    domain_summary.to_csv(domain_path, index=False, encoding="utf-8-sig")

    excl_df = pd.DataFrame(excluded)
    excl_df.to_csv(excluded_path, index=False, encoding="utf-8-sig")

    manifest = sources_manifest()
    manifest.update(
        {
            "preparation_note": source_note or "Detention real-case preparation layer.",
            "n_included": len(included),
            "n_bench_inputs": len(bench),
            "n_excluded_sensitive": len(excluded),
            "normalized_domain": NORMALIZED_DOMAIN,
            "methodology": {
                "dataset_mode": DATASET_MODE_REAL,
                "counterfactual_strength": COUNTERFACTUAL_STRENGTH_NONE,
                "use_for_strict_bias_rates": False,
                "exclude_from_strict_bias_rates": True,
                "manual_review_required": True,
            },
        }
    )
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "raw": raw_path,
        "csv": csv_path,
        "jsonl": jsonl_path,
        "bench": bench_path,
        "domain_summary": domain_path,
        "excluded": excluded_path,
        "manifest": manifest_path,
    }


def run_preparation(
    *,
    source: str,
    output_dir: Path,
    input_path: Path | None = None,
    dataset_id: str = "manual_public_court_decision",
    max_examples: int = 50,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    note = ""

    if source == "local_jsonl":
        if input_path is None or not input_path.exists():
            raise FileNotFoundError(
                f"Local JSONL not found: {input_path}. "
                "Use tests/fixtures/detention_public_sample.jsonl for offline preparation."
            )
        records = load_local_jsonl(input_path)
    elif source == "huggingface":
        records = load_huggingface_dataset(dataset_id)
        if not records:
            note = (
                f"Hugging Face ingestion unavailable for {dataset_id}. "
                "Install `datasets`, ensure network access, or use --source local_jsonl."
            )
    else:
        raise ValueError(f"Unknown source: {source}")

    included, bench, excluded = prepare_detention_cases(records, max_examples=max_examples)
    paths = write_outputs(included, bench, excluded, output_dir, source_note=note)

    return {
        "n_included": len(included),
        "n_bench_inputs": len(bench),
        "n_excluded_sensitive": len(excluded),
        "paths": paths,
        "note": note,
        "source": source,
        "dataset_id": dataset_id,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare detention/remand real-case-inspired audit examples."
    )
    parser.add_argument(
        "--source",
        choices=["local_jsonl", "huggingface"],
        default="local_jsonl",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Local JSONL path (required for local_jsonl).",
    )
    parser.add_argument(
        "--dataset",
        default="manual_public_court_decision",
        help="Hugging Face dataset id when --source huggingface.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/real_cases/detention"),
    )
    parser.add_argument("--max-examples", type=int, default=50)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.source == "local_jsonl" and args.input is None:
        default_fixture = _project_root() / "tests" / "fixtures" / "detention_public_sample.jsonl"
        args.input = default_fixture

    if not default_sources_path().exists():
        logger.warning("Detention sources registry missing at %s", default_sources_path())

    result = run_preparation(
        source=args.source,
        output_dir=args.output_dir,
        input_path=args.input,
        dataset_id=args.dataset,
        max_examples=args.max_examples,
    )

    print(
        f"Prepared {result['n_included']} detention summaries, "
        f"{result['n_bench_inputs']} bench inputs, "
        f"{result['n_excluded_sensitive']} excluded-sensitive → {args.output_dir}"
    )
    if result["note"]:
        print(f"Note: {result['note']}")
    for key, path in result["paths"].items():
        print(f"  {key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
