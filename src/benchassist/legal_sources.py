"""Local toy legal knowledge base and deterministic retrieval (no embeddings/APIs)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from benchassist.config import get_settings
from benchassist.schemas import LegalSource, RetrievedSource

_TOKEN_RE = re.compile(r"[\w\u0590-\u05FF\u0600-\u06FF]+", re.UNICODE)

_TAG_BOOST_KEYWORDS: dict[str, tuple[str, ...]] = {
    "mold": ("mold", "עובש", "עובש"),
    "eviction": ("eviction", "פינוי", "lockout", "נעילה"),
    "repair": ("repair", "תיקון", "maintenance", "habitability"),
    "electricity": ("electricity", "חשמל", "power", "חשמל"),
    "urgent": ("urgent", "דחוף", "immediate", "דחיפות"),
    "temporary_relief": ("temporary relief", "סעד זמני", "interim"),
    "evidence": ("evidence", "ראיות", "תיעוד", "documentation", "photos"),
    "harassment": ("harassment", "הטרדה", "threat"),
    "retaliation": ("retaliation", "התנכלות"),
    "language_access": ("language", "שפה", "ערבית", "arabic", "access to justice"),
}


def default_knowledge_path() -> Path:
    settings = get_settings()
    multi = settings.DATA_DIR / "knowledge" / "israeli_multidomain_knowledge.jsonl"
    if multi.exists():
        return multi
    return settings.DATA_DIR / "knowledge" / "israeli_housing_knowledge.jsonl"


def load_legal_sources(path: str | Path | None = None) -> list[LegalSource]:
    """Load toy legal sources from a JSONL file."""
    source_path = Path(path) if path is not None else default_knowledge_path()
    if not source_path.exists():
        return []
    sources: list[LegalSource] = []
    for line in source_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        sources.append(LegalSource(**json.loads(line)))
    return sources


def tokenize(text: str) -> set[str]:
    """Tokenize text for overlap scoring (Hebrew/English/Arabic word chars)."""
    return {t.lower() for t in _TOKEN_RE.findall(text) if len(t) >= 2}


def _tag_boost(query_tokens: set[str], tags: list[str]) -> float:
    tag_text = " ".join(tags).lower()
    boost = 0.0
    for _, keywords in _TAG_BOOST_KEYWORDS.items():
        if any(kw in query_tokens or kw in tag_text for kw in keywords):
            if any(kw in tag_text for kw in keywords):
                boost += 1.5
    return boost


def score_source(query_tokens: set[str], source: LegalSource) -> float:
    """Score a source by token overlap with query, title, text, and tags."""
    title_tokens = tokenize(source.title)
    text_tokens = tokenize(source.text)
    tag_tokens = tokenize(" ".join(source.tags))
    overlap = len(query_tokens & (title_tokens | text_tokens | tag_tokens))
    if not query_tokens:
        return 0.0
    base = overlap / max(len(query_tokens), 1)
    return base + _tag_boost(query_tokens, source.tags)


def retrieve_sources(
    query: str,
    sources: list[LegalSource],
    top_k: int = 5,
) -> list[RetrievedSource]:
    """Return top-k sources by deterministic keyword overlap."""
    if not sources or top_k <= 0:
        return []
    query_tokens = tokenize(query)
    scored: list[tuple[float, LegalSource]] = []
    for source in sources:
        score = score_source(query_tokens, source)
        scored.append((score, source))
    scored.sort(key=lambda item: (-item[0], item[1].source_id))
    top = scored[:top_k]
    max_score = top[0][0] if top else 1.0
    if max_score <= 0:
        max_score = 1.0
    return [
        RetrievedSource(
            source_id=source.source_id,
            title=source.title,
            relevance_score=round(score / max_score, 4),
            text=source.text,
        )
        for score, source in top
    ]


def format_sources_for_prompt(sources: list[LegalSource]) -> str:
    """Format allowed sources for inclusion in a grounded user prompt."""
    blocks: list[str] = []
    for source in sources:
        blocks.append(
            f"[{source.source_id}] {source.title}\n"
            f"{source.text}\n"
            f"Caution: {source.caution}"
        )
    return "\n\n".join(blocks)


def allowed_source_ids(sources: list[LegalSource]) -> set[str]:
    return {s.source_id for s in sources}
