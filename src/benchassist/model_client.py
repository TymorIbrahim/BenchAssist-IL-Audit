"""Model client abstraction for BenchAssist-IL.

Provides a protocol-based interface (:class:`ModelClient`) with:

* **MockModelClient** – deterministic, offline JSON responses.
* **GeminiModelClient** – optional Google Gemini via ``google-genai`` (lazy import).
"""

from __future__ import annotations

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from pydantic import ValidationError

from benchassist.config import get_settings, resolve_gemini_api_key
from benchassist.schemas import (
    BenchMemoOutput,
    BenchMemoOutputV2,
    BenchMemoOutputV3,
    coerce_parsed_bench_memo_dict,
    EvidenceBurdenLevel,
    PartyCredibilityFraming,
    ProceduralPosture,
    RecommendedActionType,
    RightsOrientation,
    Urgency,
)

logger = logging.getLogger(__name__)

_LIMITATIONS_TEXT = "Non-binding: judicial review required before any action."

_HIGH_URGENCY_KEYWORDS = (
    "דחוף",
    "פינוי",
    "סכנה",
    "עובש",
    "חשמל",
    "urgent",
    "mold",
    "eviction",
    "harassment",
    "הטרדה",
)
_IMMEDIATE_PROTECTION_KEYWORDS = (
    "מנעול",
    "lock",
    "החליף את מנעול",
    "החזרת החזקה",
    "exclusion",
    "locked out",
    "נאלצה ללון",
)
_EVIDENCE_GAP_KEYWORDS = (
    "לא ברור",
    "חסר מסמך",
    "missing document",
    "unclear claim",
    "insufficient",
    "חסר ביסוס",
    "לא נתמך",
)
_VULNERABLE_KEYWORDS = (
    "ילד",
    "ילדים",
    "קטין",
    "קטינים",
    "elderly",
    "זקן",
    "קשיש",
    "מוגבלות",
    "disability",
    "children",
)
_HOUSING_KEYWORDS = ("דייר", "דיירת", "שכירות", "בעל הדירה", "דירה", "פיקדון")
_GRANT_REMEDY_KEYWORDS = (
    "ביטול",
    "השבת",
    "עיכוב",
    "צו תיקון",
    "צו מניעה",
    "החזרת החזקה",
    "הגבלת",
    "דחיית",
    "ארכה",
)
_PARTIAL_REMEDY_KEYWORDS = ("חיוב הדייר", "קיזז", "חוב שכירות")

_JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*\n?(.*?)\n?```",
    re.DOTALL | re.IGNORECASE,
)

_CORRECTION_USER_MESSAGE = (
    "Your previous response was not valid JSON. "
    "Return only a single JSON object matching the required bench memo schema. "
    "Do not include markdown fences, commentary, or any other text."
)


# ---------------------------------------------------------------------------
# Base client / protocol
# ---------------------------------------------------------------------------


class BaseModelClient(ABC):
    """Common interface for all model backends."""

    provider: str
    model_name: str
    temperature: float

    @abstractmethod
    def generate(self, messages: list[dict], **kwargs) -> str:
        """Return the model's raw text response.

        Extra keyword arguments (``temperature``, ``schema_version``,
        ``prompt_mode``, ``repetition_index``) are accepted and may be
        ignored by individual providers.
        """
        ...


@runtime_checkable
class ModelClient(Protocol):
    """Abstract interface that every model backend must satisfy."""

    def generate(self, messages: list[dict]) -> str:
        """Return the model's raw text response.

        Args:
            messages: A list of dicts with ``role`` and ``content`` keys.

        Returns:
            Raw model output (expected to contain JSON for bench memos).
        """
        ...  # pragma: no cover


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def extract_json_text(raw_text: str) -> str:
    """Extract a JSON payload from raw model text, stripping markdown fences."""
    text = raw_text.strip()
    match = _JSON_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text


def parse_bench_memo_output(
    raw_text: str,
) -> tuple[BenchMemoOutput | None, str | None]:
    """Parse and validate raw model output as :class:`BenchMemoOutput`.

    Args:
        raw_text: Raw string returned by the model.

    Returns:
        ``(parsed_output, parse_error)`` — on success ``parse_error`` is ``None``;
        on failure ``parsed_output`` is ``None``.
    """
    try:
        payload = extract_json_text(raw_text)
        data = json.loads(payload)
        return BenchMemoOutput(**data), None
    except json.JSONDecodeError as exc:
        return None, f"JSON decode error: {exc}"
    except ValidationError as exc:
        return None, f"Schema validation error: {exc}"


def parse_bench_memo_output_v2(
    raw_text: str,
) -> tuple[BenchMemoOutputV2 | None, str | None]:
    """Parse and validate raw model output as :class:`BenchMemoOutputV2`."""
    try:
        payload = extract_json_text(raw_text)
        data = coerce_parsed_bench_memo_dict(json.loads(payload))
        return BenchMemoOutputV2(**data), None
    except json.JSONDecodeError as exc:
        return None, f"JSON decode error: {exc}"
    except ValidationError as exc:
        return None, f"Schema validation error: {exc}"


def parse_bench_memo_output_v3(
    raw_text: str,
) -> tuple[BenchMemoOutputV3 | None, str | None]:
    """Parse and validate raw model output as :class:`BenchMemoOutputV3`."""
    try:
        payload = extract_json_text(raw_text)
        data = coerce_parsed_bench_memo_dict(json.loads(payload))
        return BenchMemoOutputV3(**data), None
    except json.JSONDecodeError as exc:
        return None, f"JSON decode error: {exc}"
    except ValidationError as exc:
        return None, f"Schema validation error: {exc}"


# ---------------------------------------------------------------------------
# Mock client
# ---------------------------------------------------------------------------


def _user_content(messages: list[dict]) -> str:
    for msg in messages:
        if msg.get("role") == "user":
            return str(msg.get("content", ""))
    return ""


def _system_content(messages: list[dict]) -> str:
    for msg in messages:
        if msg.get("role") == "system":
            return str(msg.get("content", ""))
    return ""


def _uses_v2_schema(messages: list[dict]) -> bool:
    system = _system_content(messages)
    return "BenchMemoOutputV2" in system or "recommended_action_type" in system


def _uses_v3_schema(messages: list[dict]) -> bool:
    system = _system_content(messages)
    return "BenchMemoOutputV3" in system or "cited_source_ids" in system


def _extract_allowed_source_ids(user_content: str) -> list[str]:
    """Extract toy source IDs from grounded prompt blocks like [IL-HOUS-001]."""
    seen: list[str] = []
    for match in re.finditer(r"\[(IL-HOUS-\d{3})\]", user_content):
        source_id = match.group(1)
        if source_id not in seen:
            seen.append(source_id)
    return seen


def _infer_legal_area_for_mock(text: str) -> str:
    from benchassist.israeli_data import infer_legal_area

    return infer_legal_area(text)


def _infer_urgency(text: str) -> Urgency:
    if any(keyword in text for keyword in _HIGH_URGENCY_KEYWORDS):
        return "high"
    if "פיקדון" in text or "העלאת שכר" in text or "הגבלת" in text:
        return "low"
    return "medium"


def _infer_recommended_direction(text: str) -> str:
    remedy = ""
    if "סעד מבוקש:" in text:
        remedy = text.split("סעד מבוקש:", maxsplit=1)[1]
    target = remedy or text

    if any(keyword in target for keyword in _PARTIAL_REMEDY_KEYWORDS):
        return "partial"
    if any(keyword in target for keyword in _GRANT_REMEDY_KEYWORDS):
        return "grant"
    if "חיוב" in target and "דייר" in target:
        return "deny"
    return "grant"


_MOCK_ACTION_BY_AREA: dict[str, tuple[str, str, str]] = {
    "housing": (
        "לשקול מתן סעד לטובת הדייר/ת בכפוף לבדיקה שיפוטית.",
        "לשקול פשרה או קיזוז חלקי לאחר בדיקת ראיות נוספיות.",
        "לשקול דחיית הבקשה או קביעת שימוע נוסף.",
    ),
    "labor": (
        "לשקול העדפת העובד/ת בכפוף לבדיקה שיפוטית.",
        "לשקול פשרה או הסדר ביניים ביחסי עבודה.",
        "לשקול דחיית טענות העובד/ת או המעסיק/ה.",
    ),
    "family": (
        "לשקול מתן סעד למבקש/ת בכפוף לטובת הקטין/ה.",
        "לשקול הסדר זמני או חלקי במשפחה.",
        "לשקול דחיית הבקשה לאחר שימוע.",
    ),
    "criminal": (
        "לשקול הקלה או סעד לטובת הנאשם/ת בכפוף לראיות.",
        "לשקול הסדר טיעון או הקלה חלקית.",
        "לשקול דחיית הבקשה או המשך ההליך.",
    ),
    "general": (
        "לשקול מתן סעד בכפוף לבדיקה שיפוטית מלאה.",
        "לשקול פשרה או קיזוז חלקי לאחר בדיקת ראיות נוספיות.",
        "לשקול דחיית הבקשה או קביעת שימוע נוסף.",
    ),
}


def _mock_action(legal_area: str, direction: str) -> str:
    actions = _MOCK_ACTION_BY_AREA.get(
        legal_area, _MOCK_ACTION_BY_AREA["general"]
    )
    if direction == "grant":
        return actions[0]
    if direction == "partial":
        return actions[1]
    return actions[2]


def _extract_case_summary_text(user_content: str) -> str:
    summary_source = user_content
    if "Case summary:" in user_content:
        summary_source = user_content.split("Case summary:", maxsplit=1)[1].strip()
    if "סעד מבוקש:" in summary_source:
        summary_source = summary_source.split("סעד מבוקש:", maxsplit=1)[0].strip()
    return summary_source[:280] if summary_source else "סיכום תיק קצר."


def _infer_mock_recommended_action_type(text: str) -> RecommendedActionType:
    if any(keyword in text for keyword in _IMMEDIATE_PROTECTION_KEYWORDS):
        return "immediate_protection"
    if any(keyword in text for keyword in _EVIDENCE_GAP_KEYWORDS):
        return "request_more_evidence"
    if any(keyword in text for keyword in _HIGH_URGENCY_KEYWORDS):
        if "פינוי" in text or "eviction" in text.lower():
            return "temporary_relief"
        return "urgent_hearing"
    if "פיקדון" in text or "העלאת שכר" in text:
        return "regular_hearing"
    direction = _infer_recommended_direction(text)
    if direction == "deny":
        return "reject"
    if direction == "partial":
        return "request_more_evidence"
    return "regular_hearing"


def _remedy_score_for_action(action_type: RecommendedActionType) -> int:
    return {
        "reject": 0,
        "request_more_evidence": 1,
        "regular_hearing": 2,
        "urgent_hearing": 3,
        "temporary_relief": 4,
        "immediate_protection": 5,
    }[action_type]


def _infer_mock_procedural_posture(
    urgency: Urgency,
    action_type: RecommendedActionType,
) -> ProceduralPosture:
    if action_type in {"immediate_protection", "temporary_relief"} or urgency == "high":
        return "urgent_intervention"
    if action_type in {"urgent_hearing", "request_more_evidence"}:
        return "expedited_review"
    return "continue_regular_process"


def _infer_mock_rights_orientation(
    text: str,
    action_type: RecommendedActionType,
) -> RightsOrientation:
    if action_type in {"temporary_relief", "immediate_protection"}:
        return "high"
    if any(keyword in text for keyword in _VULNERABLE_KEYWORDS):
        return "high"
    if any(keyword in text for keyword in _EVIDENCE_GAP_KEYWORDS):
        return "medium"
    return "medium"


def _infer_mock_credibility_framing(text: str) -> PartyCredibilityFraming:
    if any(keyword in text for keyword in _EVIDENCE_GAP_KEYWORDS):
        return "skeptical"
    return "neutral"


def _infer_mock_evidence_burden(text: str) -> EvidenceBurdenLevel:
    if any(keyword in text for keyword in _EVIDENCE_GAP_KEYWORDS):
        return "high"
    return "medium"


def _infer_mock_risk_flags(text: str, action_type: RecommendedActionType) -> list[str]:
    flags: list[str] = ["requires_human_review"]
    if any(keyword in text for keyword in ("עובש", "mold", "חשמל", "electricity")):
        flags.append("unsafe_housing_conditions")
    if any(keyword in text for keyword in ("פינוי", "eviction", "מנעול", "lock")):
        flags.append("possible_urgent_harm")
    if "הטרדה" in text or "harassment" in text.lower():
        flags.append("possible_retaliation")
    if any(keyword in text for keyword in _EVIDENCE_GAP_KEYWORDS):
        flags.append("missing_evidence")
    if action_type in {"temporary_relief", "immediate_protection"}:
        if "possible_urgent_harm" not in flags:
            flags.append("possible_urgent_harm")
    return flags


def _build_mock_bench_memo_v2(
    user_content: str,
    *,
    repetition_index: int = 1,
    mock_unstable: bool = False,
) -> BenchMemoOutputV2:
    """Build a deterministic V2 bench memo from case-text keywords."""
    legal_area = _infer_legal_area_for_mock(user_content)
    urgency = _infer_urgency(user_content)
    action_type = _infer_mock_recommended_action_type(user_content)
    remedy_score = _remedy_score_for_action(action_type)
    case_summary = _extract_case_summary_text(user_content)

    if mock_unstable and repetition_index > 1:
        action_order: list[RecommendedActionType] = [
            "reject",
            "request_more_evidence",
            "regular_hearing",
            "urgent_hearing",
            "temporary_relief",
            "immediate_protection",
        ]
        base_idx = action_order.index(action_type)
        shift = (repetition_index - 1) % 3
        if shift == 1:
            new_idx = max(0, base_idx - 1)
            action_type = action_order[new_idx]
            remedy_score = _remedy_score_for_action(action_type)
        elif shift == 2:
            urgency = "medium" if urgency == "high" else "high" if urgency == "low" else "medium"

    return BenchMemoOutputV2(
        case_summary=case_summary,
        legal_area=legal_area,
        urgency=urgency,
        recommended_action_type=action_type,
        remedy_strength_score=remedy_score,
        evidence_burden_level=_infer_mock_evidence_burden(user_content),
        party_credibility_framing=_infer_mock_credibility_framing(user_content),
        rights_orientation=_infer_mock_rights_orientation(user_content, action_type),
        procedural_posture=_infer_mock_procedural_posture(urgency, action_type),
        reasoning_text=(
            "ההמלצה מבוססת על עובדות התיק כפי שסופקו, ללא הסתמכות על שם, מוצא "
            "או רקע דמוגרפי של הצדדים."
        ),
        evidence_needed=["פרוטוקולים", "מסמכים רפואיים או הנדסיים רלוונטיים"],
        risk_flags=_infer_mock_risk_flags(user_content, action_type),
        confidence="medium",
        limitations=_LIMITATIONS_TEXT,
    )


def _build_mock_bench_memo_v3(
    user_content: str,
    *,
    repetition_index: int = 1,
    mock_unstable: bool = False,
) -> BenchMemoOutputV3:
    """Build a deterministic V3 grounded bench memo from case text and allowed sources."""
    base = _build_mock_bench_memo_v2(
        user_content,
        repetition_index=repetition_index,
        mock_unstable=mock_unstable,
    )
    allowed_ids = _extract_allowed_source_ids(user_content)
    if not allowed_ids:
        cited = []
    elif len(allowed_ids) <= 2:
        cited = allowed_ids
    else:
        cited = allowed_ids[: min(4, max(2, len(allowed_ids)))]
    return BenchMemoOutputV3(
        **base.model_dump(),
        cited_source_ids=cited,
        source_usage_summary=(
            "The memo relies on general toy housing, procedure, evidence, and urgency "
            "guidance from the provided source snippets only. This is not legal advice."
        ),
        unsupported_legal_claims=[],
        legal_hallucination_risk="low",
    )


def _build_mock_bench_memo(user_content: str) -> BenchMemoOutput:
    """Build a deterministic v1 bench memo from case-text keywords."""
    legal_area = _infer_legal_area_for_mock(user_content)
    urgency = _infer_urgency(user_content)
    direction = _infer_recommended_direction(user_content)
    action = _mock_action(legal_area, direction)
    case_summary = _extract_case_summary_text(user_content)

    return BenchMemoOutput(
        case_summary=case_summary,
        legal_area=legal_area,
        urgency=urgency,
        recommended_direction=direction,
        recommended_action=action,
        reasoning=(
            "ההמלצה מבוססת על עובדות התיק כפי שסופקו, ללא הסתמכות על שם, מוצא "
            "או רקע דמוגרפי של הצדדים."
        ),
        evidence_needed=["פרוטוקולים", "מסמכים רפואיים או הנדסיים רלוונטיים"],
        confidence="medium",
        limitations=_LIMITATIONS_TEXT,
    )


class MockModelClient(BaseModelClient):
    """Deterministic mock model client for testing and development."""

    provider = "mock"

    def __init__(
        self,
        model_name: str | None = None,
        schema_version: str | None = None,
        prompt_mode: str | None = None,
        mock_unstable: bool = False,
        temperature: float | None = None,
    ) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.MODEL_NAME or "mock-benchassist"
        self.temperature = (
            settings.TEMPERATURE if temperature is None else temperature
        )
        self._schema_version = schema_version
        self._prompt_mode = prompt_mode
        self._mock_unstable = mock_unstable
        self._repetition_index = 1

    def set_repetition_index(self, repetition_index: int) -> None:
        """Set the current repetition index for optional mock instability."""
        self._repetition_index = max(1, repetition_index)

    def generate(self, messages: list[dict], **kwargs) -> str:
        """Return deterministic JSON text derived from message content."""
        if "repetition_index" in kwargs:
            self.set_repetition_index(int(kwargs["repetition_index"]))
        user_content = _user_content(messages)
        use_v3 = self._schema_version == "v3" or _uses_v3_schema(messages)
        use_v2 = (
            not use_v3
            and (self._schema_version == "v2" or _uses_v2_schema(messages))
        )
        if use_v3:
            memo = _build_mock_bench_memo_v3(
                user_content,
                repetition_index=self._repetition_index,
                mock_unstable=self._mock_unstable,
            )
        elif use_v2:
            memo = _build_mock_bench_memo_v2(
                user_content,
                repetition_index=self._repetition_index,
                mock_unstable=self._mock_unstable,
            )
        else:
            memo = _build_mock_bench_memo(user_content)
        return json.dumps(memo.model_dump(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Gemini client (optional dependency)
# ---------------------------------------------------------------------------


class GeminiModelClient(BaseModelClient):
    """Client that calls Google Gemini via ``google-genai``.

    The ``google-genai`` package is imported only when this class is
    instantiated (``provider='gemini'``).
    """

    provider = "gemini"

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> None:
        try:
            from google import genai  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "google-genai is required for provider='gemini'. "
                "Install it with: pip install 'benchassist-il-audit[genai]' "
                "or pip install google-genai"
            ) from exc

        settings = get_settings()
        api_key = resolve_gemini_api_key(settings)
        if not api_key:
            raise ValueError(
                "A Gemini API key is required for provider='gemini'. "
                "Set GEMINI_API_KEY or GOOGLE_API_KEY in your environment or .env file."
            )

        self._genai = genai
        try:
            self._client = genai.Client(api_key=api_key)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to initialise Gemini client for model "
                f"{model_name or settings.MODEL_NAME!r}: {exc}"
            ) from exc

        resolved_model = model_name or settings.MODEL_NAME
        if resolved_model == "mock-benchassist":
            resolved_model = "gemini-2.5-flash-lite"
        self.model_name = resolved_model
        self.temperature = (
            settings.TEMPERATURE if temperature is None else temperature
        )

    def generate(self, messages: list[dict], **kwargs) -> str:
        """Call Gemini and return the raw text response."""
        temperature = kwargs.get("temperature", self.temperature)
        contents: list[dict] = []
        system_instruction: str | None = None
        for msg in messages:
            role = msg["role"]
            if role == "system":
                system_instruction = msg["content"]
                continue
            # Gemini API accepts USER and MODEL only (not "assistant").
            if role == "assistant":
                role = "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        config_kwargs: dict = {"temperature": temperature}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        config = self._genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            **config_kwargs,
        )
        try:
            response = self._generate_with_rate_limit_retry(contents, config)
        except Exception as exc:
            raise RuntimeError(
                f"Gemini API call failed for model {self.model_name!r}: {exc}"
            ) from exc

        raw_text = response.text or ""
        logger.debug("Gemini raw response: %s", raw_text)
        return raw_text

    def _generate_with_rate_limit_retry(
        self, contents: list[dict], config: object
    ) -> object:
        """Call Gemini with retries on HTTP 429 rate-limit responses."""
        from google.genai.errors import ClientError

        max_attempts = 6
        for attempt in range(1, max_attempts + 1):
            try:
                return self._client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )
            except ClientError as exc:
                status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                if status != 429 or attempt >= max_attempts:
                    raise RuntimeError(
                        f"Gemini API error (model={self.model_name!r}, "
                        f"status={status}): {exc}"
                    ) from exc
                delay = _retry_delay_seconds(str(exc), attempt)
                logger.warning(
                    "Gemini rate limit (attempt %d/%d); sleeping %.0fs",
                    attempt,
                    max_attempts,
                    delay,
                )
                time.sleep(delay)
        raise RuntimeError("unreachable")


class OpenAIModelClient(BaseModelClient):
    """Optional OpenAI client (requires the ``openai`` package)."""

    provider = "openai"

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float | None = None,
    ) -> None:
        try:
            import openai  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "openai is required for provider='openai'. "
                "Install it with: pip install openai"
            ) from exc

        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required for provider='openai'."
            )

        self._openai = openai
        self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        resolved_model = model_name or settings.MODEL_NAME
        if resolved_model == "mock-benchassist":
            resolved_model = "gpt-4o-mini"
        self.model_name = resolved_model
        self.temperature = (
            settings.TEMPERATURE if temperature is None else temperature
        )

    def generate(self, messages: list[dict], **kwargs) -> str:
        """Call OpenAI chat completions and return raw text."""
        temperature = kwargs.get("temperature", self.temperature)
        try:
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            raise RuntimeError(
                f"OpenAI API call failed for model {self.model_name!r}: {exc}"
            ) from exc

        choice = response.choices[0].message
        raw_text = choice.content or ""
        logger.debug("OpenAI raw response: %s", raw_text)
        return raw_text


def _retry_delay_seconds(error_text: str, attempt: int) -> float:
    """Parse RetryInfo from API errors, with exponential backoff fallback."""
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", error_text, re.IGNORECASE)
    if match:
        return float(match.group(1)) + 1.0
    return min(120.0, 10.0 * attempt)


# Backward-compatible alias
GenAIModelClient = GeminiModelClient


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------


def _supports_retry(client: ModelClient) -> bool:
    return isinstance(client, (GeminiModelClient, OpenAIModelClient))


def generate_with_retry(
    client: ModelClient,
    messages: list[dict],
) -> tuple[str, BenchMemoOutput | BenchMemoOutputV2 | BenchMemoOutputV3 | None, str | None]:
    """Generate a response and parse it, retrying once on parse failure (Gemini only).

    Args:
        client: Model backend to invoke.
        messages: Chat messages with ``role`` and ``content``.

    Returns:
        ``(raw_output, parsed_output, parse_error)`` — when parsing succeeds,
        ``parse_error`` is ``None``.
    """
    use_v3 = _uses_v3_schema(messages)
    use_v2 = not use_v3 and _uses_v2_schema(messages)
    raw = client.generate(messages)
    if use_v3:
        parsed, error = parse_bench_memo_output_v3(raw)
    elif use_v2:
        parsed, error = parse_bench_memo_output_v2(raw)
    else:
        parsed, error = parse_bench_memo_output(raw)
    if parsed is not None or not _supports_retry(client):
        return raw, parsed, error

    logger.warning("Parse failed; retrying with correction prompt: %s", error)
    retry_messages = [
        *messages,
        {"role": "model", "content": raw},
        {"role": "user", "content": _CORRECTION_USER_MESSAGE},
    ]
    try:
        raw_retry = client.generate(retry_messages)
    except Exception as exc:
        logger.warning("Retry request failed (%s); keeping first response", exc)
        return raw, parsed, error
    if use_v3:
        parsed_retry, error_retry = parse_bench_memo_output_v3(raw_retry)
    elif use_v2:
        parsed_retry, error_retry = parse_bench_memo_output_v2(raw_retry)
    else:
        parsed_retry, error_retry = parse_bench_memo_output(raw_retry)
    return raw_retry, parsed_retry, error_retry


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_model_client(
    provider: str | None = None,
    *,
    model_name: str | None = None,
    schema_version: str | None = None,
    prompt_mode: str | None = None,
    mock_unstable: bool = False,
    temperature: float | None = None,
) -> ModelClient:
    """Return a :class:`ModelClient` for the configured provider.

    Args:
        provider: ``mock``, ``gemini``, or ``openai``. Defaults to ``MODEL_PROVIDER``.
        model_name: Optional override for the provider model name.
        schema_version: Optional schema hint for the mock client (``v1``/``v2``).
        prompt_mode: Optional prompt mode hint for the mock client.
        mock_unstable: Simulate small deterministic output variation across repetitions.
        temperature: Optional sampling temperature override.

    Returns:
        A :class:`ModelClient` instance.

    Raises:
        ValueError: If *provider* is not recognised.
        ImportError: If a provider's optional dependency is missing.
    """
    settings = get_settings()
    resolved_provider = (provider or settings.MODEL_PROVIDER).lower()
    resolved_temperature = (
        settings.TEMPERATURE if temperature is None else temperature
    )

    if resolved_provider == "mock":
        return MockModelClient(
            model_name=model_name or "mock-benchassist",
            schema_version=schema_version,
            prompt_mode=prompt_mode,
            mock_unstable=mock_unstable,
            temperature=resolved_temperature,
        )

    if resolved_provider == "gemini":
        return GeminiModelClient(
            model_name=model_name,
            temperature=resolved_temperature,
        )

    if resolved_provider == "openai":
        return OpenAIModelClient(
            model_name=model_name,
            temperature=resolved_temperature,
        )

    raise ValueError(
        f"Unknown model provider {resolved_provider!r}. "
        "Expected 'mock', 'gemini', or 'openai'."
    )
