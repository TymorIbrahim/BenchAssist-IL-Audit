"""Deterministic keyword filters for Israeli detention / remand material."""

from __future__ import annotations

from dataclasses import dataclass, field

# Core inclusion keywords
INCLUSION_KEYWORDS: tuple[str, ...] = (
    "מעצר ימים",
    "הארכת מעצר",
    "מעצר עד תום ההליכים",
    "חשד סביר",
    "ראיות לכאורה",
    "עילת מעצר",
    "מסוכנות",
    "שיבוש הליכי חקירה",
    "השפעה על עדים",
    "הימלטות",
    "חלופת מעצר",
    "שחרור בערובה",
    "תנאי ערובה",
    "הצהרת תובע",
    'בש"פ',
    'מ"י',
)

# Extended inclusion terms (Sprint 2)
EXTENDED_INCLUSION_KEYWORDS: tuple[str, ...] = (
    "מעצרו של החשוד",
    "הארכת מעצרו",
    "חשש לשיבוש",
    "חשש להימלטות",
    "מסוכנות הנשקפת",
    "שחרור בתנאים",
    "פיקוח",
    "איזוק אלקטרוני",
    "ערובה צד ג׳",
    "ערובה צד ג'",
    "קצין מבחן",
    "תסקיר מעצר",
    "ערעור על מעצר",
    "בקשת מעצר",
)

ALL_INCLUSION_KEYWORDS: tuple[str, ...] = INCLUSION_KEYWORDS + EXTENDED_INCLUSION_KEYWORDS

SENSITIVE_KEYWORDS: tuple[str, ...] = (
    "קטין",
    "קטינה",
    "נוער",
    "עבירת מין",
    "אונס",
    "ביטחון המדינה",
    "טרור",
    "עבירת ביטחון",
    "מעצר מנהלי",
    "צו מעצר מנהלי",
    "משפחה",
    "חסוי",
    "איסור פרסום",
)

EXCLUSION_KEYWORDS = SENSITIVE_KEYWORDS

LIKELY_CASE_STAGES: tuple[str, ...] = (
    "pre_indictment_arrest_extension",
    "post_indictment_remand",
    "detention_appeal",
    "release_with_conditions",
    "obstruction_risk",
    "dangerousness",
    "weak_evidence_dispute",
    "legal_grounding",
    "unclear",
)

DETENTION_SUBTYPES: tuple[str, ...] = (
    "pre_indictment_arrest_extension",
    "obstruction_risk",
    "dangerousness",
    "release_with_conditions",
    "post_indictment_remand",
    "general_detention",
)


@dataclass
class DetentionRelevanceResult:
    """Extended relevance scoring for pilot corpus curation."""

    is_detention_related: bool
    detention_relevance_score: int
    matched_keywords: list[str] = field(default_factory=list)
    likely_case_stage: str = "unclear"
    sensitive_content_flag: bool = False
    sensitivity_reason: str = ""
    include_in_internal_expert_dashboard: bool = True
    include_in_model_inputs: bool = True
    requires_manual_legal_review: bool = False
    detention_subtype: str = "general_detention"
    filter_notes: list[str] = field(default_factory=list)

    @property
    def matched_inclusion(self) -> list[str]:
        return self.matched_keywords

    @property
    def excluded_sensitive(self) -> bool:
        return self.sensitive_content_flag

    @property
    def exclusion_reason(self) -> str:
        return self.sensitivity_reason


@dataclass
class DetentionFilterResult:
    """Backward-compatible filter result."""

    is_detention_related: bool
    matched_inclusion: list[str] = field(default_factory=list)
    sensitive_content_flag: bool = False
    sensitivity_reason: str = ""
    include_in_internal_expert_dashboard: bool = True
    include_in_model_inputs: bool = True
    requires_manual_legal_review: bool = False
    detention_subtype: str = "general_detention"
    filter_notes: list[str] = field(default_factory=list)
    detention_relevance_score: int = 0
    likely_case_stage: str = "unclear"

    @property
    def excluded_sensitive(self) -> bool:
        return self.sensitive_content_flag

    @property
    def exclusion_reason(self) -> str:
        return self.sensitivity_reason


def _find_matches(text: str, keywords: tuple[str, ...]) -> list[str]:
    if not text:
        return []
    return [kw for kw in keywords if kw in text]


def _score_keywords(matched: list[str]) -> int:
    """Higher weight for core statutory/procedural terms."""
    core = set(INCLUSION_KEYWORDS)
    score = 0
    for kw in matched:
        score += 2 if kw in core else 1
    return score


def infer_likely_case_stage(
    text: str,
    matched: list[str],
    *,
    source_type: str = "real_case_inspired",
) -> str:
    if source_type == "legal_grounding":
        return "legal_grounding"
    if source_type == "background_statistics":
        return "legal_grounding"

    joined = " ".join(matched)
    if any(k in text for k in ("ערעור", "בג\"ץ", "בגץ")) and any(
        k in text for k in ("מעצר", "מעצרו")
    ):
        return "detention_appeal"
    if "מעצר עד תום ההליכים" in joined or "מעצר עד תום ההליכים" in text:
        return "post_indictment_remand"
    if any(k in joined for k in ("שחרור בערובה", "חלופת מעצר", "תנאי ערובה", "שחרור בתנאים")):
        return "release_with_conditions"
    if any(k in joined for k in ("שיבוש", "עדים", "חקירה")) or "שיבוש הליכי חקירה" in text:
        return "obstruction_risk"
    if "מסוכנות" in joined or "מסוכנות" in text or "מסוכנות הנשקפת" in text:
        return "dangerousness"
    if any(k in joined for k in ("מעצר ימים", "הארכת מעצר", "הארכת מעצרו")):
        return "pre_indictment_arrest_extension"
    if ("חשד סביר" in text or "ראיות לכאורה" in text) and not any(
        k in text for k in ("מעצר עד תום", "הארכת מעצר")
    ):
        return "weak_evidence_dispute"
    return "unclear"


def infer_detention_subtype(text: str, matched: list[str]) -> str:
    stage = infer_likely_case_stage(text, matched)
    mapping = {
        "post_indictment_remand": "post_indictment_remand",
        "obstruction_risk": "obstruction_risk",
        "dangerousness": "dangerousness",
        "release_with_conditions": "release_with_conditions",
        "pre_indictment_arrest_extension": "pre_indictment_arrest_extension",
    }
    return mapping.get(stage, "general_detention")


def score_detention_relevance(
    text: str,
    *,
    source_type: str = "real_case_inspired",
    include_sensitive_in_internal_dashboard: bool = True,
) -> DetentionRelevanceResult:
    """Score detention relevance and assign case stage + sensitive flags."""
    matched = _find_matches(text, ALL_INCLUSION_KEYWORDS)
    matched_sensitive = _find_matches(text, SENSITIVE_KEYWORDS)
    score = _score_keywords(matched)
    is_related = score >= 1

    sensitive = bool(matched_sensitive)
    sensitivity_reason = "; ".join(matched_sensitive) if sensitive else ""
    notes: list[str] = []
    include_model = True
    requires_review = False

    if sensitive:
        include_model = False
        requires_review = True
        notes.append(
            f"Sensitive-content keyword(s): {sensitivity_reason}. "
            "Excluded from model inputs by default."
        )
    if not is_related:
        notes.append("No detention/remand inclusion keywords matched.")

    stage = infer_likely_case_stage(text, matched, source_type=source_type) if is_related else "unclear"
    subtype = infer_detention_subtype(text, matched) if is_related else "general_detention"

    return DetentionRelevanceResult(
        is_detention_related=is_related,
        detention_relevance_score=score,
        matched_keywords=matched,
        likely_case_stage=stage,
        sensitive_content_flag=sensitive,
        sensitivity_reason=sensitivity_reason,
        include_in_internal_expert_dashboard=include_sensitive_in_internal_dashboard,
        include_in_model_inputs=include_model and not sensitive,
        requires_manual_legal_review=requires_review or sensitive,
        detention_subtype=subtype,
        filter_notes=notes,
    )


def apply_detention_filters(
    text: str,
    *,
    include_sensitive_in_internal_dashboard: bool = True,
    source_type: str = "real_case_inspired",
) -> DetentionFilterResult:
    """Backward-compatible wrapper around :func:`score_detention_relevance`."""
    result = score_detention_relevance(
        text,
        source_type=source_type,
        include_sensitive_in_internal_dashboard=include_sensitive_in_internal_dashboard,
    )
    return DetentionFilterResult(
        is_detention_related=result.is_detention_related,
        matched_inclusion=result.matched_keywords,
        sensitive_content_flag=result.sensitive_content_flag,
        sensitivity_reason=result.sensitivity_reason,
        include_in_internal_expert_dashboard=result.include_in_internal_expert_dashboard,
        include_in_model_inputs=result.include_in_model_inputs,
        requires_manual_legal_review=result.requires_manual_legal_review,
        detention_subtype=result.detention_subtype,
        filter_notes=result.filter_notes,
        detention_relevance_score=result.detention_relevance_score,
        likely_case_stage=result.likely_case_stage,
    )
