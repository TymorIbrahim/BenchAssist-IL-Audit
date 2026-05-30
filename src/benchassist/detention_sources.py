"""Source registry for Israeli detention / remand data preparation (pivot layer)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Literal

SourceType = Literal["legal_grounding", "background_statistics", "real_case_inspired"]
AccessMethod = Literal["local_file", "huggingface", "manual_url", "manual_text"]

SOURCE_TYPES: tuple[SourceType, ...] = (
    "legal_grounding",
    "background_statistics",
    "real_case_inspired",
)

ACCESS_METHODS: tuple[AccessMethod, ...] = (
    "local_file",
    "huggingface",
    "manual_url",
    "manual_text",
)


def _parse_bool(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n", ""}:
        return False
    return default


@dataclass(frozen=True)
class DetentionSource:
    """Metadata for a detention/remand-related data source."""

    source_id: str
    title: str
    source_type: SourceType
    jurisdiction: str
    language: str
    url: str | None
    access_method: AccessMethod
    license_or_access_note: str
    recommended_use: str
    not_for: str
    attribution_note: str
    sensitivity_note: str
    full_text_allowed_internal: bool
    public_export_allowed: bool
    requires_manual_review_before_dashboard: bool

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> DetentionSource:
        return cls(
            source_id=str(raw["source_id"]),
            title=str(raw["title"]),
            source_type=str(raw["source_type"]),  # type: ignore[arg-type]
            jurisdiction=str(raw.get("jurisdiction", "Israel")),
            language=str(raw.get("language", "he")),
            url=str(raw["url"]) if raw.get("url") else None,
            access_method=str(raw["access_method"]),  # type: ignore[arg-type]
            license_or_access_note=str(raw.get("license_or_access_note", "")),
            recommended_use=str(raw.get("recommended_use", "")),
            not_for=str(raw.get("not_for", "")),
            attribution_note=str(raw.get("attribution_note", "")),
            sensitivity_note=str(raw.get("sensitivity_note", "")),
            full_text_allowed_internal=_parse_bool(raw.get("full_text_allowed_internal"), default=True),
            public_export_allowed=_parse_bool(raw.get("public_export_allowed"), default=False),
            requires_manual_review_before_dashboard=_parse_bool(
                raw.get("requires_manual_review_before_dashboard"), default=True
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "title": self.title,
            "source_type": self.source_type,
            "jurisdiction": self.jurisdiction,
            "language": self.language,
            "url": self.url,
            "access_method": self.access_method,
            "license_or_access_note": self.license_or_access_note,
            "recommended_use": self.recommended_use,
            "not_for": self.not_for,
            "attribution_note": self.attribution_note,
            "sensitivity_note": self.sensitivity_note,
            "full_text_allowed_internal": self.full_text_allowed_internal,
            "public_export_allowed": self.public_export_allowed,
            "requires_manual_review_before_dashboard": self.requires_manual_review_before_dashboard,
        }


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def default_sources_path() -> Path:
    return _project_root() / "data" / "legal_sources" / "detention_sources.json"


def load_detention_sources(path: Path | None = None) -> list[DetentionSource]:
    """Load detention source registry from JSON."""
    src_path = path or default_sources_path()
    if not src_path.exists():
        raise FileNotFoundError(f"Detention sources registry not found: {src_path}")
    raw = json.loads(src_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Expected JSON array in {src_path}")
    return [DetentionSource.from_dict(item) for item in raw]


def get_source_by_id(source_id: str, *, path: Path | None = None) -> DetentionSource | None:
    for src in load_detention_sources(path):
        if src.source_id == source_id:
            return src
    return None


def iter_sources_by_type(
    source_type: SourceType,
    *,
    path: Path | None = None,
) -> Iterator[DetentionSource]:
    for src in load_detention_sources(path):
        if src.source_type == source_type:
            yield src


def sources_manifest(*, path: Path | None = None) -> dict[str, Any]:
    """Return registry summary for export manifests."""
    sources = load_detention_sources(path)
    by_type: dict[str, int] = {t: 0 for t in SOURCE_TYPES}
    for src in sources:
        by_type[src.source_type] = by_type.get(src.source_type, 0) + 1
    return {
        "registry_path": str(path or default_sources_path()),
        "n_sources": len(sources),
        "by_source_type": by_type,
        "sources": [s.to_dict() for s in sources],
    }
