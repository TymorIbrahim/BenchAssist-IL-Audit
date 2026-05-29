"""Tests for model client and bench-memo parsing."""

from __future__ import annotations

import json

import pytest

from benchassist.data_generation import create_base_cases, create_counterfactual_cases
from benchassist.model_client import (
    MockModelClient,
    parse_bench_memo_output,
)
from benchassist.prompt_builder import build_counterfactual_messages
from benchassist.schemas import BenchMemoOutput
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
