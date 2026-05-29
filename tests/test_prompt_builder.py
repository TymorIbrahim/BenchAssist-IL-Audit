"""Tests for prompt construction."""

from __future__ import annotations

import pytest

from benchassist.data_generation import create_base_cases, create_counterfactual_cases
from benchassist.prompt_builder import (
    build_counterfactual_messages,
    build_counterfactual_user_prompt,
    load_system_prompt,
)


@pytest.fixture()
def sample_counterfactual():
    return create_counterfactual_cases(create_base_cases())[0]


class TestLoadSystemPrompt:
    def test_loads_non_empty_system_prompt(self) -> None:
        prompt = load_system_prompt()
        assert len(prompt.strip()) > 0

    def test_includes_non_binding_warning(self) -> None:
        prompt = load_system_prompt()
        assert "non-binding" in prompt.lower()
        assert "must not make a final legal decision" in prompt.lower()

    def test_includes_valid_json_instruction(self) -> None:
        prompt = load_system_prompt()
        assert "valid JSON" in prompt
        assert '"case_summary"' in prompt
        assert '"urgency"' in prompt
        assert '"limitations"' in prompt


class TestCounterfactualPrompts:
    def test_user_prompt_includes_case_text(self, sample_counterfactual) -> None:
        user_prompt = build_counterfactual_user_prompt(sample_counterfactual)
        assert sample_counterfactual.input_text in user_prompt

    def test_user_prompt_includes_no_new_facts_instruction(
        self, sample_counterfactual
    ) -> None:
        user_prompt = build_counterfactual_user_prompt(sample_counterfactual)
        assert "Do not add legal facts" in user_prompt

    def test_user_prompt_includes_hebrew_instruction_for_hebrew_input(
        self, sample_counterfactual
    ) -> None:
        assert sample_counterfactual.language == "he"
        user_prompt = build_counterfactual_user_prompt(sample_counterfactual)
        assert "in Hebrew" in user_prompt

    def test_messages_include_system_and_user_roles(
        self, sample_counterfactual
    ) -> None:
        messages = build_counterfactual_messages(sample_counterfactual)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_messages_user_content_includes_case_text(
        self, sample_counterfactual
    ) -> None:
        messages = build_counterfactual_messages(sample_counterfactual)
        assert sample_counterfactual.input_text in messages[1]["content"]

    def test_messages_system_content_includes_json_instruction(
        self, sample_counterfactual
    ) -> None:
        messages = build_counterfactual_messages(sample_counterfactual)
        system = messages[0]["content"]
        assert "valid JSON" in system
        assert '"recommended_direction"' in system

    def test_messages_system_content_includes_non_binding_warning(
        self, sample_counterfactual
    ) -> None:
        messages = build_counterfactual_messages(sample_counterfactual)
        system = messages[0]["content"]
        assert "non-binding" in system.lower()
        assert "must not claim to replace the judge" in system
