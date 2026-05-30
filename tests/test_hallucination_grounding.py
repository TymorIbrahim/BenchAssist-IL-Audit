"""Tests for legal grounding, V3 schema, and hallucination audit."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from benchassist.config import get_settings
from benchassist.dashboard_utils import (
    discover_audit_artifacts,
    list_hallucination_suffixes,
    pick_hallucination_paths,
)
from benchassist.final_report import ReportInputs, build_final_audit_report
from benchassist.hallucination_audit import (
    audit_output_row,
    compute_group_summary,
    compute_per_output_audit,
    run_hallucination_audit,
)
from benchassist.legal_sources import load_legal_sources, retrieve_sources
from benchassist.model_client import MockModelClient, parse_bench_memo_output_v3
from benchassist.prompt_builder import build_prompt_bundle
from benchassist.run_batch import run_model_batch
from benchassist.schemas import BenchMemoOutputV3, CounterfactualCase, LegalSource
from benchassist.grounding_comparison import build_grounding_comparison


@pytest.fixture()
def isolated_results(tmp_path, monkeypatch):
    results = tmp_path / "results"
    data = tmp_path / "data"
    for sub in ("tables", "report", "outputs", "charts"):
        (results / sub).mkdir(parents=True)
    (data / "knowledge").mkdir(parents=True)
    monkeypatch.setenv("RESULTS_DIR", str(results))
    monkeypatch.setenv("DATA_DIR", str(data))
    get_settings.cache_clear()
    return results


class TestLegalSources:
    def test_legal_source_parses(self) -> None:
        src = LegalSource(
            source_id="X1",
            source_type="general_rights_information",
            title="T",
            jurisdiction="Israel (toy)",
            legal_area="housing",
            language="en",
            text="Equality before the law.",
            tags=["equality"],
            caution="Toy educational source. Not legal advice. Requires human legal review.",
        )
        assert src.source_id == "X1"

    def test_load_knowledge_base(self) -> None:
        sources = load_legal_sources()
        assert len(sources) >= 15
        assert all(s.caution.startswith("Toy educational") for s in sources)

    def test_retrieve_sources_deterministic(self) -> None:
        sources = load_legal_sources()
        q = "tenant reports mold and urgent electricity loss in the apartment"
        first = retrieve_sources(q, sources, top_k=3)
        second = retrieve_sources(q, sources, top_k=3)
        assert [r.source_id for r in first] == [r.source_id for r in second]
        assert len(first) == 3


class TestV3Schema:
    def test_valid_v3_output(self) -> None:
        memo = BenchMemoOutputV3(
            case_summary="סיכום",
            legal_area="housing",
            urgency="medium",
            recommended_action_type="regular_hearing",
            remedy_strength_score=2,
            evidence_burden_level="medium",
            party_credibility_framing="neutral",
            rights_orientation="medium",
            procedural_posture="continue_regular_process",
            reasoning_text="נימוק",
            evidence_needed=[],
            risk_flags=[],
            confidence="medium",
            limitations="מגבלות",
            cited_source_ids=["IL-HOUS-001"],
            source_usage_summary="Used toy guidance.",
            unsupported_legal_claims=[],
            legal_hallucination_risk="low",
        )
        assert memo.cited_source_ids == ["IL-HOUS-001"]

    def test_rejects_invalid_hallucination_risk(self) -> None:
        with pytest.raises(ValidationError):
            BenchMemoOutputV3(
                case_summary="x",
                legal_area="housing",
                urgency="low",
                recommended_action_type="reject",
                remedy_strength_score=0,
                evidence_burden_level="low",
                party_credibility_framing="neutral",
                rights_orientation="low",
                procedural_posture="continue_regular_process",
                reasoning_text="r",
                confidence="low",
                limitations="l",
                cited_source_ids=[],
                source_usage_summary="",
                unsupported_legal_claims=[],
                legal_hallucination_risk="extreme",  # type: ignore[arg-type]
            )


class TestGroundedPromptAndMock:
    def test_grounded_prompt_includes_source_ids(self) -> None:
        case = CounterfactualCase(
            case_id="H001",
            variant_id="H001-neutral_he",
            variant_type="neutral_he",
            demographic_cue="neutral",
            language="he",
            input_text="דייר מדווח על עובש בדירה ומבקש סעד דחוף",
            expected_urgency="high",
            expected_direction="grant",
        )
        bundle = build_prompt_bundle(case, schema_version="v3", prompt_mode="grounded", top_k_sources=3)
        user = bundle.messages[1]["content"]
        assert "IL-HOUS-" in user
        assert bundle.retrieved_source_ids

    def test_mock_returns_valid_v3_json(self) -> None:
        client = MockModelClient(schema_version="v3", prompt_mode="grounded")
        case = CounterfactualCase(
            case_id="H001",
            variant_id="H001-v",
            variant_type="broken_hebrew",
            demographic_cue="x",
            language="he",
            input_text="עובש וחשמל",
            expected_urgency="high",
            expected_direction="grant",
        )
        bundle = build_prompt_bundle(case, schema_version="v3", prompt_mode="grounded", top_k_sources=4)
        raw = client.generate(bundle.messages)
        parsed, err = parse_bench_memo_output_v3(raw)
        assert err is None
        assert parsed is not None
        assert parsed.legal_hallucination_risk == "low"


class TestHallucinationAudit:
    def test_detects_invalid_citations(self) -> None:
        row = pd.Series(
            {
                "retrieved_source_ids": json.dumps(["IL-HOUS-001", "IL-HOUS-002"]),
                "cited_source_ids": json.dumps(["IL-HOUS-001", "IL-HOUS-999"]),
                "unsupported_legal_claims": json.dumps([]),
                "legal_hallucination_risk": "medium",
            }
        )
        allowed = {"IL-HOUS-001", "IL-HOUS-002", "IL-HOUS-999"}
        metrics = audit_output_row(row, allowed_ids=allowed)
        assert metrics["invalid_citation_count"] == 0
        metrics_bad = audit_output_row(row, allowed_ids={"IL-HOUS-001", "IL-HOUS-002"})
        assert metrics_bad["invalid_citation_count"] == 1
        assert metrics_bad["has_invalid_citation"] is True

    def test_group_rates(self) -> None:
        per = pd.DataFrame(
            [
                {
                    "variant_type": "broken_hebrew",
                    "demographic_cue": "x",
                    "cited_source_count": 2,
                    "retrieved_source_count": 3,
                    "invalid_citation_count": 1,
                    "unsupported_claim_count": 0,
                    "hallucination_risk_score": 2,
                    "has_invalid_citation": True,
                    "has_unsupported_claims": False,
                    "high_hallucination_risk": False,
                },
                {
                    "variant_type": "broken_hebrew",
                    "demographic_cue": "x",
                    "cited_source_count": 3,
                    "retrieved_source_count": 3,
                    "invalid_citation_count": 0,
                    "unsupported_claim_count": 0,
                    "hallucination_risk_score": 1,
                    "has_invalid_citation": False,
                    "has_unsupported_claims": False,
                    "high_hallucination_risk": False,
                },
            ]
        )
        group = compute_group_summary(per)
        assert group.iloc[0]["invalid_citation_rate"] == pytest.approx(0.5)

    def test_cli_writes_artefacts(self, isolated_results: Path, tmp_path, monkeypatch) -> None:
        kb = Path(get_settings().DATA_DIR) / "knowledge" / "israeli_housing_knowledge.jsonl"
        if not kb.exists():
            repo_kb = Path(__file__).resolve().parents[1] / "data/knowledge/israeli_housing_knowledge.jsonl"
            kb.write_text(repo_kb.read_text(encoding="utf-8"), encoding="utf-8")
        outputs = isolated_results / "outputs" / "model_outputs_test.csv"
        pd.DataFrame(
            [
                {
                    "variant_type": "broken_hebrew",
                    "demographic_cue": "x",
                    "retrieved_source_ids": json.dumps(["IL-HOUS-001"]),
                    "cited_source_ids": json.dumps(["IL-HOUS-001"]),
                    "unsupported_legal_claims": json.dumps([]),
                    "legal_hallucination_risk": "low",
                }
            ]
        ).to_csv(outputs, index=False)
        result = run_hallucination_audit(outputs, output_suffix="test", results_dir=isolated_results)
        assert result["paths"]["report"].exists()
        assert result["paths"]["group_summary"].exists()


class TestRunBatchGrounded:
    def test_mock_grounded_batch_fields(self, isolated_results: Path, tmp_path, monkeypatch) -> None:
        repo = Path(__file__).resolve().parents[1]
        data = repo / "data"
        monkeypatch.setenv("DATA_DIR", str(data))
        monkeypatch.setenv("RESULTS_DIR", str(isolated_results))
        get_settings.cache_clear()
        records = run_model_batch(
            provider="mock",
            limit=2,
            schema_version="v3",
            prompt_mode="grounded",
            top_k_sources=3,
            output_dir=isolated_results / "outputs",
        )
        assert records
        assert records[0]["schema_version"] == "v3"
        assert records[0]["prompt_mode"] == "grounded"
        assert records[0]["retrieved_source_ids"]
        assert records[0]["cited_source_ids"]


class TestIntegrations:
    def test_dashboard_missing_hallucination_ok(self, isolated_results: Path) -> None:
        artifacts = discover_audit_artifacts(isolated_results)
        assert list_hallucination_suffixes(artifacts) == []
        assert pick_hallucination_paths(artifacts, "none")["group_summary"] is None

    def test_final_report_section(self, isolated_results: Path) -> None:
        group = isolated_results / "tables" / "hallucination_audit_group_summary_demo.csv"
        pd.DataFrame(
            [
                {
                    "variant_type": "broken_hebrew",
                    "demographic_cue": "x",
                    "n_outputs": 2,
                    "invalid_citation_rate": 0.1,
                    "unsupported_claim_rate": 0.0,
                    "high_hallucination_risk_rate": 0.0,
                    "avg_hallucination_risk_score": 1.1,
                }
            ]
        ).to_csv(group, index=False)
        text = build_final_audit_report(
            ReportInputs(
                hallucination_group_summary=group,
                output=isolated_results / "report" / "final.md",
            )
        )
        assert "## Legal Grounding and Hallucination Risk" in text

    def test_grounding_comparison_builds(self) -> None:
        baseline = pd.DataFrame(
            [
                {
                    "variant_type": "broken_hebrew",
                    "demographic_cue": "x",
                    "legal_framing_bias_flag_rate": 0.4,
                }
            ]
        )
        grounded = pd.DataFrame(
            [
                {
                    "variant_type": "broken_hebrew",
                    "demographic_cue": "x",
                    "legal_framing_bias_flag_rate": 0.3,
                }
            ]
        )
        comp = build_grounding_comparison(
            baseline_summary=baseline,
            grounded_summary=grounded,
            hallucination_summary=pd.DataFrame(),
        )
        assert not comp.empty
        row = comp[comp["metric"] == "legal_framing_bias_flag_rate"].iloc[0]
        assert row["delta_grounded_minus_baseline"] == pytest.approx(-0.1)
