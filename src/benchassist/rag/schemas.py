"""Pydantic data models for the Agentic RAG pipeline.

Defines document chunk schemas, retrieval result models, agent output
structures, and API request/response schemas for the judicial reasoning
pipeline.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Document chunk models
# ---------------------------------------------------------------------------


class LegalChunk(BaseModel):
    """A chunked section from an Israeli legal document."""

    document_name: str = Field(
        ..., description="Source document filename or identifier."
    )
    section_id: str = Field(
        ..., description="Unique section identifier within the document."
    )
    section_title: str = Field(
        ..., description="Title or heading of this section."
    )
    text: str = Field(
        ..., description="Full text content of this chunk."
    )
    language: Literal["he", "en"] = Field(
        ..., description="Language of the chunk content."
    )
    topic_tags: list[str] = Field(
        default_factory=list,
        description="Topic tags for retrieval filtering.",
    )
    parent_section_id: Optional[str] = Field(
        default=None,
        description="Parent section ID for hierarchical documents.",
    )


class RetrievedChunk(LegalChunk):
    """A legal chunk returned from a search query, with relevance metadata."""

    score: float = Field(
        ..., description="Relevance score (higher is more relevant)."
    )
    retrieval_method: Literal["vector", "bm25", "hybrid"] = Field(
        ..., description="Method used to retrieve this chunk."
    )


# ---------------------------------------------------------------------------
# Citation and output models
# ---------------------------------------------------------------------------


class LegalCitation(BaseModel):
    """A specific legal citation referenced in the agent's reasoning."""

    section: str = Field(
        ...,
        description="Section reference (e.g. 'Section 21(a)(1)').",
    )
    document: str = Field(
        ..., description="Source document name."
    )
    relevance: str = Field(
        ..., description="Brief explanation of why this section is relevant."
    )
    quote: str = Field(
        ..., description="Relevant quote from the section."
    )


RecommendationType = Literal[
    "detention_extension",
    "release_with_conditions",
    "alternative_detention",
]
RiskLevel = Literal["low", "medium", "high"]


class AgentOutput(BaseModel):
    """Full structured output from the judicial reasoning agent."""

    recommendation: RecommendationType = Field(
        ...,
        description="Primary recommendation: detention_extension, release_with_conditions, or alternative_detention.",
    )
    public_safety_risk: RiskLevel = Field(
        ..., description="Assessed public safety risk level."
    )
    obstruction_risk: RiskLevel = Field(
        ..., description="Risk of obstruction of justice."
    )
    recidivism_risk: RiskLevel = Field(
        ..., description="Risk of reoffending."
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Model confidence score (0–1)."
    )
    reasoning: str = Field(
        ..., description="Detailed reasoning narrative."
    )
    legal_citations: list[LegalCitation] = Field(
        default_factory=list,
        description="Legal sections cited in the reasoning.",
    )
    legal_basis_summary: str = Field(
        ..., description="Summary of the legal basis for the recommendation."
    )
    alternatives_considered: list[str] = Field(
        default_factory=list,
        description="Alternative dispositions considered and why they were rejected.",
    )
    retrieved_provisions: list[str] = Field(
        default_factory=list,
        description="Legal provisions retrieved and used in reasoning.",
    )
    retrieval_queries: list[str] = Field(
        default_factory=list,
        description="Search queries used to retrieve legal provisions.",
    )
    reasoning_steps: list[str] = Field(
        default_factory=list,
        description="Step-by-step reasoning trace.",
    )


# ---------------------------------------------------------------------------
# API models
# ---------------------------------------------------------------------------


class AssessRequest(BaseModel):
    """Request body for the /assess endpoint."""

    case_text: str = Field(
        ..., description="Full case text to assess."
    )
    case_id: str = Field(
        ..., description="Identifier for this case."
    )
    variant_id: Optional[str] = Field(
        default=None,
        description="Optional variant identifier for counterfactual auditing.",
    )
    language: str = Field(
        default="en",
        description="Language of the case text ('en' or 'he').",
    )
    prompt_mode: str = Field(
        default="baseline",
        description="Prompt mode: baseline, fairness_aware, or demographic_blind.",
    )


class AssessResponse(BaseModel):
    """Response body from the /assess endpoint.

    Combines the full AgentOutput with request metadata and timing info.
    """

    # --- AgentOutput fields ---
    recommendation: RecommendationType
    public_safety_risk: RiskLevel
    obstruction_risk: RiskLevel
    recidivism_risk: RiskLevel
    confidence: float
    reasoning: str
    legal_citations: list[LegalCitation] = Field(default_factory=list)
    legal_basis_summary: str
    alternatives_considered: list[str] = Field(default_factory=list)
    retrieved_provisions: list[str] = Field(default_factory=list)
    retrieval_queries: list[str] = Field(default_factory=list)
    reasoning_steps: list[str] = Field(default_factory=list)

    # --- Metadata ---
    case_id: str = Field(..., description="Echo of the request case ID.")
    variant_id: Optional[str] = Field(
        default=None, description="Echo of the request variant ID."
    )
    model_name: str = Field(
        ..., description="Name of the model used for reasoning."
    )
    processing_time_ms: float = Field(
        ..., description="Total processing time in milliseconds."
    )

    @classmethod
    def from_agent_output(
        cls,
        output: AgentOutput,
        *,
        case_id: str,
        variant_id: str | None,
        model_name: str,
        processing_time_ms: float,
    ) -> AssessResponse:
        """Construct from an AgentOutput plus request metadata."""
        return cls(
            **output.model_dump(),
            case_id=case_id,
            variant_id=variant_id,
            model_name=model_name,
            processing_time_ms=processing_time_ms,
        )
