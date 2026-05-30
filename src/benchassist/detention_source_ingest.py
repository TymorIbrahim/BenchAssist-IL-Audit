"""Ingest Israeli detention/remand source material from local JSONL or Hugging Face."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

IngestionMethod = Literal["local_jsonl", "huggingface"]

# Datasets that require full parquet download before streaming; skip auto-ingest.
KNOWN_LARGE_HF_DATASETS: frozenset[str] = frozenset(
    {
        "LevMuchnik/SupremeCourtOfIsrael",
    }
)

TEXT_FIELD_CANDIDATES: tuple[str, ...] = (
    "text",
    "content",
    "judgment",
    "decision_text",
    "body",
    "decision",
    "summary",
    "prompt",
    "completion",
    "instruction",
    "output",
    "input",
    "answer",
    "response",
)

TITLE_FIELD_CANDIDATES: tuple[str, ...] = (
    "title",
    "name",
    "case_name",
    "subject",
)

URL_FIELD_CANDIDATES: tuple[str, ...] = (
    "url",
    "source_url",
    "link",
    "uri",
)

ID_FIELD_CANDIDATES: tuple[str, ...] = (
    "source_id",
    "id",
    "case_id",
    "document_id",
    "doc_id",
)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _first_nonempty(record: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        val = record.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def _extract_messages(record: dict[str, Any]) -> tuple[str, str]:
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
    user = "\n".join(user_parts).strip()
    assistant = "\n".join(assistant_parts).strip()
    return user, assistant


def extract_full_text(record: dict[str, Any]) -> str:
    """Robustly extract full text from heterogeneous record shapes."""
    if record.get("full_text"):
        return str(record["full_text"]).strip()

    parts: list[str] = []
    for key in TEXT_FIELD_CANDIDATES:
        val = record.get(key)
        if val and str(val).strip():
            parts.append(str(val).strip())

    user, assistant = _extract_messages(record)
    if user:
        parts.append(user)
    if assistant:
        parts.append(assistant)

    metadata = record.get("metadata")
    if isinstance(metadata, dict):
        for key in TEXT_FIELD_CANDIDATES:
            val = metadata.get(key)
            if val and str(val).strip():
                parts.append(str(val).strip())

    # prompt/completion pair style
    prompt = _first_nonempty(record, ("prompt", "instruction", "question"))
    completion = _first_nonempty(record, ("completion", "output", "answer", "response"))
    if prompt and completion:
        combined = f"{prompt}\n\n{completion}".strip()
        if combined not in parts:
            parts.append(combined)

    seen: set[str] = set()
    unique: list[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return "\n\n".join(unique).strip()


def infer_source_type(source_dataset: str, record: dict[str, Any]) -> str:
    explicit = str(record.get("source_type") or "").strip()
    if explicit in {"legal_grounding", "background_statistics", "real_case_inspired"}:
        return explicit
    lower = source_dataset.lower()
    if "kolzchut" in lower or "law" in lower or "statute" in lower:
        return "legal_grounding"
    if "comptroller" in lower or "judicial_authority" in lower or "statistics" in lower:
        return "background_statistics"
    return "real_case_inspired"


def normalize_source_row(
    record: dict[str, Any],
    *,
    source_dataset: str,
    ingestion_method: IngestionMethod,
    index: int = 0,
) -> dict[str, Any] | None:
    """Normalize a raw record to the standard candidate format."""
    text = extract_full_text(record)
    if not text or len(text.strip()) < 20:
        return None

    source_id = _first_nonempty(record, ID_FIELD_CANDIDATES)
    if not source_id:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        source_id = f"auto_{digest}"

    title = _first_nonempty(record, TITLE_FIELD_CANDIDATES)
    url = _first_nonempty(record, URL_FIELD_CANDIDATES)
    language = str(record.get("language") or "he")
    publication_status = str(record.get("publication_status") or "public")
    dataset_name = str(record.get("source_dataset") or source_dataset)

    raw_metadata = {
        k: v
        for k, v in record.items()
        if k not in {"text", "content", "messages", "full_text"}
    }

    return {
        "source_dataset": dataset_name,
        "source_id": source_id,
        "title": title,
        "text": text,
        "url": url,
        "language": language,
        "publication_status": publication_status,
        "source_type": infer_source_type(dataset_name, record),
        "raw_metadata": raw_metadata,
        "ingested_at": _utc_now(),
        "ingestion_method": ingestion_method,
        "full_text_preserved": True,
        "candidate_index": index,
    }


def load_local_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Local JSONL not found: {path}")
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _load_huggingface_rows(
    dataset_id: str,
    *,
    split: str,
    scan_limit: int,
) -> tuple[list[dict[str, Any]], str | None]:
    """Inner HF loader (may block on large parquet downloads)."""
    from datasets import load_dataset  # type: ignore

    errors: list[str] = []
    for streaming in (True, False):
        try:
            ds = load_dataset(
                dataset_id,
                split=split,
                trust_remote_code=False,
                streaming=streaming,
            )
            rows: list[dict[str, Any]] = []
            for idx, row in enumerate(ds):
                if scan_limit and idx >= scan_limit:
                    break
                rows.append(dict(row))
            if rows:
                return rows, None
            errors.append(f"{'streaming' if streaming else 'non-streaming'} load returned 0 rows")
        except Exception as exc:
            errors.append(f"{'streaming' if streaming else 'non-streaming'}: {exc}")

    return [], " | ".join(errors)


class _HuggingFaceLoadTimeout(Exception):
    """Raised when HF dataset loading exceeds the configured alarm."""


def _hf_timeout_handler(signum: int, frame: Any) -> None:
    raise _HuggingFaceLoadTimeout()


def load_huggingface_dataset(
    dataset_id: str,
    *,
    split: str = "train",
    scan_limit: int = 200,
    timeout_seconds: int = 120,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Load Hugging Face dataset rows via streaming when possible.

    ``scan_limit`` is the maximum number of raw rows to iterate. Large parquet
    datasets may require a long first-byte wait; ``timeout_seconds`` bounds that wait.

    Returns (records, error_message). error_message is None on success.
    """
    try:
        from datasets import load_dataset  # type: ignore  # noqa: F401
    except ImportError:
        return [], (
            "Hugging Face `datasets` package not installed. "
            "Install with: pip install datasets"
        )

    if dataset_id in KNOWN_LARGE_HF_DATASETS:
        return [], (
            f"{dataset_id} is a large parquet corpus that requires a substantial download "
            "before rows are readable. For Sprint 2, export selected public decisions to "
            "data/manual_sources/detention_manual_public_cases.jsonl instead of auto-ingesting. "
            "See docs/detention_pilot_corpus.md."
        )

    previous_handler = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _hf_timeout_handler)
    signal.alarm(max(1, timeout_seconds))
    try:
        rows, inner_error = _load_huggingface_rows(
            dataset_id,
            split=split,
            scan_limit=scan_limit,
        )
    except _HuggingFaceLoadTimeout:
        return [], (
            f"Hugging Face load timed out after {timeout_seconds}s for {dataset_id}. "
            "The dataset may require a large parquet download. "
            "Use local JSONL manual cases or retry with a longer timeout."
        )
    except Exception as exc:
        return [], f"Hugging Face load error for {dataset_id}: {exc}"
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)

    if rows:
        return rows, None
    return [], (
        f"Hugging Face load failed for {dataset_id}. "
        + (inner_error or "Unknown error")
        + " Use local JSONL or retry when network/datasets are available."
    )


def write_failure_manifest(output: Path, *, dataset: str, error: str) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "status": "failed",
        "dataset": dataset,
        "error": error,
        "timestamp": _utc_now(),
        "note": "Ingestion skipped gracefully. Use local JSONL or retry when network/datasets available.",
    }
    path = output.with_suffix(".failure_manifest.json")
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def ingest_records(
    raw_records: list[dict[str, Any]],
    *,
    source_dataset: str,
    ingestion_method: IngestionMethod,
    max_examples: int | None = None,
    filter_detention: bool = False,
    min_detention_score: int = 1,
) -> list[dict[str, Any]]:
    from benchassist.detention_source_filters import score_detention_relevance

    normalized: list[dict[str, Any]] = []
    for idx, record in enumerate(raw_records, start=1):
        if max_examples is not None and len(normalized) >= max_examples:
            break
        row = normalize_source_row(
            record,
            source_dataset=source_dataset,
            ingestion_method=ingestion_method,
            index=idx,
        )
        if row is None:
            continue
        if filter_detention:
            relevance = score_detention_relevance(
                row["text"],
                source_type=row.get("source_type", "real_case_inspired"),
            )
            if relevance.detention_relevance_score < min_detention_score:
                continue
            row["ingest_detention_relevance_score"] = relevance.detention_relevance_score
            row["ingest_matched_keywords"] = relevance.matched_keywords
        normalized.append(row)
    return normalized


def write_candidates(rows: list[dict[str, Any]], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return output


def run_ingestion(
    *,
    source: str,
    output: Path,
    input_path: Path | None = None,
    dataset: str = "manual_public_court_decision",
    max_examples: int = 200,
    scan_limit: int | None = None,
    filter_detention: bool = False,
    min_detention_score: int = 1,
) -> dict[str, Any]:
    """Run ingestion and write candidate JSONL."""
    error: str | None = None
    raw: list[dict[str, Any]] = []
    effective_scan = scan_limit if scan_limit is not None else max_examples

    if source == "local_jsonl":
        if input_path is None:
            raise ValueError("--input is required for local_jsonl source")
        raw = load_local_jsonl(input_path)
        source_dataset = dataset or str(raw[0].get("source_dataset", "manual_public_court_decision")) if raw else dataset
        candidates = ingest_records(
            raw,
            source_dataset=source_dataset,
            ingestion_method="local_jsonl",
            max_examples=max_examples,
            filter_detention=filter_detention,
            min_detention_score=min_detention_score,
        )
    elif source == "huggingface":
        raw, error = load_huggingface_dataset(dataset, scan_limit=effective_scan)
        if error or not raw:
            manifest = write_failure_manifest(output, dataset=dataset, error=error or "No rows returned")
            return {
                "status": "failed",
                "n_candidates": 0,
                "output": output,
                "failure_manifest": manifest,
                "error": error or "No rows returned",
            }
        candidates = ingest_records(
            raw,
            source_dataset=dataset,
            ingestion_method="huggingface",
            max_examples=max_examples,
            filter_detention=filter_detention,
            min_detention_score=min_detention_score,
        )
    else:
        raise ValueError(f"Unknown source: {source}")

    path = write_candidates(candidates, output)
    return {
        "status": "success",
        "n_raw": len(raw),
        "n_candidates": len(candidates),
        "output": path,
        "error": error,
        "scan_limit": effective_scan,
        "filter_detention": filter_detention,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest detention/remand source candidates.")
    parser.add_argument("--source", choices=["local_jsonl", "huggingface"], default="local_jsonl")
    parser.add_argument("--input", type=Path, default=None, help="Local JSONL path.")
    parser.add_argument("--dataset", default="manual_public_court_decision", help="HF dataset id or source label.")
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output candidate JSONL path.",
    )
    parser.add_argument("--max-examples", type=int, default=200)
    parser.add_argument(
        "--scan-limit",
        type=int,
        default=None,
        help="HF rows to scan (default: --max-examples). Use a higher value with --filter-detention.",
    )
    parser.add_argument(
        "--filter-detention",
        action="store_true",
        help="Keep only rows matching detention/remand keywords (HF scan mode).",
    )
    parser.add_argument(
        "--min-detention-score",
        type=int,
        default=1,
        help="Minimum detention_relevance_score when --filter-detention is set.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    result = run_ingestion(
        source=args.source,
        output=args.output,
        input_path=args.input,
        dataset=args.dataset,
        max_examples=args.max_examples,
        scan_limit=args.scan_limit,
        filter_detention=args.filter_detention,
        min_detention_score=args.min_detention_score,
    )

    if result["status"] == "failed":
        print(f"INGESTION FAILED: {result['error']}")
        print(f"  Failure manifest: {result.get('failure_manifest')}")
        return 0  # graceful exit, not crash

    print(f"Ingested {result['n_candidates']} candidates (raw={result.get('n_raw', '?')}) → {result['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
