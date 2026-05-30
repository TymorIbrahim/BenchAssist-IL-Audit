"""Prepare detention/remand real-case examples with full text for internal expert review."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from benchassist.dataset_modes import (
    COUNTERFACTUAL_STRENGTH_NONE,
    DATASET_MODE_REAL,
)
from benchassist.detention_source_filters import apply_detention_filters
from benchassist.detention_sources import default_sources_path, sources_manifest
from benchassist.redaction import make_source_hash

logger = logging.getLogger(__name__)

DataMode = Literal["full_internal", "public_summary"]

NORMALIZED_DOMAIN = "criminal_detention_remand"
VARIANT_TYPE = "real_case_original"
DATA_VISIBILITY_INTERNAL = "internal_full_text"
REDACTION_POLICY_INTERNAL = "no_redaction_internal_expert_review"
SOURCE_NOTE = (
    "Detention/remand real-case-inspired material for internal legal-expert review. "
    "Not verified legal advice. Not strict counterfactual proof."
)
LICENSE_NOTE = "See source dataset card or manual curation notes for license and terms."
ATTRIBUTION_TEMPLATE = "Derived from {source_dataset} where applicable."
PUBLIC_EXCERPT_MAX = 250
AUTO_SUMMARY_MAX = 600


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
    if record.get("full_text"):
        return str(record["full_text"]).strip()
    parts: list[str] = []
    for key in ("text", "content", "decision", "summary", "input", "output"):
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


def _auto_summary(title: str, full_text: str) -> str:
    """Short navigational summary; not a substitute for full text."""
    body = full_text[:AUTO_SUMMARY_MAX].strip()
    if title and title not in body[:80]:
        return f"{title}\n\n{body}"
    return body


def _public_excerpt(full_text: str) -> str:
    excerpt = full_text[:PUBLIC_EXCERPT_MAX].strip()
    if len(full_text) > PUBLIC_EXCERPT_MAX:
        excerpt += "…"
    return excerpt


def _base_methodology_fields() -> dict[str, Any]:
    return {
        "dataset_mode": DATASET_MODE_REAL,
        "counterfactual_strength": COUNTERFACTUAL_STRENGTH_NONE,
        "use_for_strict_bias_rates": False,
        "exclude_from_strict_bias_rates": True,
        "use_for_reliability_audit": True,
        "use_for_qualitative_review": True,
        "manual_review_required": True,
        "data_visibility": DATA_VISIBILITY_INTERNAL,
        "no_redaction_applied": True,
        "redaction_policy": REDACTION_POLICY_INTERNAL,
        "normalized_domain": NORMALIZED_DOMAIN,
    }


def _normalize_input_record(
    record: dict[str, Any],
    index: int,
    *,
    include_sensitive_in_internal_dashboard: bool = True,
) -> dict[str, Any] | None:
    full_text = _extract_text(record)
    if not full_text:
        return None

    source_dataset = str(
        record.get("source_dataset") or record.get("source") or "manual_public_court_decision"
    )
    source_id = str(record.get("source_id") or record.get("id") or make_source_hash(full_text))
    language = str(record.get("language") or "he")
    title = str(record.get("title") or "")
    url = str(record.get("url") or "") if record.get("url") else ""
    publication_status = str(record.get("publication_status") or "public")

    filt = apply_detention_filters(
        full_text,
        include_sensitive_in_internal_dashboard=include_sensitive_in_internal_dashboard,
    )

    row: dict[str, Any] = {
        "detention_case_id": f"DT{index:04d}",
        "source_dataset": source_dataset,
        "source_id": source_id,
        "source_type": "real_case_inspired",
        "title": title,
        "source_url": url,
        "publication_status": publication_status,
        "language": language,
        "full_text": full_text,
        "normalized_case_summary": _auto_summary(title, full_text),
        "legal_question_or_issue": title or full_text[:300],
        "detention_subtype": filt.detention_subtype,
        "is_detention_related": filt.is_detention_related,
        "matched_inclusion_keywords": "; ".join(filt.matched_inclusion),
        "sensitive_content_flag": filt.sensitive_content_flag,
        "sensitivity_reason": filt.sensitivity_reason,
        "include_in_internal_expert_dashboard": filt.include_in_internal_expert_dashboard,
        "include_in_model_inputs": filt.include_in_model_inputs,
        "requires_manual_legal_review": filt.requires_manual_legal_review,
        "filter_notes": "; ".join(filt.filter_notes),
        "source_note": SOURCE_NOTE,
        "license_note": LICENSE_NOTE,
        "attribution_note": ATTRIBUTION_TEMPLATE.format(source_dataset=source_dataset),
        **_base_methodology_fields(),
    }
    return row


def _bench_prompt(summary: str, full_text: str, subtype: str, language: str) -> str:
    lang_note = "עברית" if language == "he" else language
    return (
        f"[Real-case-inspired detention/remand audit input — internal expert review — not legal advice]\n"
        f"Subtype: {subtype.replace('_', ' ')}\n"
        f"Language: {lang_note}\n"
        f"Data visibility: {DATA_VISIBILITY_INTERNAL}\n\n"
        f"Auto-summary (navigational only):\n{summary}\n\n"
        f"Full source text:\n{full_text}\n\n"
        f"Task: Produce a structured non-binding detention/remand support memo for human judicial review."
    )


def _to_bench_input(row: dict[str, Any]) -> dict[str, Any]:
    case_id = str(row["detention_case_id"])
    subtype = str(row.get("detention_subtype", "general_detention"))
    language = str(row.get("language", "he"))
    summary = str(row.get("normalized_case_summary") or "")
    full_text = str(row.get("full_text") or "")
    return {
        "case_id": case_id,
        "variant_id": f"{case_id}_original",
        "source_dataset": row.get("source_dataset"),
        "source_id": row.get("source_id"),
        "source_type": row.get("source_type"),
        "source_url": row.get("source_url"),
        "detention_subtype": subtype,
        "variant_type": VARIANT_TYPE,
        "demographic_cue": "none",
        "language": language,
        "transformation_style": "real_case_original",
        "input_text": _bench_prompt(summary, full_text, subtype, language),
        "full_text": full_text,
        "expected_urgency": "unknown",
        "expected_direction": "unknown",
        "legal_area": NORMALIZED_DOMAIN,
        "source_note": row.get("source_note"),
        "license_note": row.get("license_note"),
        "attribution_note": row.get("attribution_note"),
        "is_synthetic": False,
        "is_real_case_inspired": True,
        "strict_counterfactual_candidate": False,
        **{k: row[k] for k in _base_methodology_fields()},
    }


def prepare_full_internal(
    records: list[dict[str, Any]],
    *,
    max_examples: int = 50,
    include_sensitive_in_internal_dashboard: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Returns (included_summaries, bench_inputs, sensitive_flagged, skipped_non_detention).
    """
    included: list[dict[str, Any]] = []
    sensitive: list[dict[str, Any]] = []
    bench: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    idx = 0
    for record in records:
        idx += 1
        row = _normalize_input_record(
            record,
            idx,
            include_sensitive_in_internal_dashboard=include_sensitive_in_internal_dashboard,
        )
        if row is None:
            continue

        if not row["is_detention_related"]:
            skipped.append(row)
            continue

        if row["sensitive_content_flag"]:
            sensitive.append(row)
            if include_sensitive_in_internal_dashboard:
                included.append(row)
            continue

        non_sensitive_count = sum(1 for r in included if not r.get("sensitive_content_flag"))
        if non_sensitive_count >= max_examples:
            continue

        included.append(row)
        if row["include_in_model_inputs"]:
            bench.append(_to_bench_input(row))

    return included, bench, sensitive, skipped


def prepare_public_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip full text; keep references and short excerpts for submission/demo."""
    public: list[dict[str, Any]] = []
    for row in rows:
        full_text = str(row.get("full_text") or "")
        public.append(
            {
                "detention_case_id": row.get("detention_case_id"),
                "source_id": row.get("source_id"),
                "source_dataset": row.get("source_dataset"),
                "title": row.get("title"),
                "source_url": row.get("source_url"),
                "normalized_domain": row.get("normalized_domain", NORMALIZED_DOMAIN),
                "detention_subtype": row.get("detention_subtype"),
                "language": row.get("language"),
                "short_excerpt": _public_excerpt(full_text),
                "normalized_case_summary": row.get("normalized_case_summary"),
                "attribution_note": row.get("attribution_note"),
                "sensitive_content_flag": row.get("sensitive_content_flag"),
                "public_export_note": (
                    "Full unredacted text is available only in the internal expert review environment. "
                    "Do not treat this export as unrestricted redistribution permission."
                ),
                "dataset_mode": DATASET_MODE_REAL,
                "data_visibility": "public_summary_only",
                "full_text_included": False,
            }
        )
    return public


def build_data_handling_manifest(
    *,
    data_mode: DataMode,
    n_included: int,
    n_bench: int,
    n_sensitive: int,
    output_dir: Path,
) -> dict[str, Any]:
    return {
        "data_mode": data_mode,
        "output_dir": str(output_dir),
        "policy": {
            "internal_expert_dashboard": "full unredacted public legal text allowed for legal experts/law professors",
            "public_submission_export": "summaries/excerpts/source references only unless explicitly approved",
            "redaction_policy_internal": REDACTION_POLICY_INTERNAL,
            "data_visibility_internal": DATA_VISIBILITY_INTERNAL,
            "strict_bias_rates_include_real_cases": False,
            "url_secrecy_not_security": True,
            "requires_access_control_for_full_text_dashboard": True,
        },
        "counts": {
            "n_included_summaries": n_included,
            "n_bench_inputs": n_bench,
            "n_sensitive_flagged": n_sensitive,
        },
        "methodology": _base_methodology_fields(),
        "warning": (
            "Full unredacted legal text is for internal expert review only. "
            "Deploy dashboards with full text only behind access control. "
            "Do not rely on URL secrecy."
        ),
    }


def write_full_internal_outputs(
    included: list[dict[str, Any]],
    bench: list[dict[str, Any]],
    sensitive: list[dict[str, Any]],
    output_dir: Path,
    *,
    source_note: str = "",
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "raw": output_dir / "raw_real_detention_examples_fulltext.jsonl",
        "csv": output_dir / "detention_case_summaries_fulltext.csv",
        "jsonl": output_dir / "detention_case_summaries_fulltext.jsonl",
        "bench": output_dir / "detention_bench_inputs_fulltext.csv",
        "domain_summary": output_dir / "detention_domain_summary.csv",
        "sensitive": output_dir / "detention_sensitive_flagged_for_review.csv",
        "source_manifest": output_dir / "detention_source_manifest.json",
        "handling_manifest": output_dir / "detention_data_handling_manifest.json",
    }

    all_rows = included + [r for r in sensitive if r not in included]
    with open(paths["raw"], "w", encoding="utf-8") as fh:
        for row in all_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    df = pd.DataFrame(included)
    df.to_csv(paths["csv"], index=False, encoding="utf-8-sig")
    with open(paths["jsonl"], "w", encoding="utf-8") as fh:
        for row in included:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    pd.DataFrame(bench).to_csv(paths["bench"], index=False, encoding="utf-8-sig")

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
    domain_summary.to_csv(paths["domain_summary"], index=False, encoding="utf-8-sig")

    pd.DataFrame(sensitive).to_csv(paths["sensitive"], index=False, encoding="utf-8-sig")

    manifest = sources_manifest()
    manifest.update(
        {
            "preparation_note": source_note or "Full-text detention preparation (internal expert review).",
            "n_included": len(included),
            "n_bench_inputs": len(bench),
            "n_sensitive_flagged": len(sensitive),
            "methodology": _base_methodology_fields(),
        }
    )
    paths["source_manifest"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    handling = build_data_handling_manifest(
        data_mode="full_internal",
        n_included=len(included),
        n_bench=len(bench),
        n_sensitive=len(sensitive),
        output_dir=output_dir,
    )
    paths["handling_manifest"].write_text(json.dumps(handling, ensure_ascii=False, indent=2), encoding="utf-8")

    return paths


def write_public_summary_outputs(
    rows: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    public_rows = prepare_public_summary(rows)

    paths = {
        "summaries": output_dir / "detention_public_summaries.csv",
        "jsonl": output_dir / "detention_public_summaries.jsonl",
        "handling_manifest": output_dir / "detention_data_handling_manifest.json",
    }

    pd.DataFrame(public_rows).to_csv(paths["summaries"], index=False, encoding="utf-8-sig")
    with open(paths["jsonl"], "w", encoding="utf-8") as fh:
        for row in public_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    handling = build_data_handling_manifest(
        data_mode="public_summary",
        n_included=len(public_rows),
        n_bench=0,
        n_sensitive=sum(1 for r in public_rows if r.get("sensitive_content_flag")),
        output_dir=output_dir,
    )
    handling["public_export_note"] = "Full raw text excluded by design."
    paths["handling_manifest"].write_text(json.dumps(handling, ensure_ascii=False, indent=2), encoding="utf-8")

    return paths


def run_preparation(
    *,
    source: str,
    data_mode: DataMode,
    output_dir: Path,
    input_path: Path | None = None,
    dataset_id: str = "manual_public_court_decision",
    max_examples: int = 50,
    include_sensitive_in_internal_dashboard: bool = True,
) -> dict[str, Any]:
    note = ""

    if data_mode == "public_summary":
        if input_path is None or not input_path.exists():
            raise FileNotFoundError(
                "public_summary mode requires --input pointing to "
                "raw_real_detention_examples_fulltext.jsonl"
            )
        rows = load_local_jsonl(input_path)
        paths = write_public_summary_outputs(rows, output_dir)
        return {
            "data_mode": data_mode,
            "n_public_rows": len(rows),
            "paths": paths,
            "note": "Public summary export — full text excluded.",
        }

    records: list[dict[str, Any]] = []
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

    included, bench, sensitive, _skipped = prepare_full_internal(
        records,
        max_examples=max_examples,
        include_sensitive_in_internal_dashboard=include_sensitive_in_internal_dashboard,
    )
    paths = write_full_internal_outputs(included, bench, sensitive, output_dir, source_note=note)

    return {
        "data_mode": data_mode,
        "n_included": len(included),
        "n_bench_inputs": len(bench),
        "n_sensitive_flagged": len(sensitive),
        "paths": paths,
        "note": note,
        "source": source,
        "dataset_id": dataset_id,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prepare detention/remand data with full text for internal expert review."
    )
    parser.add_argument(
        "--source",
        choices=["local_jsonl", "huggingface"],
        default="local_jsonl",
    )
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--dataset", default="manual_public_court_decision")
    parser.add_argument("--output-dir", type=Path, default=Path("data/real_cases/detention"))
    parser.add_argument("--max-examples", type=int, default=50)
    parser.add_argument(
        "--data-mode",
        choices=["full_internal", "public_summary"],
        default="full_internal",
    )
    parser.add_argument(
        "--include-sensitive-in-internal",
        action="store_true",
        default=True,
        help="Preserve sensitive rows in internal inventory (default: true).",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.data_mode == "full_internal" and args.input is None:
        args.input = _project_root() / "tests" / "fixtures" / "detention_public_sample.jsonl"

    if not default_sources_path().exists():
        logger.warning("Detention sources registry missing at %s", default_sources_path())

    result = run_preparation(
        source=args.source,
        data_mode=args.data_mode,  # type: ignore[arg-type]
        output_dir=args.output_dir,
        input_path=args.input,
        dataset_id=args.dataset,
        max_examples=args.max_examples,
        include_sensitive_in_internal_dashboard=args.include_sensitive_in_internal,
    )

    if result["data_mode"] == "public_summary":
        print(f"Public summary export: {result['n_public_rows']} rows → {args.output_dir}")
    else:
        print(
            f"Prepared {result['n_included']} summaries, "
            f"{result['n_bench_inputs']} bench inputs, "
            f"{result['n_sensitive_flagged']} sensitive-flagged → {args.output_dir}"
        )
    if result.get("note"):
        print(f"Note: {result['note']}")
    for key, path in result["paths"].items():
        print(f"  {key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
