"""Tests for detention / remand full-text data preparation layer."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "detention_public_sample.jsonl"
REGISTRY = ROOT / "data" / "legal_sources" / "detention_sources.json"


def test_source_registry_loading() -> None:
    from benchassist.detention_sources import (
        get_source_by_id,
        iter_sources_by_type,
        load_detention_sources,
        sources_manifest,
    )

    sources = load_detention_sources(REGISTRY)
    assert len(sources) >= 8
    assert all(s.jurisdiction == "Israel" for s in sources)
    arrest = get_source_by_id("arrest_law_1996", path=REGISTRY)
    assert arrest is not None
    assert arrest.full_text_allowed_internal is True
    assert arrest.requires_manual_review_before_dashboard is True
    grounding = list(iter_sources_by_type("legal_grounding", path=REGISTRY))
    assert len(grounding) >= 3
    manifest = sources_manifest(path=REGISTRY)
    assert manifest["n_sources"] == len(sources)


def test_keyword_inclusion_filter() -> None:
    from benchassist.detention_source_filters import apply_detention_filters

    text = "התובע מבקש הארכת מעצר ימים. קיים חשד סביר וראיות לכאורה."
    result = apply_detention_filters(text)
    assert result.is_detention_related
    assert not result.sensitive_content_flag
    assert result.include_in_model_inputs


def test_sensitive_content_flagging() -> None:
    from benchassist.detention_source_filters import apply_detention_filters

    text = "בקשה להארכת מעצר ימים של קטין החשוד בעבירה."
    result = apply_detention_filters(text)
    assert result.is_detention_related
    assert result.sensitive_content_flag
    assert result.include_in_model_inputs is False
    assert result.requires_manual_legal_review
    assert "קטין" in result.sensitivity_reason


def test_full_text_preserved_full_internal(tmp_path: Path) -> None:
    from benchassist.detention_fulltext_prepare import run_preparation

    fixture_text = FIXTURE.read_text(encoding="utf-8")
    assert "יוסי כהן" in fixture_text
    assert "1234/24" in fixture_text

    out = tmp_path / "detention"
    run_preparation(
        source="local_jsonl",
        data_mode="full_internal",
        input_path=FIXTURE,
        output_dir=out,
        max_examples=50,
    )
    df = pd.read_csv(out / "detention_case_summaries_fulltext.csv")
    row = df[df["source_id"] == "sample_001"].iloc[0]
    assert "יוסי כהן" in str(row["full_text"])
    assert "1234/24" in str(row["full_text"])
    assert row["no_redaction_applied"] is True or str(row["no_redaction_applied"]).lower() == "true"
    assert row["redaction_policy"] == "no_redaction_internal_expert_review"
    assert row["data_visibility"] == "internal_full_text"


def test_fulltext_preparation_creates_all_files(tmp_path: Path) -> None:
    from benchassist.detention_fulltext_prepare import run_preparation

    out = tmp_path / "detention"
    result = run_preparation(
        source="local_jsonl",
        data_mode="full_internal",
        input_path=FIXTURE,
        output_dir=out,
        max_examples=50,
    )
    assert result["n_bench_inputs"] == 5
    assert result["n_sensitive_flagged"] == 3
    expected = [
        "raw_real_detention_examples_fulltext.jsonl",
        "detention_case_summaries_fulltext.csv",
        "detention_case_summaries_fulltext.jsonl",
        "detention_bench_inputs_fulltext.csv",
        "detention_domain_summary.csv",
        "detention_sensitive_flagged_for_review.csv",
        "detention_source_manifest.json",
        "detention_data_handling_manifest.json",
    ]
    for name in expected:
        assert (out / name).exists(), name


def test_prepared_rows_exclude_strict_bias(tmp_path: Path) -> None:
    from benchassist.detention_fulltext_prepare import run_preparation

    out = tmp_path / "detention"
    run_preparation(
        source="local_jsonl",
        data_mode="full_internal",
        input_path=FIXTURE,
        output_dir=out,
        max_examples=50,
    )
    bench = pd.read_csv(out / "detention_bench_inputs_fulltext.csv")
    assert len(bench) == 5
    assert all(bench["use_for_strict_bias_rates"] == False)  # noqa: E712
    assert all(bench["exclude_from_strict_bias_rates"] == True)  # noqa: E712
    assert all(bench["dataset_mode"] == "real_case_inspired")
    assert all(bench["counterfactual_strength"] == "not_counterfactual")
    assert all(bench["manual_review_required"] == True)  # noqa: E712
    assert all(bench["data_visibility"] == "internal_full_text")


def test_sensitive_rows_excluded_from_bench_inputs(tmp_path: Path) -> None:
    from benchassist.detention_fulltext_prepare import run_preparation

    out = tmp_path / "detention"
    run_preparation(
        source="local_jsonl",
        data_mode="full_internal",
        input_path=FIXTURE,
        output_dir=out,
        max_examples=50,
    )
    bench = pd.read_csv(out / "detention_bench_inputs_fulltext.csv")
    sensitive = pd.read_csv(out / "detention_sensitive_flagged_for_review.csv")
    assert len(sensitive) == 3
    bench_ids = set(bench["case_id"].astype(str))
    sensitive_ids = set(sensitive["detention_case_id"].astype(str))
    assert bench_ids.isdisjoint(sensitive_ids)


def test_source_attribution_preserved(tmp_path: Path) -> None:
    from benchassist.detention_fulltext_prepare import run_preparation

    out = tmp_path / "detention"
    run_preparation(
        source="local_jsonl",
        data_mode="full_internal",
        input_path=FIXTURE,
        output_dir=out,
        max_examples=50,
    )
    bench = pd.read_csv(out / "detention_bench_inputs_fulltext.csv")
    assert bench["attribution_note"].notna().all()
    assert bench["source_dataset"].notna().all()
    assert bench["source_id"].notna().all()
    assert "source_url" in bench.columns


def test_public_summary_mode_excludes_full_text(tmp_path: Path) -> None:
    from benchassist.detention_fulltext_prepare import run_preparation

    internal = tmp_path / "detention"
    run_preparation(
        source="local_jsonl",
        data_mode="full_internal",
        input_path=FIXTURE,
        output_dir=internal,
        max_examples=50,
    )
    public_out = tmp_path / "detention_public_export"
    run_preparation(
        source="local_jsonl",
        data_mode="public_summary",
        input_path=internal / "raw_real_detention_examples_fulltext.jsonl",
        output_dir=public_out,
    )
    pub = pd.read_csv(public_out / "detention_public_summaries.csv")
    assert "full_text" not in pub.columns
    assert all(pub["full_text_included"] == False)  # noqa: E712
    internal_df = pd.read_csv(internal / "detention_case_summaries_fulltext.csv")
    full_row = internal_df[internal_df["source_id"] == "sample_001"].iloc[0]
    pub_row = pub[pub["source_id"] == "sample_001"].iloc[0]
    assert len(str(pub_row["short_excerpt"])) <= 253
    assert len(str(pub_row["short_excerpt"])) < len(str(full_row["full_text"]))
    handling = json.loads(
        (public_out / "detention_data_handling_manifest.json").read_text(encoding="utf-8")
    )
    assert handling["data_mode"] == "public_summary"


def test_data_handling_manifest_created(tmp_path: Path) -> None:
    from benchassist.detention_fulltext_prepare import run_preparation

    out = tmp_path / "detention"
    run_preparation(
        source="local_jsonl",
        data_mode="full_internal",
        input_path=FIXTURE,
        output_dir=out,
        max_examples=50,
    )
    handling = json.loads((out / "detention_data_handling_manifest.json").read_text(encoding="utf-8"))
    assert handling["policy"]["requires_access_control_for_full_text_dashboard"] is True
    assert handling["methodology"]["exclude_from_strict_bias_rates"] is True


def test_huggingface_graceful_skip() -> None:
    from benchassist.detention_fulltext_prepare import load_huggingface_dataset

    rows = load_huggingface_dataset("BrainboxAI/legal-training-il")
    assert isinstance(rows, list)


def test_legacy_redaction_module_still_available() -> None:
    """Legacy redaction module remains for other layers; fulltext path does not use it."""
    from benchassist.detention_redaction import redact_detention_text

    result = redact_detention_text("test@example.com")
    assert "test@example.com" not in result.redacted_text
