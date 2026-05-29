"""Pydantic data models for BenchAssist-IL.

Defines the canonical schemas used throughout the audit pipeline:
base cases, counterfactual variants, bench-memo outputs, and run records.

Legacy models (``ApplicableLaw``, ``BenchMemo``, ``CaseSummary``,
``CounterfactualPair``) are retained at the bottom of this module for
backward compatibility with existing pipeline code.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════
# New core models (v2)
# ═══════════════════════════════════════════════════════════════════════════

Urgency = Literal["low", "medium", "high"]
Confidence = Literal["low", "medium", "high"]


class BaseCase(BaseModel):
    """A synthetic base legal-case used as the starting point for auditing.

    Contains the canonical facts in Hebrew (and optionally English) plus
    the expected outcome annotations used to evaluate model behaviour.
    """

    case_id: str = Field(..., description="Unique case identifier.")
    legal_area: str = Field(
        ..., description="Area of law (e.g. criminal, civil, family)."
    )
    title: str = Field(..., description="Short human-readable case title.")
    base_facts_he: str = Field(
        ..., description="Case facts written in Hebrew."
    )
    base_facts_en: Optional[str] = Field(
        default=None, description="Optional English translation of the facts."
    )
    requested_remedy: str = Field(
        ..., description="Remedy or relief sought by the petitioner."
    )
    expected_urgency: Urgency = Field(
        ..., description="Ground-truth urgency label for evaluation."
    )
    expected_direction: str = Field(
        ...,
        description="Expected recommendation direction (e.g. 'grant', 'deny').",
    )
    source_note: str = Field(
        ...,
        description="Provenance note (e.g. 'synthetic', 'adapted from ...').",
    )


class CounterfactualCase(BaseModel):
    """A variant derived from a :class:`BaseCase` with a single demographic
    or linguistic perturbation applied.  Legal facts are unchanged."""

    case_id: str = Field(
        ..., description="ID of the originating BaseCase."
    )
    variant_id: str = Field(
        ..., description="Unique ID for this specific variant."
    )
    variant_type: str = Field(
        ...,
        description="Category of perturbation (e.g. 'name_swap', 'language').",
    )
    demographic_cue: str = Field(
        ...,
        description="Demographic signal embedded in the variant (e.g. 'Arab-Palestinian').",
    )
    language: str = Field(
        ..., description="Language of the input text (e.g. 'he', 'ar', 'en')."
    )
    input_text: str = Field(
        ..., description="Full case text sent to the model."
    )
    expected_urgency: str = Field(
        ..., description="Expected urgency (should match BaseCase)."
    )
    expected_direction: str = Field(
        ..., description="Expected direction (should match BaseCase)."
    )


class BenchMemoOutput(BaseModel):
    """Structured bench memo returned by the model.

    This is the schema we instruct the model to produce (via
    ``prompts/bench_memo_schema.json``) and that we parse from its raw output.
    """

    case_summary: str = Field(
        ..., description="Brief summary of the case as understood by the model."
    )
    legal_area: str = Field(
        ..., description="Legal domain identified by the model."
    )
    urgency: Urgency = Field(
        ..., description="Model's assessment of case urgency."
    )
    recommended_direction: str = Field(
        ...,
        description="High-level direction (e.g. 'grant', 'deny', 'dismiss').",
    )
    recommended_action: str = Field(
        ..., description="Specific action the judge should consider."
    )
    reasoning: str = Field(
        ..., description="Model's reasoning for the recommendation."
    )
    evidence_needed: list[str] = Field(
        default_factory=list,
        description="Additional evidence the model recommends gathering.",
    )
    confidence: Confidence = Field(
        ..., description="Model's stated confidence level."
    )
    limitations: str = Field(
        ...,
        description="Caveats or limitations acknowledged by the model.",
    )


class ModelRunRecord(BaseModel):
    """A single model invocation record, linking input, raw output, and
    (optionally) a parsed :class:`BenchMemoOutput`."""

    run_id: str = Field(..., description="Unique run identifier.")
    case_id: str = Field(..., description="Originating BaseCase ID.")
    variant_id: str = Field(
        ..., description="CounterfactualCase variant ID (or 'base')."
    )
    variant_type: str = Field(
        ..., description="Perturbation category (or 'base')."
    )
    demographic_cue: str = Field(
        ..., description="Demographic signal in the input."
    )
    language: str = Field(..., description="Input language code.")
    input_text: str = Field(..., description="Full prompt text sent to model.")
    raw_output: str = Field(
        ..., description="Raw string returned by the model."
    )
    parsed_output: Optional[BenchMemoOutput] = Field(
        default=None,
        description="Parsed bench memo, or None if parsing failed.",
    )
    parse_error: Optional[str] = Field(
        default=None,
        description="Error message if raw_output could not be parsed.",
    )
    model_name: str = Field(
        ..., description="Identifier of the model used for this run."
    )
    timestamp: str = Field(
        ..., description="ISO-8601 timestamp of the run."
    )


# ═══════════════════════════════════════════════════════════════════════════
# Legacy models (v1) — kept for backward compatibility with existing
# pipeline modules (data_generation, model_client, audit_metrics, etc.)
# ═══════════════════════════════════════════════════════════════════════════

AreaOfLaw = Literal[
    "criminal",
    "civil",
    "family",
    "labor",
    "administrative",
    "constitutional",
    "real_estate",
    "immigration",
    "tax",
    "military",
]


class ApplicableLaw(BaseModel):
    """A reference to a specific legal source and provision."""

    source: str = Field(
        ...,
        description="Name or title of the legal source (e.g. statute, regulation).",
    )
    reference: str = Field(
        ..., description="Section / article reference within the source."
    )


class BenchMemo(BaseModel):
    """Structured judicial bench memo produced by the model (legacy v1)."""

    case_id: str = Field(..., description="Unique case identifier.")
    area_of_law: AreaOfLaw = Field(
        ..., description="Legal domain classification."
    )
    key_issues: list[str] = Field(
        default_factory=list, description="List of key legal issues."
    )
    applicable_law: list[ApplicableLaw] = Field(
        default_factory=list,
        description="Applicable statutes / regulations.",
    )
    recommendation: str = Field(
        ..., description="Recommended disposition or action."
    )
    confidence: Literal["high", "medium", "low"] = Field(
        ..., description="Model's stated confidence level."
    )
    flags: list[str] = Field(
        default_factory=list,
        description="Risk or bias flags raised during analysis.",
    )


class CaseSummary(BaseModel):
    """A synthetic legal case summary used as model input (legacy v1)."""

    case_id: str = Field(..., description="Unique case identifier.")
    description: str = Field(
        ..., description="Narrative description of the case facts."
    )
    area_of_law: str = Field(
        ...,
        description="Legal domain (free-text, mapped to AreaOfLaw downstream).",
    )
    parties: list[dict] = Field(
        default_factory=list,
        description="List of party dicts, e.g. [{'role': 'plaintiff', 'name': '...'}].",
    )
    demographic_group: Optional[str] = Field(
        default=None,
        description="Optional label for the demographic group of the primary party.",
    )
    language_cue: Optional[str] = Field(
        default=None,
        description="Optional language or cultural cue embedded in the description.",
    )


class CounterfactualPair(BaseModel):
    """A pair of case summaries differing only in demographic / language cues (legacy v1)."""

    base: CaseSummary
    variant: CaseSummary
    perturbation_type: str = Field(
        ...,
        description="Category of perturbation applied (e.g. 'name_swap', 'language_cue').",
    )
    perturbation_detail: str = Field(
        ..., description="Human-readable description of what was changed."
    )
