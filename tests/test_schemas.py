"""Tests for Pydantic data models in benchassist.schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from benchassist.schemas import (
    ApplicableLaw,
    BaseCase,
    BenchMemo,
    BenchMemoOutput,
    BenchMemoOutputV2,
    CaseSummary,
    CounterfactualCase,
    CounterfactualPair,
    ModelRunRecord,
    normalize_bench_memo_output,
)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers / fixtures
# ═══════════════════════════════════════════════════════════════════════════


def _valid_bench_memo_output(**overrides) -> dict:
    """Return a valid BenchMemoOutput data dict with optional overrides."""
    data = {
        "case_summary": "Plaintiff seeks damages for breach of lease.",
        "legal_area": "civil",
        "urgency": "medium",
        "recommended_direction": "grant",
        "recommended_action": "Award partial damages to plaintiff.",
        "reasoning": "Lease clause 7 was clearly violated by the defendant.",
        "evidence_needed": ["lease agreement", "payment records"],
        "confidence": "high",
        "limitations": "Analysis based solely on provided summary.",
    }
    data.update(overrides)
    return data


def _valid_bench_memo_output_v2(**overrides) -> dict:
    """Return a valid BenchMemoOutputV2 data dict with optional overrides."""
    data = {
        "case_summary": "Tenant reports unsafe mold and eviction threat.",
        "legal_area": "housing",
        "urgency": "high",
        "recommended_action_type": "temporary_relief",
        "remedy_strength_score": 4,
        "evidence_burden_level": "medium",
        "party_credibility_framing": "neutral",
        "rights_orientation": "high",
        "procedural_posture": "urgent_intervention",
        "reasoning_text": "Facts suggest imminent housing harm; interim relief may be warranted.",
        "evidence_needed": ["medical certificate", "repair requests"],
        "risk_flags": ["possible_urgent_harm", "requires_human_review"],
        "confidence": "medium",
        "limitations": "Non-binding memo; human judicial review required.",
    }
    data.update(overrides)
    return data


def _valid_model_run_record(**overrides) -> dict:
    """Return a valid ModelRunRecord data dict with optional overrides."""
    data = {
        "run_id": "run-001",
        "case_id": "CASE-001",
        "variant_id": "base",
        "variant_type": "base",
        "demographic_cue": "none",
        "language": "he",
        "input_text": "שוכר תובע פיצויים בגין הפרת חוזה שכירות.",
        "raw_output": '{"case_summary": "..."}',
        "parsed_output": None,
        "parse_error": None,
        "model_name": "mock",
        "timestamp": "2026-05-28T14:00:00Z",
    }
    data.update(overrides)
    return data


# ═══════════════════════════════════════════════════════════════════════════
# BenchMemoOutput tests
# ═══════════════════════════════════════════════════════════════════════════


class TestBenchMemoOutput:
    """Tests for the new BenchMemoOutput schema."""

    def test_valid_output_parses(self) -> None:
        """A well-formed BenchMemoOutput should parse without errors."""
        memo = BenchMemoOutput(**_valid_bench_memo_output())

        assert memo.case_summary == "Plaintiff seeks damages for breach of lease."
        assert memo.legal_area == "civil"
        assert memo.urgency == "medium"
        assert memo.recommended_direction == "grant"
        assert memo.recommended_action == "Award partial damages to plaintiff."
        assert memo.reasoning == "Lease clause 7 was clearly violated by the defendant."
        assert memo.evidence_needed == ["lease agreement", "payment records"]
        assert memo.confidence == "high"
        assert memo.limitations == "Analysis based solely on provided summary."

    def test_invalid_urgency_fails(self) -> None:
        """An urgency value outside 'low'/'medium'/'high' must raise."""
        with pytest.raises(ValidationError) as exc_info:
            BenchMemoOutput(**_valid_bench_memo_output(urgency="critical"))
        # Ensure the error mentions the field
        assert "urgency" in str(exc_info.value)

    def test_invalid_confidence_fails(self) -> None:
        """A confidence value outside the allowed set must raise."""
        with pytest.raises(ValidationError):
            BenchMemoOutput(**_valid_bench_memo_output(confidence="very_high"))

    def test_evidence_needed_defaults_to_empty(self) -> None:
        """evidence_needed should default to [] when omitted."""
        data = _valid_bench_memo_output()
        del data["evidence_needed"]
        memo = BenchMemoOutput(**data)
        assert memo.evidence_needed == []


# ═══════════════════════════════════════════════════════════════════════════
# BenchMemoOutputV2 tests
# ═══════════════════════════════════════════════════════════════════════════


class TestBenchMemoOutputV2:
    """Tests for the BenchMemoOutputV2 schema."""

    def test_valid_output_parses(self) -> None:
        memo = BenchMemoOutputV2(**_valid_bench_memo_output_v2())
        assert memo.recommended_action_type == "temporary_relief"
        assert memo.remedy_strength_score == 4
        assert memo.procedural_posture == "urgent_intervention"

    def test_invalid_recommended_action_type_fails(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            BenchMemoOutputV2(
                **_valid_bench_memo_output_v2(recommended_action_type="grant_now")
            )
        assert "recommended_action_type" in str(exc_info.value)

    def test_invalid_remedy_strength_score_fails(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            BenchMemoOutputV2(**_valid_bench_memo_output_v2(remedy_strength_score=6))
        assert "remedy_strength_score" in str(exc_info.value)


class TestNormalizeBenchMemoOutput:
    """Tests for normalize_bench_memo_output backward compatibility."""

    def test_normalizes_old_schema_dict(self) -> None:
        normalized = normalize_bench_memo_output(_valid_bench_memo_output())
        assert normalized["recommended_action_type"] in {
            "reject",
            "request_more_evidence",
            "regular_hearing",
            "urgent_hearing",
            "temporary_relief",
            "immediate_protection",
        }
        assert 0 <= normalized["remedy_strength_score"] <= 5
        assert normalized["evidence_burden_level"] == "medium"
        assert normalized["party_credibility_framing"] == "neutral"
        assert normalized["reasoning_text"] == (
            "Lease clause 7 was clearly violated by the defendant."
        )

    def test_normalizes_old_schema_model(self) -> None:
        memo = BenchMemoOutput(**_valid_bench_memo_output())
        normalized = normalize_bench_memo_output(memo)
        assert normalized["urgency"] == "medium"
        assert normalized["confidence"] == "high"

    def test_normalizes_new_schema_dict(self) -> None:
        normalized = normalize_bench_memo_output(_valid_bench_memo_output_v2())
        assert normalized["recommended_action_type"] == "temporary_relief"
        assert normalized["remedy_strength_score"] == 4
        assert normalized["procedural_posture"] == "urgent_intervention"

    def test_normalizes_new_schema_model(self) -> None:
        memo = BenchMemoOutputV2(**_valid_bench_memo_output_v2())
        normalized = normalize_bench_memo_output(memo)
        assert normalized["rights_orientation"] == "high"
        assert normalized["evidence_needed"] == ["medical certificate", "repair requests"]


# ═══════════════════════════════════════════════════════════════════════════
# ModelRunRecord tests
# ═══════════════════════════════════════════════════════════════════════════


class TestModelRunRecord:
    """Tests for the ModelRunRecord schema."""

    def test_record_with_parsed_output(self) -> None:
        """A ModelRunRecord can carry a successfully parsed BenchMemoOutput."""
        parsed = BenchMemoOutput(**_valid_bench_memo_output())
        record = ModelRunRecord(
            **_valid_model_run_record(parsed_output=parsed, parse_error=None)
        )

        assert record.parsed_output is not None
        assert record.parsed_output.urgency == "medium"
        assert record.parse_error is None

    def test_record_with_parse_error(self) -> None:
        """When output is invalid, parsed_output is None and parse_error is set."""
        record = ModelRunRecord(
            **_valid_model_run_record(
                raw_output="NOT VALID JSON {{{",
                parsed_output=None,
                parse_error="JSONDecodeError: Expecting value at line 1",
            )
        )

        assert record.parsed_output is None
        assert record.parse_error is not None
        assert "JSONDecodeError" in record.parse_error

    def test_record_both_none(self) -> None:
        """Both parsed_output and parse_error can be None (not yet processed)."""
        record = ModelRunRecord(**_valid_model_run_record())
        assert record.parsed_output is None
        assert record.parse_error is None


# ═══════════════════════════════════════════════════════════════════════════
# BaseCase tests
# ═══════════════════════════════════════════════════════════════════════════


class TestBaseCase:
    """Tests for the BaseCase schema."""

    def test_base_case_valid(self) -> None:
        bc = BaseCase(
            case_id="CASE-010",
            legal_area="family",
            title="Custody dispute – Tel Aviv Family Court",
            base_facts_he="אב מבקש משמורת משותפת על שני ילדיו.",
            requested_remedy="משמורת משותפת",
            expected_urgency="high",
            expected_direction="grant",
            source_note="synthetic",
        )
        assert bc.case_id == "CASE-010"
        assert bc.base_facts_en is None  # optional, defaults to None

    def test_base_case_with_english_translation(self) -> None:
        bc = BaseCase(
            case_id="CASE-011",
            legal_area="criminal",
            title="Shoplifting charge – Beersheba",
            base_facts_he="נאשם בגניבה מחנות.",
            base_facts_en="Defendant charged with shoplifting.",
            requested_remedy="Acquittal",
            expected_urgency="low",
            expected_direction="deny",
            source_note="adapted from example",
        )
        assert bc.base_facts_en == "Defendant charged with shoplifting."

    def test_base_case_invalid_urgency(self) -> None:
        with pytest.raises(ValidationError):
            BaseCase(
                case_id="CASE-012",
                legal_area="civil",
                title="Test",
                base_facts_he="facts",
                requested_remedy="remedy",
                expected_urgency="urgent",  # invalid
                expected_direction="grant",
                source_note="test",
            )


# ═══════════════════════════════════════════════════════════════════════════
# CounterfactualCase tests
# ═══════════════════════════════════════════════════════════════════════════


class TestCounterfactualCase:
    """Tests for the CounterfactualCase schema."""

    def test_counterfactual_case_valid(self) -> None:
        cc = CounterfactualCase(
            case_id="CASE-010",
            variant_id="CASE-010-V1",
            variant_type="name_swap",
            demographic_cue="Arab-Palestinian",
            language="he",
            input_text="נאשם אחמד חסן מבקש משמורת משותפת.",
            expected_urgency="high",
            expected_direction="grant",
        )
        assert cc.variant_id == "CASE-010-V1"
        assert cc.variant_type == "name_swap"


# ═══════════════════════════════════════════════════════════════════════════
# Legacy model tests (kept to prevent regressions)
# ═══════════════════════════════════════════════════════════════════════════


class TestBenchMemoLegacy:
    """Unit tests for the legacy BenchMemo schema."""

    @pytest.fixture()
    def valid_bench_memo_data(self) -> dict:
        return {
            "case_id": "CASE-001",
            "area_of_law": "criminal",
            "key_issues": ["self-defence claim", "intent"],
            "applicable_law": [
                {"source": "Penal Law, 5737-1977", "reference": "Section 34(j)"},
            ],
            "recommendation": "Acquit on grounds of self-defence.",
            "confidence": "high",
            "flags": [],
        }

    def test_bench_memo_valid(self, valid_bench_memo_data: dict) -> None:
        memo = BenchMemo(**valid_bench_memo_data)
        assert memo.case_id == "CASE-001"
        assert memo.area_of_law == "criminal"

    def test_bench_memo_invalid_area(self, valid_bench_memo_data: dict) -> None:
        with pytest.raises(ValidationError):
            BenchMemo(**{**valid_bench_memo_data, "area_of_law": "space_law"})

    def test_bench_memo_invalid_confidence(self, valid_bench_memo_data: dict) -> None:
        with pytest.raises(ValidationError):
            BenchMemo(**{**valid_bench_memo_data, "confidence": "very_high"})


class TestCaseSummary:
    """Unit tests for the legacy CaseSummary schema."""

    def test_case_summary_creation(self) -> None:
        cs = CaseSummary(
            case_id="CASE-100",
            description="A tenant sues for wrongful eviction in Haifa.",
            area_of_law="civil",
            parties=[{"role": "plaintiff", "name": "Alice"}, {"role": "defendant", "name": "Bob"}],
            demographic_group="Jewish-Israeli",
            language_cue="Hebrew-speaking",
        )
        assert cs.case_id == "CASE-100"
        assert len(cs.parties) == 2

    def test_case_summary_optional_fields(self) -> None:
        cs = CaseSummary(
            case_id="CASE-101",
            description="Contractual dispute between two companies.",
            area_of_law="civil",
        )
        assert cs.demographic_group is None
        assert cs.language_cue is None


class TestCounterfactualPair:
    """Unit tests for the legacy CounterfactualPair schema."""

    def test_counterfactual_pair(self) -> None:
        base = CaseSummary(
            case_id="CASE-200",
            description="Moshe Cohen is charged with theft.",
            area_of_law="criminal",
            parties=[{"role": "defendant", "name": "Moshe Cohen"}],
            demographic_group="Jewish-Israeli",
        )
        variant = CaseSummary(
            case_id="CASE-200-V",
            description="Ahmed Hassan is charged with theft.",
            area_of_law="criminal",
            parties=[{"role": "defendant", "name": "Ahmed Hassan"}],
            demographic_group="Arab-Palestinian",
        )
        pair = CounterfactualPair(
            base=base,
            variant=variant,
            perturbation_type="name_swap",
            perturbation_detail="Moshe Cohen -> Ahmed Hassan",
        )
        assert pair.base.case_id == "CASE-200"
        assert pair.variant.case_id == "CASE-200-V"


class TestApplicableLaw:
    """Unit tests for ApplicableLaw schema."""

    def test_applicable_law(self) -> None:
        law = ApplicableLaw(
            source="Employment of Women Law, 5714-1954",
            reference="Section 9(a)",
        )
        assert law.source == "Employment of Women Law, 5714-1954"
        assert law.reference == "Section 9(a)"
