"""Ingest public/licensed Israeli legal training examples into real-case summaries."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

from benchassist.dataset_modes import (
    DATASET_MODE_REAL,
    REAL_CASE_ATTRIBUTION,
    REAL_CASE_LICENSE_NOTE,
    REAL_CASE_SOURCE_DATASET,
)
from benchassist.domain_taxonomy import (
    NORMALIZED_DOMAINS,
    detect_language,
    is_default_demo_domain,
    resolve_domain,
)
from benchassist.redaction import make_source_hash, redact_text

logger = logging.getLogger(__name__)

LICENSE_NOTE = REAL_CASE_LICENSE_NOTE
ATTRIBUTION_NOTE = REAL_CASE_ATTRIBUTION


def _extract_messages(record: dict[str, Any]) -> tuple[str, str]:
    """Extract user question and assistant answer from flexible record shapes."""
    user_parts: list[str] = []
    assistant_parts: list[str] = []

    messages = record.get("messages")
    if isinstance(messages, list):
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            role = str(msg.get("role", "")).lower()
            content = str(msg.get("content", "") or "").strip()
            if not content:
                continue
            if role in {"user", "human", "instruction"}:
                user_parts.append(content)
            elif role in {"assistant", "model", "output"}:
                assistant_parts.append(content)

    for key in ("instruction", "input", "question", "prompt"):
        val = record.get(key)
        if val and str(val).strip():
            user_parts.append(str(val).strip())
    for key in ("output", "answer", "response"):
        val = record.get(key)
        if val and str(val).strip():
            assistant_parts.append(str(val).strip())

    user_text = "\n".join(user_parts).strip()
    assistant_text = "\n".join(assistant_parts).strip()
    return user_text, assistant_text


def _normalize_record(record: dict[str, Any], index: int) -> dict[str, Any] | None:
    user_text, assistant_text = _extract_messages(record)
    combined = f"{user_text}\n{assistant_text}".strip()
    if not combined:
        return None

    red_user = redact_text(user_text)
    red_combined = redact_text(combined)
    original_domain = str(record.get("domain") or record.get("legal_area") or record.get("category") or "")
    normalized_domain = resolve_domain(original_domain, combined)
    language = detect_language(combined)
    source_id = str(record.get("id") or record.get("source_id") or make_source_hash(combined))
    source_dataset = str(record.get("source_dataset") or record.get("source") or REAL_CASE_SOURCE_DATASET)
    source_type = str(record.get("source_type") or "public_licensed_training")

    excerpt = red_combined.text[:400]
    issue = red_user.text[:500] if red_user.text else excerpt[:500]
    summary = red_combined.text[:1200]

    pii_notes = "; ".join(red_user.notes + red_combined.notes)
    contains_pii = bool(red_user.detected or red_combined.detected)

    return {
        "real_case_id": f"RC{index:04d}",
        "source_dataset": source_dataset,
        "source_id": source_id,
        "source_type": source_type,
        "original_domain": original_domain,
        "normalized_domain": normalized_domain,
        "language": language,
        "source_text_excerpt": excerpt,
        "legal_question_or_issue": issue,
        "normalized_case_summary": summary,
        "requested_remedy_or_issue": issue[:300],
        "likely_legal_area": normalized_domain,
        "source_note": "Source-derived summary for audit realism. Not verified legal advice.",
        "license_note": LICENSE_NOTE,
        "attribution_note": ATTRIBUTION_NOTE,
        "contains_possible_personal_data": contains_pii,
        "pii_redaction_notes": pii_notes or "None detected by heuristic redaction.",
        "use_for_counterfactual_audit": False,
        "use_for_reliability_audit": True,
        "use_for_qualitative_review": True,
        "dataset_mode": DATASET_MODE_REAL,
        "assistant_excerpt": assistant_text[:400] if assistant_text else "",
    }


def load_local_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def load_huggingface_dataset(dataset_id: str, split: str = "train") -> list[dict[str, Any]]:
    """Load from Hugging Face; returns empty list if unavailable."""
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


def ingest_records(
    records: list[dict[str, Any]],
    *,
    max_per_domain: int = 30,
    allowed_domains: tuple[str, ...] = NORMALIZED_DOMAINS,
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    domain_counts: dict[str, int] = {d: 0 for d in allowed_domains}

    for idx, record in enumerate(records, start=1):
        row = _normalize_record(record, idx)
        if row is None:
            continue
        domain = row["normalized_domain"]
        if domain not in allowed_domains:
            continue
        if not is_default_demo_domain(domain):
            continue
        if domain_counts.get(domain, 0) >= max_per_domain:
            continue
        summaries.append(row)
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

    return summaries


def write_outputs(summaries: list[dict[str, Any]], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "raw_real_case_examples.jsonl"
    csv_path = output_dir / "real_case_summaries.csv"
    jsonl_path = output_dir / "real_case_summaries.jsonl"
    domain_path = output_dir / "real_case_domain_summary.csv"

    with open(raw_path, "w", encoding="utf-8") as fh:
        for row in summaries:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    df = pd.DataFrame(summaries)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    with open(jsonl_path, "w", encoding="utf-8") as fh:
        for row in summaries:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    if len(df):
        domain_summary = (
            df.groupby("normalized_domain", dropna=False)
            .agg(n_examples=("real_case_id", "count"), languages=("language", lambda s: ",".join(sorted(set(s)))))
            .reset_index()
        )
    else:
        domain_summary = pd.DataFrame(columns=["normalized_domain", "n_examples", "languages"])
    domain_summary.to_csv(domain_path, index=False, encoding="utf-8-sig")

    return {
        "raw": raw_path,
        "csv": csv_path,
        "jsonl": jsonl_path,
        "domain_summary": domain_path,
    }


def run_ingestion(
    *,
    source: str,
    output_dir: Path,
    dataset_id: str = REAL_CASE_SOURCE_DATASET,
    input_path: Path | None = None,
    max_per_domain: int = 30,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    note = ""

    if source == "huggingface":
        records = load_huggingface_dataset(dataset_id)
        if not records:
            note = (
                "Hugging Face ingestion unavailable. Install `datasets` and ensure network access, "
                "or use --source local_jsonl with a downloaded JSONL file."
            )
    elif source == "local_jsonl":
        if input_path is None or not input_path.exists():
            raise FileNotFoundError(
                f"Local JSONL not found: {input_path}. "
                "Download Legal-Training-IL manually or use tests/fixtures/legal_training_sample.jsonl"
            )
        records = load_local_jsonl(input_path)
    else:
        raise ValueError(f"Unknown source: {source}")

    summaries = ingest_records(records, max_per_domain=max_per_domain)
    paths = write_outputs(summaries, output_dir)
    return {
        "n_ingested": len(summaries),
        "paths": paths,
        "note": note,
        "source": source,
        "dataset_id": dataset_id,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest real Israeli case-inspired legal examples.")
    parser.add_argument("--source", choices=["huggingface", "local_jsonl"], default="local_jsonl")
    parser.add_argument("--dataset-id", default=REAL_CASE_SOURCE_DATASET)
    parser.add_argument("--input", type=Path, default=None, help="Local JSONL path for local_jsonl source.")
    parser.add_argument("--output-dir", type=Path, default=Path("data/real_cases"))
    parser.add_argument("--max-per-domain", type=int, default=30)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = run_ingestion(
        source=args.source,
        output_dir=args.output_dir,
        dataset_id=args.dataset_id,
        input_path=args.input,
        max_per_domain=args.max_per_domain,
    )
    print(f"Ingested {result['n_ingested']} real-case summaries → {args.output_dir}")
    if result["note"]:
        print(f"Note: {result['note']}")
    for key, path in result["paths"].items():
        print(f"  {key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
