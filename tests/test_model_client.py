"""Tests for model client and bench-memo parsing."""

from __future__ import annotations

import json

import pytest

from benchassist.data_generation import create_base_cases, create_counterfactual_cases
from benchassist.model_client import (
    MockModelClient,
    parse_bench_memo_output,
    parse_bench_memo_output_v2,
)
from benchassist.prompt_builder import build_counterfactual_messages
from benchassist.schemas import BenchMemoOutput, BenchMemoOutputV2
from tests.test_schemas import _valid_bench_memo_output


class TestParseBenchMemoOutput:
    def test_parser_handles_clean_json(self) -> None:
        payload = _valid_bench_memo_output()
        raw = json.dumps(payload)
        parsed, error = parse_bench_memo_output(raw)
        assert error is None
        assert parsed is not None
        assert isinstance(parsed, BenchMemoOutput)
        assert parsed.legal_area == "civil"

    def test_parser_handles_json_inside_markdown_code_block(self) -> None:
        payload = _valid_bench_memo_output(legal_area="housing", urgency="high")
        raw = f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
        parsed, error = parse_bench_memo_output(raw)
        assert error is None
        assert parsed is not None
        assert parsed.legal_area == "housing"
        assert parsed.urgency == "high"

    def test_invalid_output_creates_parse_error(self) -> None:
        parsed, error = parse_bench_memo_output("this is not json at all")
        assert parsed is None
        assert error is not None
        assert "JSON decode error" in error

    def test_invalid_schema_creates_parse_error(self) -> None:
        raw = json.dumps({"case_summary": "only one field"})
        parsed, error = parse_bench_memo_output(raw)
        assert parsed is None
        assert error is not None
        assert "Schema validation error" in error


class TestMockModelClient:
    @pytest.fixture()
    def housing_messages(self):
        case = create_counterfactual_cases(create_base_cases())[0]
        return build_counterfactual_messages(case)

    def test_mock_returns_valid_parseable_bench_memo_output(
        self, housing_messages
    ) -> None:
        client = MockModelClient()
        raw = client.generate(housing_messages)
        parsed, error = parse_bench_memo_output(raw)
        assert error is None
        assert parsed is not None
        assert parsed.legal_area == "housing"
        assert parsed.confidence == "medium"
        assert parsed.limitations == (
            "Non-binding: judicial review required before any action."
        )

    def test_mock_urgency_high_for_mold_case(self, housing_messages) -> None:
        client = MockModelClient()
        raw = client.generate(housing_messages)
        parsed, _ = parse_bench_memo_output(raw)
        assert parsed is not None
        assert parsed.urgency == "high"

    def test_mock_is_deterministic(self, housing_messages) -> None:
        client = MockModelClient()
        first = client.generate(housing_messages)
        second = client.generate(housing_messages)
        assert first == second


class TestMockModelClientV2:
    @pytest.fixture()
    def housing_messages_v2(self):
        case = create_counterfactual_cases(create_base_cases())[0]
        return build_counterfactual_messages(case, schema_version="v2")

    def test_mock_returns_valid_v2_json(self, housing_messages_v2) -> None:
        client = MockModelClient()
        raw = client.generate(housing_messages_v2)
        parsed, error = parse_bench_memo_output_v2(raw)
        assert error is None
        assert parsed is not None
        assert isinstance(parsed, BenchMemoOutputV2)
        assert parsed.legal_area == "housing"
        assert parsed.recommended_action_type in {
            "temporary_relief",
            "urgent_hearing",
            "immediate_protection",
            "regular_hearing",
            "request_more_evidence",
            "reject",
        }
        assert 0 <= parsed.remedy_strength_score <= 5
        assert parsed.limitations == (
            "Non-binding: judicial review required before any action."
        )
        assert "requires_human_review" in parsed.risk_flags

    def test_parse_v3_hebrew_enums_coerced(self) -> None:
        from benchassist.model_client import parse_bench_memo_output_v3

        raw = json.dumps(
            {
                "case_summary": "סיכום",
                "legal_area": "housing",
                "urgency": "גבוהה",
                "recommended_action_type": "סעד זמני",
                "remedy_strength_score": 4,
                "evidence_burden_level": "בינוני",
                "party_credibility_framing": "יש לבחון את טענות הדייר.",
                "rights_orientation": "הגנה על זכויות הדייר",
                "procedural_posture": "בקשה לביטול הליך פינוי",
                "reasoning_text": "נדרש סעד זמני בגלל עובש.",
                "evidence_needed": [],
                "risk_flags": [],
                "confidence": 4,
                "limitations": "לא מחייב.",
                "cited_source_ids": ["IL-HOUS-001"],
                "source_usage_summary": "שימוש במקורות",
                "unsupported_legal_claims": [],
                "legal_hallucination_risk": "בינוני",
            },
            ensure_ascii=False,
        )
        parsed, error = parse_bench_memo_output_v3(raw)
        assert error is None
        assert parsed is not None
        assert parsed.urgency == "high"
        assert parsed.recommended_action_type == "temporary_relief"
        assert parsed.evidence_burden_level == "medium"
        assert parsed.confidence == "high"

    def test_mock_v2_high_urgency_for_mold_case(self, housing_messages_v2) -> None:
        client = MockModelClient()
        raw = client.generate(housing_messages_v2)
        parsed, _ = parse_bench_memo_output_v2(raw)
        assert parsed is not None
        assert parsed.urgency == "high"
        assert parsed.remedy_strength_score >= 3
