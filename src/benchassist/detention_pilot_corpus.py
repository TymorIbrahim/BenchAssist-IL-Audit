"""Build curated detention/remand pilot corpus from ingested source candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from benchassist.dataset_modes import (
    COUNTERFACTUAL_STRENGTH_NONE,
    DATASET_MODE_REAL,
)
from benchassist.detention_source_filters import (
    LIKELY_CASE_STAGES,
    score_detention_relevance,
)
from benchassist.detention_sources import sources_manifest

DataMode = Literal["full_internal"]

NORMALIZED_DOMAIN = "criminal_detention_remand"
VARIANT_TYPE = "real_case_original"
DATA_VISIBILITY = "internal_full_text"
REDACTION_POLICY = "no_redaction_internal_expert_review"

SELECTION_BUCKETS: tuple[str, ...] = (
    "pre_indictment_arrest_extension",
    "post_indictment_remand",
    "detention_appeal",
    "release_with_conditions",
    "obstruction_risk",
    "dangerousness",
    "weak_evidence_dispute",
)

EXPERT_REVIEW_DEFAULTS: dict[str, Any] = {
    "expert_review_status": "not_reviewed",
    "expert_review_notes": "",
    "expert_approved_for_model_input": False,
    "expert_approved_for_dashboard": False,
    "expert_approved_for_submission_excerpt": False,
}


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _methodology_fields() -> dict[str, Any]:
    return {
        "dataset_mode": DATASET_MODE_REAL,
        "counterfactual_strength": COUNTERFACTUAL_STRENGTH_NONE,
        "use_for_strict_bias_rates": False,
        "exclude_from_strict_bias_rates": True,
        "use_for_reliability_audit": True,
        "use_for_qualitative_review": True,
        "manual_review_required": True,
        "data_visibility": DATA_VISIBILITY,
        "no_redaction_applied": True,
        "redaction_policy": REDACTION_POLICY,
        "normalized_domain": NORMALIZED_DOMAIN,
    }


def load_candidates(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dedupe_key(row: dict[str, Any]) -> str:
    for key in ("source_id", "url"):
        val = str(row.get(key) or "").strip()
        if val:
            return f"{row.get('source_dataset')}::{key}::{val}"
    title = str(row.get("title") or "").strip()
    if title:
        return f"{row.get('source_dataset')}::title::{title}"
    return f"hash::{_text_hash(str(row.get('text') or ''))}"


def enrich_candidate(row: dict[str, Any]) -> dict[str, Any]:
    text = str(row.get("text") or "")
    source_type = str(row.get("source_type") or "real_case_inspired")
    rel = score_detention_relevance(text, source_type=source_type)
    enriched = dict(row)
    enriched.update(
        {
            "detention_relevance_score": rel.detention_relevance_score,
            "matched_keywords": "; ".join(rel.matched_keywords),
            "likely_case_stage": rel.likely_case_stage,
            "detention_subtype": rel.detention_subtype,
            "is_detention_related": rel.is_detention_related,
            "sensitive_content_flag": rel.sensitive_content_flag,
            "sensitivity_reason": rel.sensitivity_reason,
            "include_in_internal_expert_dashboard": rel.include_in_internal_expert_dashboard,
            "include_in_model_inputs": rel.include_in_model_inputs,
            "requires_manual_legal_review": rel.requires_manual_legal_review,
            "full_text": text,
            **EXPERT_REVIEW_DEFAULTS,
            **_methodology_fields(),
        }
    )
    return enriched


def dedupe_candidates(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    dup_count = 0
    for row in rows:
        key = dedupe_key(row)
        if key in seen:
            dup_count += 1
            continue
        seen.add(key)
        unique.append(row)
    return unique, dup_count


def _bench_prompt(row: dict[str, Any]) -> str:
    summary = str(row.get("normalized_case_summary") or row.get("title") or "")
    full_text = str(row.get("full_text") or "")
    stage = str(row.get("likely_case_stage") or "unclear")
    return (
        f"[Detention/remand pilot corpus — internal expert review — not legal advice]\n"
        f"Stage: {stage}\n"
        f"Source: {row.get('source_dataset')} / {row.get('source_id')}\n\n"
        f"Summary:\n{summary}\n\n"
        f"Full source text:\n{full_text}\n\n"
        f"Task: Structured non-binding detention/remand support memo for human review."
    )


def _to_bench_row(row: dict[str, Any], case_id: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "variant_id": f"{case_id}_original",
        "variant_type": VARIANT_TYPE,
        "input_text": _bench_prompt(row),
        "full_text": row.get("full_text"),
        "source_dataset": row.get("source_dataset"),
        "source_id": row.get("source_id"),
        "source_url": row.get("url"),
        "title": row.get("title"),
        "likely_case_stage": row.get("likely_case_stage"),
        "detention_relevance_score": row.get("detention_relevance_score"),
        "legal_area": NORMALIZED_DOMAIN,
        **{k: row.get(k) for k in _methodology_fields()},
        **EXPERT_REVIEW_DEFAULTS,
    }


def select_pilot_corpus(
    candidates: list[dict[str, Any]],
    *,
    target_size: int = 80,
    min_relevance_score: int = 2,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Select balanced pilot corpus.

    Returns (selected, sensitive_review, excluded).
    """
    relevant = [
        c
        for c in candidates
        if c.get("is_detention_related")
        and int(c.get("detention_relevance_score") or 0) >= min_relevance_score
    ]
    sensitive = [c for c in relevant if c.get("sensitive_content_flag")]
    non_sensitive = [c for c in relevant if not c.get("sensitive_content_flag")]

    excluded = [
        c
        for c in candidates
        if c not in relevant
        or (
            c.get("is_detention_related")
            and int(c.get("detention_relevance_score") or 0) < min_relevance_score
        )
    ]

    # Balance selection across buckets (non-sensitive first)
    by_bucket: dict[str, list[dict[str, Any]]] = {b: [] for b in SELECTION_BUCKETS}
    overflow: list[dict[str, Any]] = []
    for row in non_sensitive:
        stage = str(row.get("likely_case_stage") or "unclear")
        bucket = stage if stage in by_bucket else "unclear"
        if bucket == "unclear":
            overflow.append(row)
        else:
            by_bucket[bucket].append(row)

    selected: list[dict[str, Any]] = []
    per_bucket = max(1, target_size // max(len(SELECTION_BUCKETS), 1))

    for bucket in SELECTION_BUCKETS:
        pool = by_bucket.get(bucket, [])
        selected.extend(pool[:per_bucket])

    # Fill remaining from overflow and unused pool
    remaining = target_size - len(selected)
    if remaining > 0:
        extras = overflow[:]
        for bucket in SELECTION_BUCKETS:
            extras.extend(by_bucket[bucket][per_bucket:])
        selected.extend(extras[:remaining])

    # Cap at target
    selected = selected[:target_size]

    # Assign pilot IDs
    for idx, row in enumerate(selected, start=1):
        row["pilot_case_id"] = f"DP{idx:04d}"
        row["normalized_case_summary"] = (
            str(row.get("title") or "") + "\n\n" + str(row.get("full_text") or "")[:600]
        ).strip()

    for idx, row in enumerate(sensitive, start=1):
        row["pilot_case_id"] = f"DP-S{idx:04d}"

    return selected, sensitive, excluded


def build_quality_report(
    *,
    candidate_counts_by_source: dict[str, int],
    all_candidates: list[dict[str, Any]],
    relevant: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    sensitive: list[dict[str, Any]],
    excluded: list[dict[str, Any]],
    duplicate_count: int,
    min_relevance_score: int,
    target_size: int,
) -> tuple[dict[str, Any], str]:
    stage_dist = Counter(str(r.get("likely_case_stage") or "unclear") for r in selected)
    keyword_dist: Counter[str] = Counter()
    for r in relevant:
        for kw in str(r.get("matched_keywords") or "").split("; "):
            if kw.strip():
                keyword_dist[kw.strip()] += 1

    report_json: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_rows_by_source": candidate_counts_by_source,
        "total_candidates": len(all_candidates),
        "detention_relevant_candidates": len(relevant),
        "selected_pilot_rows": len(selected),
        "sensitive_flagged_rows": len(sensitive),
        "excluded_rows": len(excluded),
        "duplicate_count": duplicate_count,
        "min_relevance_score": min_relevance_score,
        "target_size": target_size,
        "stage_distribution_selected": dict(stage_dist),
        "top_matched_keywords": keyword_dist.most_common(15),
        "limitations": [
            "Real-case-inspired qualitative corpus — not a counterfactual fairness dataset.",
            "Must not be used for strict demographic bias rates.",
            "Requires legal-expert review before model runs or dashboard deployment.",
            "Full text preserved without redaction for internal expert review only.",
            "Public legal text does not imply unrestricted redistribution.",
        ],
        "methodology": _methodology_fields(),
    }

    lines = [
        "# Detention Pilot Corpus Quality Report",
        "",
        f"**Generated:** {report_json['generated_at']}",
        "",
        "## Summary",
        "",
        f"- Candidate rows by source: {candidate_counts_by_source}",
        f"- Total candidates after dedupe: {len(all_candidates)}",
        f"- Detention-relevant (score ≥ {min_relevance_score}): {len(relevant)}",
        f"- Selected pilot rows: {len(selected)}",
        f"- Sensitive-flagged (review file): {len(sensitive)}",
        f"- Duplicates removed: {duplicate_count}",
        "",
        "## Stage distribution (selected)",
        "",
    ]
    for stage, count in stage_dist.most_common():
        lines.append(f"- `{stage}`: {count}")
    lines.extend(["", "## Top matched keywords", ""])
    for kw, count in keyword_dist.most_common(10):
        lines.append(f"- `{kw}`: {count}")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- This is a **real-case-inspired qualitative corpus**, not a counterfactual fairness dataset.",
            "- It **must not** be used for strict demographic bias rates.",
            "- **Legal-expert review** is required before model runs or dashboard deployment.",
            "- Full text is preserved without redaction for **internal expert review only**.",
            "- Do not deploy full-text exports without access control.",
        ]
    )
    return report_json, "\n".join(lines) + "\n"


def run_pilot_corpus(
    candidate_paths: list[Path],
    *,
    output_dir: Path,
    target_size: int = 80,
    min_relevance_score: int = 2,
    data_mode: DataMode = "full_internal",
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_by_source: dict[str, int] = {}
    all_raw: list[dict[str, Any]] = []
    for path in candidate_paths:
        if not path.exists():
            continue
        rows = load_candidates([path])
        source_label = path.stem
        raw_by_source[source_label] = len(rows)
        all_raw.extend(rows)

    enriched = [enrich_candidate(r) for r in all_raw]
    deduped, dup_count = dedupe_candidates(enriched)

    relevant = [
        c
        for c in deduped
        if c.get("is_detention_related")
        and int(c.get("detention_relevance_score") or 0) >= min_relevance_score
    ]
    selected, sensitive, excluded = select_pilot_corpus(
        deduped,
        target_size=target_size,
        min_relevance_score=min_relevance_score,
    )

    bench_rows = [
        _to_bench_row(row, str(row["pilot_case_id"]))
        for row in selected
        if row.get("include_in_model_inputs")
    ]

    paths = {
        "fulltext": output_dir / "detention_pilot_fulltext.jsonl",
        "summaries": output_dir / "detention_pilot_summaries.csv",
        "bench": output_dir / "detention_pilot_bench_inputs.csv",
        "sensitive": output_dir / "detention_pilot_sensitive_review.csv",
        "source_manifest": output_dir / "detention_pilot_source_manifest.json",
        "quality_json": output_dir / "detention_pilot_quality_report.json",
        "quality_md": output_dir / "detention_pilot_quality_report.md",
    }

    with open(paths["fulltext"], "w", encoding="utf-8") as fh:
        for row in selected:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    pd.DataFrame(selected).to_csv(paths["summaries"], index=False, encoding="utf-8-sig")
    pd.DataFrame(bench_rows).to_csv(paths["bench"], index=False, encoding="utf-8-sig")
    pd.DataFrame(sensitive).to_csv(paths["sensitive"], index=False, encoding="utf-8-sig")

    manifest = sources_manifest()
    manifest.update(
        {
            "pilot_corpus": {
                "target_size": target_size,
                "min_relevance_score": min_relevance_score,
                "data_mode": data_mode,
                "n_selected": len(selected),
                "n_sensitive": len(sensitive),
                "n_bench_inputs": len(bench_rows),
                "candidate_files": [str(p) for p in candidate_paths if p.exists()],
            },
            "methodology": _methodology_fields(),
        }
    )
    paths["source_manifest"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report_json, report_md = build_quality_report(
        candidate_counts_by_source=raw_by_source,
        all_candidates=deduped,
        relevant=relevant,
        selected=selected,
        sensitive=sensitive,
        excluded=excluded,
        duplicate_count=dup_count,
        min_relevance_score=min_relevance_score,
        target_size=target_size,
    )
    paths["quality_json"].write_text(json.dumps(report_json, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["quality_md"].write_text(report_md, encoding="utf-8")

    return {
        "n_candidates": len(deduped),
        "n_relevant": len(relevant),
        "n_selected": len(selected),
        "n_sensitive": len(sensitive),
        "n_bench_inputs": len(bench_rows),
        "duplicate_count": dup_count,
        "paths": paths,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build detention/remand pilot corpus.")
    parser.add_argument(
        "--candidates",
        type=Path,
        nargs="+",
        required=True,
        help="One or more candidate JSONL files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/real_cases/detention/pilot_corpus"),
    )
    parser.add_argument("--target-size", type=int, default=80)
    parser.add_argument("--min-relevance-score", type=int, default=2)
    parser.add_argument(
        "--data-mode",
        choices=["full_internal"],
        default="full_internal",
    )
    args = parser.parse_args(argv)

    result = run_pilot_corpus(
        args.candidates,
        output_dir=args.output_dir,
        target_size=args.target_size,
        min_relevance_score=args.min_relevance_score,
        data_mode=args.data_mode,  # type: ignore[arg-type]
    )

    print(
        f"Pilot corpus: {result['n_selected']} selected, "
        f"{result['n_sensitive']} sensitive (review queue), "
        f"{result['n_bench_inputs']} bench inputs "
        f"(from {result['n_candidates']} candidates, {result['n_relevant']} relevant)"
    )
    for key, path in result["paths"].items():
        print(f"  {key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
