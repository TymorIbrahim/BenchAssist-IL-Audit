"""Tests for real Israeli case-inspired multi-domain audit layer."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "legal_training_sample.jsonl"


def test_domain_taxonomy_mapping() -> None:
    from benchassist.domain_taxonomy import infer_domain_from_text, normalize_domain_label, resolve_domain

    assert normalize_domain_label("housing") == "housing"
    assert normalize_domain_label("labor") == "labor_employment"
    assert infer_domain_from_text("דייר מדווח על פינוי") == "housing"
    assert resolve_domain("welfare", "קצבת נכות") == "social_benefits_welfare"


def test_redaction_emails_phones_ids() -> None:
    from benchassist.redaction import detect_possible_pii, redact_text

    text = "Contact test@example.com or 050-1234567 id 123456789"
    detected = detect_possible_pii(text)
    assert "email" in detected
    assert "phone" in detected
    result = redact_text(text)
    assert "test@example.com" not in result.text
    assert "050-1234567" not in result.text
    assert result.redacted
    assert result.notes


def test_redaction_preserves_hebrew() -> None:
    from benchassist.redaction import redact_text

    he = "דייר מדווח על עובש בדירה"
    result = redact_text(he, redact_names=False)
    assert "עובש" in result.text


def test_local_jsonl_ingestion(tmp_path: Path) -> None:
    from benchassist.real_case_ingestion import run_ingestion

    out = tmp_path / "real_cases"
    result = run_ingestion(
        source="local_jsonl",
        input_path=FIXTURE,
        output_dir=out,
        max_per_domain=5,
    )
    assert result["n_ingested"] >= 5
    assert (out / "real_case_summaries.csv").exists()
    df = pd.read_csv(out / "real_case_summaries.csv")
    assert "real_case_id" in df.columns
    assert "normalized_domain" in df.columns


def test_huggingface_ingestion_graceful_skip() -> None:
    from benchassist.real_case_ingestion import load_huggingface_dataset

    # Should not raise even without network/datasets
    rows = load_huggingface_dataset("BrainboxAI/legal-training-il")
    assert isinstance(rows, list)


def test_real_case_transform_run_batch_compatible(tmp_path: Path) -> None:
    from benchassist.real_case_ingestion import run_ingestion
    from benchassist.real_case_transform import transform_summaries

    out = tmp_path / "real_cases"
    run_ingestion(source="local_jsonl", input_path=FIXTURE, output_dir=out, max_per_domain=3)
    df = pd.read_csv(out / "real_case_summaries.csv")
    bench = transform_summaries(df, max_per_domain=3)
    assert len(bench) >= 3
    assert all(bench["dataset_mode"] == "real_case_inspired")
    assert all(bench["use_for_strict_bias_rates"] == False)  # noqa: E712
    assert all(bench["counterfactual_strength"] == "not_counterfactual")


def test_real_case_original_not_strict_counterfactual() -> None:
    from benchassist.dataset_modes import exclude_from_strict_bias

    row = {
        "dataset_mode": "real_case_inspired",
        "variant_type": "real_case_original",
        "use_for_strict_bias_rates": False,
    }
    assert exclude_from_strict_bias(row)


def test_audit_metrics_strict_excludes_real_cases() -> None:
    from benchassist.audit_metrics_v2 import filter_synthetic_strict_eligible

    df = pd.DataFrame([
        {"case_id": "H1", "variant_type": "neutral_he", "dataset_mode": "synthetic_controlled", "use_for_strict_bias_rates": True},
        {"case_id": "RC1", "variant_type": "real_case_original", "dataset_mode": "real_case_inspired", "use_for_strict_bias_rates": False},
    ])
    filtered = filter_synthetic_strict_eligible(df)
    assert len(filtered) == 1
    assert filtered.iloc[0]["case_id"] == "H1"


def test_counterfactual_validity_real_case_categories() -> None:
    from benchassist.counterfactual_validity import audit_counterfactual_row

    row = pd.Series({
        "case_id": "RC0001",
        "variant_id": "RC0001_original",
        "variant_type": "real_case_original",
        "dataset_mode": "real_case_inspired",
        "is_real_case_inspired": True,
        "demographic_cue": "none",
        "language": "he",
        "transformation_style": "real_case_original",
        "input_text": "sample",
    })
    out = audit_counterfactual_row(row, "base")
    assert out["validity_category"] == "real_case_original_not_counterfactual"
    assert out["exclude_from_strict_bias_rates"] is True


def test_real_case_variants_approximate(tmp_path: Path) -> None:
    from benchassist.real_case_transform import transform_summaries
    from benchassist.real_case_variants import generate_variants
    from benchassist.real_case_ingestion import run_ingestion

    out = tmp_path / "real_cases"
    run_ingestion(source="local_jsonl", input_path=FIXTURE, output_dir=out, max_per_domain=1)
    summaries = pd.read_csv(out / "real_case_summaries.csv")
    bench = transform_summaries(summaries, max_per_domain=1)
    variants = generate_variants(bench)
    assert len(variants) > len(bench)
    approx = variants[variants["variant_type"] != "real_case_original"]
    assert (approx["counterfactual_strength"] == "approximate").all()


def test_real_case_audit_group_summary(tmp_path: Path) -> None:
    from benchassist.real_case_audit import run_real_case_audit

    outputs = tmp_path / "outputs.csv"
    pd.DataFrame([
        {
            "case_id": "RC0001",
            "variant_id": "RC0001_original",
            "normalized_domain": "housing",
            "language": "he",
            "recommended_action_type": "regular_hearing",
            "urgency": "medium",
            "confidence": "medium",
            "dataset_mode": "real_case_inspired",
        }
    ]).to_csv(outputs, index=False)

    paths = run_real_case_audit(
        outputs,
        output_suffix="test",
        tables_dir=tmp_path / "tables",
        report_dir=tmp_path / "report",
    )
    assert paths["group_summary"].exists()
    group = pd.read_csv(paths["group_summary"])
    assert group.iloc[0]["n_outputs"] == 1


def test_multidomain_knowledge_loads() -> None:
    from benchassist.legal_sources import load_legal_sources

    path = ROOT / "data" / "knowledge" / "israeli_multidomain_knowledge.jsonl"
    assert path.exists()
    sources = load_legal_sources(path)
    domains = {s.legal_area for s in sources}
    assert "housing" in domains
    assert "labor_employment" in domains


def test_vercel_export_includes_real_case_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from benchassist.vercel_export import _load_real_case_layer_exports, export_csv

    data_dir = tmp_path / "data" / "real_cases"
    data_dir.mkdir(parents=True)
    pd.DataFrame([{"normalized_domain": "housing", "n_examples": 2}]).to_csv(
        data_dir / "real_case_domain_summary.csv", index=False
    )
    pd.DataFrame([{"real_case_id": "RC0001", "normalized_domain": "housing"}]).to_csv(
        data_dir / "real_case_summaries.csv", index=False
    )
    tables = tmp_path / "results" / "tables"
    tables.mkdir(parents=True)
    pd.DataFrame([{"normalized_domain": "housing", "n_outputs": 2}]).to_csv(
        tables / "real_case_audit_group_summary_qa.csv", index=False
    )

    exports = _load_real_case_layer_exports(tmp_path / "results", tmp_path)
    assert len(export_csv(exports["real_case_examples.json"][0])) >= 1


def test_dashboard_real_case_section_exists() -> None:
    assert (ROOT / "web_dashboard" / "components" / "RealCaseAuditSection.tsx").exists()
    text = (ROOT / "web_dashboard" / "components" / "Dashboard.tsx").read_text(encoding="utf-8")
    assert "real-case-audit" in text
    assert "RealCaseAuditSection" in text


def test_final_report_mentions_hybrid_methodology() -> None:
    text = (ROOT / "src" / "benchassist" / "final_report.py").read_text(encoding="utf-8")
    assert "_section_hybrid_methodology" in text
    assert "real-case-inspired" in text.lower() or "real_case" in text


def test_real_case_data_card_exists() -> None:
    assert (ROOT / "REAL_CASE_DATA_CARD.md").exists()
    text = (ROOT / "REAL_CASE_DATA_CARD.md").read_text(encoding="utf-8")
    assert "strict demographic counterfactual" in text.lower() or "strict" in text.lower()


def test_run_batch_input_cases(tmp_path: Path) -> None:
    from benchassist.run_batch import run_model_batch
    from benchassist.real_case_ingestion import run_ingestion
    from benchassist.real_case_transform import transform_summaries

    data_dir = tmp_path / "data" / "real_cases"
    run_ingestion(source="local_jsonl", input_path=FIXTURE, output_dir=data_dir, max_per_domain=2)
    summaries = pd.read_csv(data_dir / "real_case_summaries.csv")
    bench = transform_summaries(summaries, max_per_domain=2)
    inputs = data_dir / "bench.csv"
    bench.to_csv(inputs, index=False)

    out_dir = tmp_path / "outputs"
    records = run_model_batch(
        provider="mock",
        schema_version="v2",
        prompt_mode="baseline",
        input_cases=inputs,
        output_dir=out_dir,
        output_prefix="qa_real_test",
        limit=3,
    )
    assert len(records) == 3
    assert records[0].get("dataset_mode") == "real_case_inspired"
