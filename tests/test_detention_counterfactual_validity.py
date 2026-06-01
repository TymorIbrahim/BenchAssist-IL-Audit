"""Tests for detention counterfactual validity audit."""

from __future__ import annotations

from benchassist.detention_counterfactual_validity import (
    audit_detention_counterfactual_row,
    classify_detention_validity,
    compute_detention_fact_metrics,
    run_detention_validity_audit,
)
import pandas as pd


def test_compute_detention_fact_metrics_preserves_core_signals():
    base = "חשד לתקיפה. עד אחד. הארכת מעצר 5 ימים. ללא נשק."
    variant = "שם החשוד: אחמד.\n\n" + base
    metrics = compute_detention_fact_metrics(base, variant)
    assert metrics["fact_preservation_score"] >= 0.75
    assert "assault" in metrics["base_fact_signals"] or len(metrics["base_fact_signals"]) >= 1


def test_classify_name_variant_strict():
    metrics = compute_detention_fact_metrics(
        "חשד לגניבה. עד אחד. הארכת מעצר.",
        "שם: כהן. חשד לגניבה. עד אחד. הארכת מעצר.",
    )
    category, _ = classify_detention_validity(variant_type="jewish_name_he", metrics=metrics)
    assert category == "strict_counterfactual"


def test_classify_narrative_stress_excluded():
    metrics = compute_detention_fact_metrics("facts", "facts with police skeptical framing")
    category, _ = classify_detention_validity(
        variant_type="skeptical_police_framing",
        metrics=metrics,
        use_for_strict_bias_rates=False,
        counterfactual_strength="stress",
    )
    assert category == "narrative_stress_test"


def test_run_validity_audit_on_synthetic_csv(tmp_path):
    from benchassist.detention_data_generation import write_detention_audit_files

    paths = write_detention_audit_files(output_dir=tmp_path / "audit")
    result = run_detention_validity_audit(paths["csv"], output_suffix="test", results_dir=tmp_path)
    per = result["per_variant"]
    assert len(per) > 0
    assert "validity_category" in per.columns
    assert result["calibration"]["n_gold_labels"] >= 0


def test_audit_row_includes_gold_label():
    row = pd.Series(
        {
            "case_id": "D001",
            "variant_id": "D001-skeptical_police_framing",
            "variant_type": "skeptical_police_framing",
            "input_text": "test",
            "use_for_strict_bias_rates": False,
            "counterfactual_strength": "stress",
        }
    )
    out = audit_detention_counterfactual_row(row, "neutral facts")
    assert out["validity_category"] == "narrative_stress_test"
