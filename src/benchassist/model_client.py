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
import re
from typing import Protocol, runtime_checkable

from pydantic import ValidationError

from benchassist.config import get_settings
from benchassist.schemas import BenchMemoOutput, Confidence, Urgency

logger = logging.getLogger(__name__)

_LIMITATIONS_TEXT = "Non-binding: judicial review required before any action."

_HIGH_URGENCY_KEYWORDS = ("דחוף", "פינוי", "סכנה", "עובש", "חשמל")
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
# Protocol
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Mock client
# ---------------------------------------------------------------------------


def _user_content(messages: list[dict]) -> str:
    for msg in messages:
        if msg.get("role") == "user":
            return str(msg.get("content", ""))
    return ""


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


def _build_mock_bench_memo(user_content: str) -> BenchMemoOutput:
    """Build a deterministic bench memo from case-text keywords."""
    legal_area = _infer_legal_area_for_mock(user_content)
    urgency = _infer_urgency(user_content)
    direction = _infer_recommended_direction(user_content)

    action = _mock_action(legal_area, direction)

    summary_source = user_content
    if "Case summary:" in user_content:
        summary_source = user_content.split("Case summary:", maxsplit=1)[1].strip()
    if "סעד מבוקש:" in summary_source:
        summary_source = summary_source.split("סעד מבוקש:", maxsplit=1)[0].strip()
    case_summary = summary_source[:280] if summary_source else "סיכום תיק קצר."

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


class MockModelClient:
    """Deterministic mock model client for testing and development."""

    def generate(self, messages: list[dict]) -> str:
        """Return deterministic JSON text derived from message content."""
        memo = _build_mock_bench_memo(_user_content(messages))
        return json.dumps(memo.model_dump(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Gemini client (optional dependency)
# ---------------------------------------------------------------------------


class GeminiModelClient:
    """Client that calls Google Gemini via ``google-genai``.

    The ``google-genai`` package is imported only when this class is
    instantiated (``provider='gemini'``).
    """

    def __init__(self, model_name: str | None = None) -> None:
        try:
            from google import genai  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "google-genai is required for GeminiModelClient. "
                "Install it with: pip install google-genai"
            ) from exc

        settings = get_settings()
        if not settings.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required for provider='gemini'."
            )

        self._genai = genai
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model_name = model_name or settings.MODEL_NAME
        self._temperature = settings.TEMPERATURE

    def generate(self, messages: list[dict]) -> str:
        """Call Gemini and return the raw text response."""
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

        config_kwargs: dict = {"temperature": self._temperature}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        config = self._genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            **config_kwargs,
        )
        response = self._generate_with_rate_limit_retry(contents, config)

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
                    model=self._model_name,
                    contents=contents,
                    config=config,
                )
            except ClientError as exc:
                status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                if status != 429 or attempt >= max_attempts:
                    raise
                delay = _retry_delay_seconds(str(exc), attempt)
                logger.warning(
                    "Gemini rate limit (attempt %d/%d); sleeping %.0fs",
                    attempt,
                    max_attempts,
                    delay,
                )
                time.sleep(delay)
        raise RuntimeError("unreachable")


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
    return isinstance(client, GeminiModelClient)


def generate_with_retry(
    client: ModelClient,
    messages: list[dict],
) -> tuple[str, BenchMemoOutput | None, str | None]:
    """Generate a response and parse it, retrying once on parse failure (Gemini only).

    Args:
        client: Model backend to invoke.
        messages: Chat messages with ``role`` and ``content``.

    Returns:
        ``(raw_output, parsed_output, parse_error)`` — when parsing succeeds,
        ``parse_error`` is ``None``.
    """
    raw = client.generate(messages)
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
    parsed_retry, error_retry = parse_bench_memo_output(raw_retry)
    return raw_retry, parsed_retry, error_retry


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_model_client(
    provider: str | None = None,
    *,
    model_name: str | None = None,
) -> ModelClient:
    """Return a :class:`ModelClient` for the configured provider.

    Args:
        provider: ``mock`` or ``gemini``. Defaults to ``MODEL_PROVIDER`` env.
        model_name: Optional override for the provider model name.

    Returns:
        A :class:`ModelClient` instance.

    Raises:
        ValueError: If *provider* is not recognised.
    """
    settings = get_settings()
    resolved_provider = (provider or settings.MODEL_PROVIDER).lower()

    if resolved_provider == "mock":
        return MockModelClient()

    if resolved_provider == "gemini":
        return GeminiModelClient(model_name=model_name)

    raise ValueError(
        f"Unknown model provider {resolved_provider!r}. Expected 'mock' or 'gemini'."
    )
