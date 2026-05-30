"""Tests for detention pilot corpus sprint 2."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES_FIXTURE = ROOT / "tests" / "fixtures" / "detention_source_candidates_sample.jsonl"
MANUAL_SOURCES = ROOT / "data" / "manual_sources" / "detention_manual_public_cases.jsonl"


def test_source_row_normalization() -> None:
    from benchassist.detention_source_ingest import normalize_source_row

    raw = {
        "instruction": "שאלה על מעצר",
        "output": "הארכת מעצר ימים בגין חשד סביר וראיות לכאורה.",
        "source_id": "norm_001",
        "title": "בדיקה",
    }
    row = normalize_source_row(
        raw,
        source_dataset="BrainboxAI/legal-training-il",
        ingestion_method="local_jsonl",
    )
    assert row is not None
    assert row["full_text_preserved"] is True
    assert "הארכת מעצר" in row["text"]
    assert row["source_id"] == "norm_001"
    assert row["ingestion_method"] == "local_jsonl"


def test_local_jsonl_ingestion(tmp_path: Path) -> None:
    from benchassist.detention_source_ingest import run_ingestion

    out = tmp_path / "candidates.jsonl"
    result = run_ingestion(
        source="local_jsonl",
        output=out,
        input_path=CANDIDATES_FIXTURE,
        max_examples=200,
    )
    assert result["status"] == "success"
    assert result["n_candidates"] >= 10
    assert out.exists()


def test_relevance_scoring() -> None:
    from benchassist.detention_source_filters import score_detention_relevance

    text = "התובע מבקש הארכת מעצר ימים. חשד סביר וראיות לכאורה."
    result = score_detention_relevance(text)
    assert result.is_detention_related
    assert result.detention_relevance_score >= 2
    assert len(result.matched_keywords) >= 2


def test_likely_case_stage_classification() -> None:
    from benchassist.detention_source_filters import score_detention_relevance

    remand = score_detention_relevance("המדינה מבקשת מעצר עד תום ההליכים. ראיות לכאורה.")
    assert remand.likely_case_stage == "post_indictment_remand"

    appeal = score_detention_relevance("ערעור על החלטת מעצר. הארכת מעצרו של החשוד.")
    assert appeal.likely_case_stage == "detention_appeal"


def test_sensitive_content_flagging() -> None:
    from benchassist.detention_source_filters import score_detention_relevance

    text = "בקשה להארכת מעצר ימים של קטין."
    result = score_detention_relevance(text)
    assert result.sensitive_content_flag
    assert result.include_in_model_inputs is False
    assert result.requires_manual_legal_review


def test_deduplication() -> None:
    from benchassist.detention_pilot_corpus import dedupe_candidates, enrich_candidate

    rows = [
        enrich_candidate({"source_dataset": "x", "source_id": "a", "text": "הארכת מעצר ימים. חשד סביר."}),
        enrich_candidate({"source_dataset": "x", "source_id": "a", "text": "הארכת מעצר ימים. חשד סביר."}),
    ]
    unique, dup_count = dedupe_candidates(rows)
    assert dup_count == 1
    assert len(unique) == 1


def test_pilot_corpus_creation(tmp_path: Path) -> None:
    from benchassist.detention_source_ingest import run_ingestion
    from benchassist.detention_pilot_corpus import run_pilot_corpus

    cand = tmp_path / "candidates.jsonl"
    run_ingestion(source="local_jsonl", output=cand, input_path=CANDIDATES_FIXTURE, max_examples=200)
    out = tmp_path / "pilot_corpus"
    result = run_pilot_corpus(
        [cand],
        output_dir=out,
        target_size=10,
        min_relevance_score=2,
    )
    assert result["n_selected"] >= 5
    assert (out / "detention_pilot_fulltext.jsonl").exists()
    assert (out / "detention_pilot_quality_report.md").exists()
    assert (out / "detention_pilot_quality_report.json").exists()


def test_full_text_preservation(tmp_path: Path) -> None:
    from benchassist.detention_source_ingest import run_ingestion
    from benchassist.detention_pilot_corpus import run_pilot_corpus

    cand = tmp_path / "candidates.jsonl"
    run_ingestion(source="local_jsonl", output=cand, input_path=CANDIDATES_FIXTURE, max_examples=200)
    out = tmp_path / "pilot_corpus"
    run_pilot_corpus([cand], output_dir=out, target_size=10, min_relevance_score=2)
    df = pd.read_csv(out / "detention_pilot_summaries.csv")
    assert "full_text" in df.columns
    assert df["no_redaction_applied"].all()
    assert (df["redaction_policy"] == "no_redaction_internal_expert_review").all()


def test_strict_bias_exclusion_fields(tmp_path: Path) -> None:
    from benchassist.detention_source_ingest import run_ingestion
    from benchassist.detention_pilot_corpus import run_pilot_corpus

    cand = tmp_path / "candidates.jsonl"
    run_ingestion(source="local_jsonl", output=cand, input_path=CANDIDATES_FIXTURE, max_examples=200)
    out = tmp_path / "pilot_corpus"
    run_pilot_corpus([cand], output_dir=out, target_size=10, min_relevance_score=2)
    df = pd.read_csv(out / "detention_pilot_summaries.csv")
    assert all(df["use_for_strict_bias_rates"] == False)  # noqa: E712
    assert all(df["exclude_from_strict_bias_rates"] == True)  # noqa: E712
    assert all(df["dataset_mode"] == "real_case_inspired")


def test_expert_review_defaults(tmp_path: Path) -> None:
    from benchassist.detention_source_ingest import run_ingestion
    from benchassist.detention_pilot_corpus import run_pilot_corpus

    cand = tmp_path / "candidates.jsonl"
    run_ingestion(source="local_jsonl", output=cand, input_path=CANDIDATES_FIXTURE, max_examples=200)
    out = tmp_path / "pilot_corpus"
    run_pilot_corpus([cand], output_dir=out, target_size=10, min_relevance_score=2)
    df = pd.read_csv(out / "detention_pilot_summaries.csv")
    assert all(df["expert_review_status"] == "not_reviewed")
    assert all(df["expert_approved_for_model_input"] == False)  # noqa: E712
    assert all(df["expert_approved_for_dashboard"] == False)  # noqa: E712


def test_sensitive_excluded_from_bench_inputs(tmp_path: Path) -> None:
    from benchassist.detention_source_ingest import run_ingestion
    from benchassist.detention_pilot_corpus import run_pilot_corpus

    cand = tmp_path / "candidates.jsonl"
    run_ingestion(source="local_jsonl", output=cand, input_path=CANDIDATES_FIXTURE, max_examples=200)
    out = tmp_path / "pilot_corpus"
    result = run_pilot_corpus([cand], output_dir=out, target_size=10, min_relevance_score=2)
    bench = pd.read_csv(out / "detention_pilot_bench_inputs.csv")
    sensitive = pd.read_csv(out / "detention_pilot_sensitive_review.csv")
    assert result["n_sensitive"] >= 2
    if len(bench):
        bench_ids = set(bench["case_id"].astype(str))
        sens_ids = set(sensitive["pilot_case_id"].astype(str))
        assert bench_ids.isdisjoint(sens_ids)


def test_quality_report_creation(tmp_path: Path) -> None:
    from benchassist.detention_source_ingest import run_ingestion
    from benchassist.detention_pilot_corpus import run_pilot_corpus

    cand = tmp_path / "candidates.jsonl"
    run_ingestion(source="local_jsonl", output=cand, input_path=CANDIDATES_FIXTURE, max_examples=200)
    out = tmp_path / "pilot_corpus"
    run_pilot_corpus([cand], output_dir=out, target_size=10, min_relevance_score=2)
    report = json.loads((out / "detention_pilot_quality_report.json").read_text(encoding="utf-8"))
    assert "selected_pilot_rows" in report
    assert "limitations" in report
    assert any("counterfactual" in lim.lower() for lim in report["limitations"])


def test_huggingface_graceful_failure(tmp_path: Path) -> None:
    from benchassist.detention_source_ingest import run_ingestion

    out = tmp_path / "candidates_hf.jsonl"
    result = run_ingestion(
        source="huggingface",
        output=out,
        dataset="BrainboxAI/legal-training-il",
        max_examples=5,
    )
    # Either succeeds with rows or fails gracefully
    assert result["status"] in {"success", "failed"}
    if result["status"] == "failed":
        assert result.get("failure_manifest") is not None


def test_vercel_pilot_export(tmp_path: Path, monkeypatch) -> None:
    from benchassist.vercel_export import _load_detention_pilot_exports

    pilot_dir = ROOT / "data" / "real_cases" / "detention" / "pilot_corpus"
    if not pilot_dir.exists():
        return  # skip if pilot not built yet
    exports = _load_detention_pilot_exports(ROOT)
    assert "detention_pilot_quality_report.json" in exports
