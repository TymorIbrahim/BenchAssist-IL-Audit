"""Pydantic data models for BenchAssist-IL.

Defines the canonical schemas used throughout the audit pipeline:
base cases, counterfactual variants, bench-memo outputs, and run records.

Legacy models (``ApplicableLaw``, ``BenchMemo``, ``CaseSummary``,
``CounterfactualPair``) are retained at the bottom of this module for
backward compatibility with existing pipeline code.
"""

from __future__ import annotations

import json
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════
# New core models (v2)
# ═══════════════════════════════════════════════════════════════════════════

Urgency = Literal["low", "medium", "high"]
Confidence = Literal["low", "medium", "high"]
RecommendedActionType = Literal[
    "reject",
    "request_more_evidence",
    "regular_hearing",
    "urgent_hearing",
    "temporary_relief",
    "immediate_protection",
]
EvidenceBurdenLevel = Literal["low", "medium", "high"]
PartyCredibilityFraming = Literal["supportive", "neutral", "skeptical"]
RightsOrientation = Literal["low", "medium", "high"]
ProceduralPosture = Literal[
    "continue_regular_process",
    "expedited_review",
    "urgent_intervention",
]
LegalHallucinationRisk = Literal["low", "medium", "high"]

_REMEDY_SCORE_BY_ACTION: dict[str, int] = {
    "reject": 0,
    "request_more_evidence": 1,
    "regular_hearing": 2,
    "urgent_hearing": 3,
    "temporary_relief": 4,
    "immediate_protection": 5,
}


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
    transformation_style: str = Field(
        default="",
        description=(
            "Linguistic transformation style (e.g. 'formal_clerk', 'simple_plain', "
            "'broken_non_native'). Empty for legacy demographic-only variants."
        ),
    )
    input_text: str = Field(
        ..., description="Full case text sent to the model."
    )
    expected_urgency: str = Field(
        default="", description="Expected urgency (should match BaseCase)."
    )
    expected_direction: str = Field(
        default="", description="Expected direction (should match BaseCase)."
    )
    strict_counterfactual_candidate: bool = Field(
        default=True,
        description="Whether this variant is intended as a strict factual counterfactual.",
    )
    framing_axis: str = Field(
        default="",
        description="Narrative framing axis (e.g. emotionality, credibility_priming).",
    )
    framing_direction: str = Field(
        default="",
        description="Narrative framing direction (e.g. skeptical, tenant_favorable).",
    )
    # Dataset layer metadata (synthetic controlled vs real-case-inspired)
    dataset_mode: str = Field(
        default="synthetic_controlled",
        description="Audit dataset layer: synthetic_controlled, real_case_inspired, or hybrid.",
    )
    source_type: str = Field(default="", description="Provenance type for real-case layer.")
    source_dataset: str = Field(default="", description="Source dataset id/name if applicable.")
    source_id: str = Field(default="", description="Source record identifier.")
    source_domain: str = Field(default="", description="Original domain label from source.")
    normalized_domain: str = Field(default="", description="Normalized multi-domain taxonomy id.")
    source_license: str = Field(default="", description="License note if available.")
    is_synthetic: bool = Field(default=True, description="True for synthetic controlled audit cases.")
    is_real_case_inspired: bool = Field(
        default=False,
        description="True for source-derived real-case-inspired examples.",
    )
    counterfactual_strength: str = Field(
        default="strict",
        description="strict, approximate, stress_test, or not_counterfactual.",
    )
    use_for_strict_bias_rates: bool = Field(
        default=True,
        description="Whether row may enter main strict fairness rate tables.",
    )
    use_for_reliability_audit: bool = Field(
        default=False,
        description="Whether row is intended for real-case reliability audit.",
    )
    legal_area: str = Field(default="", description="Legal area label (may mirror normalized_domain).")
    source_note: str = Field(default="", description="Provenance note for the input case.")
    license_note: str = Field(default="", description="License/attribution note for real cases.")
    attribution_note: str = Field(default="", description="Attribution text for real-case sources.")


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


class LegalSource(BaseModel):
    """A toy legal-information snippet in the local knowledge base."""

    source_id: str
    source_type: str
    title: str
    jurisdiction: str
    legal_area: str
    language: str
    text: str
    tags: list[str] = Field(default_factory=list)
    caution: str


class RetrievedSource(BaseModel):
    """A source snippet retrieved for a case query."""

    source_id: str
    title: str
    relevance_score: float
    text: str


class BenchMemoOutputV2(BaseModel):
    """Structured bench memo (schema v2) with categorical legal-framing fields.

    Separates recommendation type, remedy strength, evidentiary burden,
    credibility framing, rights orientation, and procedural posture from
    free-text reasoning so audit metrics can compare substantive changes
    without noise from harmless paraphrasing.
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
    recommended_action_type: RecommendedActionType = Field(
        ...,
        description=(
            "Categorical recommended procedural action: reject, request_more_evidence, "
            "regular_hearing, urgent_hearing, temporary_relief, or immediate_protection."
        ),
    )
    remedy_strength_score: int = Field(
        ...,
        ge=0,
        le=5,
        description=(
            "0=reject/no action, 1=request evidence only, 2=regular hearing, "
            "3=urgent hearing, 4=temporary relief, 5=immediate protection."
        ),
    )
    evidence_burden_level: EvidenceBurdenLevel = Field(
        ...,
        description="How much additional evidence the judge should require before acting.",
    )
    party_credibility_framing: PartyCredibilityFraming = Field(
        ...,
        description="Whether the memo frames the petitioner's account as supportive, neutral, or skeptical.",
    )
    rights_orientation: RightsOrientation = Field(
        ...,
        description="Degree to which the memo emphasizes protective/rights-based considerations.",
    )
    procedural_posture: ProceduralPosture = Field(
        ...,
        description=(
            "Suggested procedural track: continue_regular_process, expedited_review, "
            "or urgent_intervention."
        ),
    )
    reasoning_text: str = Field(
        ..., description="Model's reasoning for the recommendation."
    )
    evidence_needed: list[str] = Field(
        default_factory=list,
        description="Additional evidence the model recommends gathering.",
    )
    risk_flags: list[str] = Field(
        default_factory=list,
        description="Structured risk flags (e.g. possible_urgent_harm, missing_evidence).",
    )
    confidence: Confidence = Field(
        ..., description="Model's stated confidence level."
    )
    limitations: str = Field(
        ...,
        description="Caveats or limitations acknowledged by the model.",
    )


class BenchMemoOutputV3(BenchMemoOutputV2):
    """Schema v3: V2 legal-framing fields plus source-grounding metadata."""

    cited_source_ids: list[str] = Field(
        default_factory=list,
        description="Source IDs from the provided allowed snippet list used in the memo.",
    )
    source_usage_summary: str = Field(
        default="",
        description="Brief explanation of how provided sources informed the memo.",
    )
    unsupported_legal_claims: list[str] = Field(
        default_factory=list,
        description="Legal claims in the memo not supported by provided sources.",
    )
    legal_hallucination_risk: LegalHallucinationRisk = Field(
        default="low",
        description="Screening risk that the memo cites or invents unsupported legal authority.",
    )


BenchMemoOutputLike = Union[
    BenchMemoOutput,
    BenchMemoOutputV2,
    BenchMemoOutputV3,
    dict[str, Any],
]


def _infer_recommended_action_type_from_text(
    recommended_direction: str | None,
    recommended_action: str | None,
) -> RecommendedActionType:
    """Map legacy free-text direction/action to a V2 action type."""
    combined = f"{recommended_direction or ''} {recommended_action or ''}".lower()

    reject_keywords = (
        "reject",
        "deny",
        "dismiss",
        "דחי",
        "לדחות",
        "שליל",
    )
    evidence_keywords = (
        "more evidence",
        "additional evidence",
        "request evidence",
        "gather evidence",
        "evidence only",
        "ראיות נוספות",
        "השלמת ראיות",
        "נדרש ביסוס",
        "לא ברור",
        "unclear",
        "missing document",
        "חסר מסמך",
    )
    immediate_keywords = (
        "immediate protection",
        "immediate intervention",
        "immediate relief",
        "הגנה מיידית",
        "החזרת החזקה",
        "לאלתר",
        "מנעול",
        "lock",
        "exclusion",
        "הרחקה מיידית",
    )
    temporary_keywords = (
        "temporary relief",
        "temporary protection",
        "סעד זמני",
        "צו מניעה",
        "restraining order",
        "עיכוב פינוי",
    )
    urgent_keywords = (
        "urgent hearing",
        "דיון דחוף",
        "סעד דחוף",
        "expedited",
        "דחוף",
    )
    regular_keywords = (
        "regular hearing",
        "ordinary procedure",
        "hearing",
        "דיון",
        "שימוע",
        "procedure",
        "בדיקה שיפוטית",
    )

    if any(kw in combined for kw in reject_keywords):
        return "reject"
    if any(kw in combined for kw in evidence_keywords):
        return "request_more_evidence"
    if any(kw in combined for kw in immediate_keywords):
        return "immediate_protection"
    if any(kw in combined for kw in temporary_keywords):
        return "temporary_relief"
    if any(kw in combined for kw in urgent_keywords):
        return "urgent_hearing"
    if any(kw in combined for kw in regular_keywords):
        return "regular_hearing"

    direction = (recommended_direction or "").strip().lower()
    if direction in {"deny", "reject", "dismiss"}:
        return "reject"
    if direction in {"partial"}:
        return "regular_hearing"
    if direction in {"grant"}:
        return "temporary_relief"
    return "regular_hearing"


def _infer_rights_orientation_from_text(*texts: str | None) -> RightsOrientation:
    combined = " ".join(t for t in texts if t).lower()
    high_keywords = (
        "rights",
        "protection",
        "protective",
        "זכויות",
        "הגנה",
        "סעד זמני",
        "temporary relief",
        "immediate protection",
        "vulnerable",
        "פגיע",
        "קטין",
        "קטינים",
        "elderly",
        "מוגבלות",
        "disability",
    )
    low_keywords = (
        "no basis",
        "insufficient",
        "unsupported",
        "אין בסיס",
        "חסר ביסוס",
    )
    high_hits = sum(1 for kw in high_keywords if kw in combined)
    low_hits = sum(1 for kw in low_keywords if kw in combined)
    if high_hits >= 2 or (high_hits >= 1 and low_hits == 0):
        return "high"
    if low_hits >= 2:
        return "low"
    if high_hits == 1:
        return "medium"
    return "medium"


_LEVEL_LITERALS: frozenset[str] = frozenset({"low", "medium", "high"})
_VALID_ACTION_TYPES: frozenset[str] = frozenset(
    {
        "reject",
        "request_more_evidence",
        "regular_hearing",
        "urgent_hearing",
        "temporary_relief",
        "immediate_protection",
    }
)
_VALID_CREDIBILITY: frozenset[str] = frozenset({"supportive", "neutral", "skeptical"})
_VALID_PROCEDURAL: frozenset[str] = frozenset(
    {"continue_regular_process", "expedited_review", "urgent_intervention"}
)

_HEBREW_LEVEL_MAP: dict[str, str] = {
    "גבוהה": "high",
    "גבוה": "high",
    "בינוני": "medium",
    "בינונית": "medium",
    "נמוכה": "low",
    "נמוך": "low",
}


def _coerce_level_literal(value: Any, *, default: str = "medium") -> str:
    """Map Hebrew or numeric level labels to low/medium/high."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        numeric = int(value)
        if numeric >= 4:
            return "high"
        if numeric <= 1:
            return "low"
        return "medium"
    text = str(value).strip()
    lowered = text.lower()
    if lowered in _LEVEL_LITERALS:
        return lowered
    for hebrew, english in _HEBREW_LEVEL_MAP.items():
        if hebrew in text:
            return english
    if any(kw in lowered for kw in ("high", "urgent", "דחוף", "גבוה")):
        return "high"
    if any(kw in lowered for kw in ("low", "נמוך")):
        return "low"
    return default


def coerce_parsed_bench_memo_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Coerce Gemini Hebrew or free-text fields into V2/V3 schema literals."""
    out = dict(data)
    reasoning = str(
        out.get("reasoning_text") or out.get("reasoning") or out.get("case_summary") or ""
    )

    for field in (
        "urgency",
        "evidence_burden_level",
        "confidence",
        "rights_orientation",
        "legal_hallucination_risk",
    ):
        if field in out:
            out[field] = _coerce_level_literal(out[field])

    action_raw = out.get("recommended_action_type")
    if action_raw not in _VALID_ACTION_TYPES:
        out["recommended_action_type"] = _infer_recommended_action_type_from_text(
            out.get("recommended_direction"),
            str(action_raw or out.get("recommended_action") or ""),
        )

    credibility = out.get("party_credibility_framing")
    if credibility not in _VALID_CREDIBILITY:
        out["party_credibility_framing"] = _infer_credibility_framing_from_text(
            str(credibility or ""),
            reasoning,
        )

    posture = out.get("procedural_posture")
    if posture not in _VALID_PROCEDURAL:
        out["procedural_posture"] = _infer_procedural_posture(
            str(out.get("urgency", "medium")),
            out["recommended_action_type"],  # type: ignore[arg-type]
        )

    if out.get("remedy_strength_score") is None or not isinstance(
        out.get("remedy_strength_score"), int
    ):
        out["remedy_strength_score"] = _REMEDY_SCORE_BY_ACTION.get(
            str(out.get("recommended_action_type", "regular_hearing")),
            2,
        )

    if "legal_hallucination_risk" not in out:
        out["legal_hallucination_risk"] = "low"

    for list_field in ("evidence_needed", "risk_flags", "cited_source_ids", "unsupported_legal_claims"):
        value = out.get(list_field)
        if value is None:
            out[list_field] = []
        elif isinstance(value, str):
            try:
                parsed = json.loads(value)
                out[list_field] = parsed if isinstance(parsed, list) else [value]
            except json.JSONDecodeError:
                out[list_field] = [value] if value.strip() else []

    for str_field in (
        "limitations",
        "reasoning_text",
        "reasoning",
        "case_summary",
        "source_usage_summary",
    ):
        value = out.get(str_field)
        if isinstance(value, list):
            out[str_field] = " ".join(str(part).strip() for part in value if str(part).strip())
        elif value is not None and not isinstance(value, str):
            out[str_field] = str(value)

    retrieved = out.get("retrieved_source_ids")
    if isinstance(retrieved, str):
        try:
            parsed = json.loads(retrieved)
            out["retrieved_source_ids"] = parsed if isinstance(parsed, list) else [retrieved]
        except json.JSONDecodeError:
            out["retrieved_source_ids"] = [retrieved] if retrieved.strip() else []

    return out


def _infer_procedural_posture(
    urgency: str,
    recommended_action_type: RecommendedActionType,
) -> ProceduralPosture:
    if recommended_action_type in {
        "immediate_protection",
        "temporary_relief",
    } or urgency == "high":
        return "urgent_intervention"
    if recommended_action_type in {"urgent_hearing", "request_more_evidence"}:
        return "expedited_review"
    return "continue_regular_process"


def _infer_credibility_framing_from_text(*texts: str | None) -> PartyCredibilityFraming:
    combined = " ".join(t for t in texts if t).lower()
    skeptical_keywords = (
        "unsupported",
        "unclear",
        "insufficient",
        "not credible",
        "חסר ביסוס",
        "לא ברור",
        "לא נתמך",
        "ספק",
    )
    supportive_keywords = (
        "credible",
        "well-supported",
        "documented",
        "מבוסס",
        "מוכח",
        "תיעוד",
    )
    if any(kw in combined for kw in skeptical_keywords):
        return "skeptical"
    if any(kw in combined for kw in supportive_keywords):
        return "supportive"
    return "neutral"


def normalize_bench_memo_output(
    output: BenchMemoOutputLike,
) -> dict[str, Any]:
    """Normalize v1 or v2 bench memo outputs to a common audit dictionary.

    Accepts :class:`BenchMemoOutput`, :class:`BenchMemoOutputV2`, or raw dicts
    from either schema.  Missing V2 fields on legacy outputs are inferred with
    conservative heuristics so existing CSV results remain usable.
    """
    if isinstance(output, BenchMemoOutputV2):
        base = {
            "legal_area": output.legal_area,
            "urgency": output.urgency,
            "recommended_action_type": output.recommended_action_type,
            "remedy_strength_score": output.remedy_strength_score,
            "evidence_burden_level": output.evidence_burden_level,
            "party_credibility_framing": output.party_credibility_framing,
            "rights_orientation": output.rights_orientation,
            "procedural_posture": output.procedural_posture,
            "reasoning_text": output.reasoning_text,
            "evidence_needed": list(output.evidence_needed),
            "confidence": output.confidence,
            "limitations": output.limitations,
        }
        if isinstance(output, BenchMemoOutputV3):
            base.update(
                {
                    "cited_source_ids": list(output.cited_source_ids),
                    "source_usage_summary": output.source_usage_summary,
                    "unsupported_legal_claims": list(output.unsupported_legal_claims),
                    "legal_hallucination_risk": output.legal_hallucination_risk,
                }
            )
        return base

    if isinstance(output, BenchMemoOutput):
        data = output.model_dump()
    elif isinstance(output, dict):
        data = dict(output)
    else:
        raise TypeError(
            "output must be BenchMemoOutput, BenchMemoOutputV2, or a dict"
        )

    if "cited_source_ids" in data or "legal_hallucination_risk" in data:
        memo_v3 = BenchMemoOutputV3(**data)
        return normalize_bench_memo_output(memo_v3)

    if "recommended_action_type" in data:
        memo_v2 = BenchMemoOutputV2(**data)
        return normalize_bench_memo_output(memo_v2)

    recommended_direction = data.get("recommended_direction")
    recommended_action = data.get("recommended_action")
    reasoning = data.get("reasoning") or data.get("reasoning_text") or ""
    urgency = data.get("urgency", "medium")

    recommended_action_type = _infer_recommended_action_type_from_text(
        recommended_direction,
        recommended_action,
    )
    remedy_strength_score = _REMEDY_SCORE_BY_ACTION[recommended_action_type]
    evidence_burden_level: EvidenceBurdenLevel = "medium"
    party_credibility_framing = _infer_credibility_framing_from_text(
        reasoning,
        recommended_action,
    )
    rights_orientation = _infer_rights_orientation_from_text(
        reasoning,
        recommended_action,
        recommended_direction,
    )
    procedural_posture = _infer_procedural_posture(
        str(urgency),
        recommended_action_type,
    )

    return {
        "legal_area": data.get("legal_area", ""),
        "urgency": urgency,
        "recommended_action_type": recommended_action_type,
        "remedy_strength_score": remedy_strength_score,
        "evidence_burden_level": evidence_burden_level,
        "party_credibility_framing": party_credibility_framing,
        "rights_orientation": rights_orientation,
        "procedural_posture": procedural_posture,
        "reasoning_text": reasoning,
        "evidence_needed": list(data.get("evidence_needed") or []),
        "confidence": data.get("confidence", "medium"),
        "limitations": data.get("limitations", ""),
    }


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
