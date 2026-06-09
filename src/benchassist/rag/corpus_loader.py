"""Legal corpus loader and chunking utilities.

Reads Israeli legal documents from a directory tree, splits them into
semantically meaningful chunks based on section headers, and returns
:class:`LegalChunk` objects ready for embedding and storage.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from benchassist.rag.schemas import LegalChunk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Section header patterns
# ---------------------------------------------------------------------------

# English: "Section 21", "Section 21(a)", "SECTION 3.", "Art. 5"
_EN_SECTION_RE = re.compile(
    r"^(?:Section|SECTION|Art\.?|Article)\s+(\d+[A-Za-z]?(?:\([a-z0-9]+\))*)",
    re.MULTILINE,
)

# Hebrew: "סעיף 21", "סעיף 21(א)", "סעיף קטן 3"
_HE_SECTION_RE = re.compile(
    r"^סעיף\s+(?:קטן\s+)?(\d+[א-ת]?(?:\([א-ת0-9]+\))*)",
    re.MULTILINE,
)

# Generic numbered sections: "1.", "1.2", "1.2.3" at the start of a line
_NUMBERED_RE = re.compile(
    r"^(\d+(?:\.\d+)*)\.\s+",
    re.MULTILINE,
)

# Minimum and maximum chunk sizes (characters)
_MIN_CHUNK_SIZE = 100
_MAX_CHUNK_SIZE = 2000


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------


def _detect_language_from_filename(filename: str) -> str | None:
    """Detect language from filename suffix convention.

    Returns ``'he'`` for ``*_he.txt``, ``'en'`` for ``*_en.txt``, or ``None``.
    """
    stem = Path(filename).stem.lower()
    if stem.endswith("_he"):
        return "he"
    if stem.endswith("_en"):
        return "en"
    return None


def _detect_language_from_content(text: str) -> str:
    """Heuristic language detection based on Hebrew character ratio.

    Returns ``'he'`` if more than 20% of alphabetic characters are Hebrew,
    otherwise ``'en'``.
    """
    if not text:
        return "en"
    hebrew_chars = sum(1 for c in text if "\u0590" <= c <= "\u05FF")
    latin_chars = sum(1 for c in text if c.isascii() and c.isalpha())
    total = hebrew_chars + latin_chars
    if total == 0:
        return "en"
    return "he" if hebrew_chars / total > 0.2 else "en"


def detect_language(filename: str, text: str) -> str:
    """Detect document language from filename convention or content analysis.

    Args:
        filename: Document filename (e.g. ``'criminal_procedure_he.txt'``).
        text: Document text content for fallback detection.

    Returns:
        ``'he'`` or ``'en'``.
    """
    lang = _detect_language_from_filename(filename)
    if lang is not None:
        return lang
    return _detect_language_from_content(text)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def _find_section_splits(text: str, language: str) -> list[tuple[int, str, str]]:
    """Find section header positions in the text.

    Returns a list of ``(start_pos, section_id, section_title)`` tuples.
    """
    splits: list[tuple[int, str, str]] = []

    # Choose patterns based on language
    patterns: list[re.Pattern[str]] = []
    if language == "he":
        patterns = [_HE_SECTION_RE, _NUMBERED_RE]
    else:
        patterns = [_EN_SECTION_RE, _NUMBERED_RE]

    for pattern in patterns:
        for match in pattern.finditer(text):
            section_id = match.group(1)
            # Extract the full line as the section title
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            if line_end == -1:
                line_end = len(text)
            section_title = text[line_start:line_end].strip()
            splits.append((match.start(), section_id, section_title))

    # Sort by position and deduplicate overlapping matches
    splits.sort(key=lambda x: x[0])
    deduped: list[tuple[int, str, str]] = []
    for split in splits:
        if deduped and split[0] - deduped[-1][0] < 10:
            # Skip near-duplicate matches (same position from different patterns)
            continue
        deduped.append(split)

    return deduped


def _merge_small_chunks(
    chunks: list[dict[str, str]],
    min_size: int = _MIN_CHUNK_SIZE,
) -> list[dict[str, str]]:
    """Merge chunks smaller than ``min_size`` into their predecessor."""
    if not chunks:
        return chunks

    merged: list[dict[str, str]] = [chunks[0]]
    for chunk in chunks[1:]:
        if len(chunk["text"]) < min_size and merged:
            # Merge into previous chunk
            prev = merged[-1]
            prev["text"] = prev["text"].rstrip() + "\n\n" + chunk["text"]
            prev["section_title"] = prev["section_title"] or chunk["section_title"]
        else:
            merged.append(chunk)

    return merged


def _split_oversized_chunk(text: str, max_size: int = _MAX_CHUNK_SIZE) -> list[str]:
    """Split a chunk exceeding ``max_size`` at paragraph boundaries.

    Falls back to sentence boundaries, then hard character splits.
    """
    if len(text) <= max_size:
        return [text]

    parts: list[str] = []
    remaining = text

    while len(remaining) > max_size:
        # Try paragraph boundary
        split_pos = remaining.rfind("\n\n", 0, max_size)
        if split_pos == -1 or split_pos < max_size // 3:
            # Try sentence boundary
            split_pos = remaining.rfind(". ", 0, max_size)
        if split_pos == -1 or split_pos < max_size // 3:
            # Hard split
            split_pos = max_size

        parts.append(remaining[: split_pos + 1].rstrip())
        remaining = remaining[split_pos + 1 :].lstrip()

    if remaining.strip():
        parts.append(remaining.strip())

    return parts


def chunk_statute(text: str, metadata: dict[str, Any]) -> list[LegalChunk]:
    """Split a legal statute text into semantically meaningful chunks.

    Splits on section headers (``Section NN``, ``סעיף NN``, numbered sections).
    Each chunk retains its section header plus content. Chunks smaller than
    100 characters are merged into their predecessor; chunks larger than 2000
    characters are split at paragraph boundaries.

    Args:
        text: Full text of the legal document.
        metadata: Dict with at minimum ``document_name``; may also include
            ``language``, ``topic_tags``, ``parent_section_id``.

    Returns:
        List of :class:`LegalChunk` objects.
    """
    document_name: str = metadata.get("document_name", "unknown")
    language: str = metadata.get("language", "en")
    topic_tags: list[str] = metadata.get("topic_tags", [])
    parent_section_id: str | None = metadata.get("parent_section_id")

    splits = _find_section_splits(text, language)

    if not splits:
        # No section headers found — treat entire document as one chunk
        logger.debug(
            "No section headers found in %s; creating single chunk",
            document_name,
        )
        return [
            LegalChunk(
                document_name=document_name,
                section_id="full",
                section_title=document_name,
                text=text.strip(),
                language=language,
                topic_tags=topic_tags,
                parent_section_id=parent_section_id,
            )
        ]

    # Build raw chunks from splits
    raw_chunks: list[dict[str, str]] = []

    # Content before first section header
    preamble = text[: splits[0][0]].strip()
    if preamble:
        raw_chunks.append(
            {
                "section_id": "preamble",
                "section_title": "Preamble",
                "text": preamble,
            }
        )

    for i, (start, section_id, section_title) in enumerate(splits):
        end = splits[i + 1][0] if i + 1 < len(splits) else len(text)
        chunk_text = text[start:end].strip()
        raw_chunks.append(
            {
                "section_id": section_id,
                "section_title": section_title,
                "text": chunk_text,
            }
        )

    # Merge small chunks
    raw_chunks = _merge_small_chunks(raw_chunks, _MIN_CHUNK_SIZE)

    # Split oversized chunks and build final LegalChunk objects
    chunks: list[LegalChunk] = []
    for raw in raw_chunks:
        parts = _split_oversized_chunk(raw["text"], _MAX_CHUNK_SIZE)
        for part_idx, part_text in enumerate(parts):
            sid = raw["section_id"]
            if len(parts) > 1:
                sid = f"{sid}_part{part_idx + 1}"
            chunks.append(
                LegalChunk(
                    document_name=document_name,
                    section_id=sid,
                    section_title=raw["section_title"],
                    text=part_text,
                    language=language,
                    topic_tags=topic_tags,
                    parent_section_id=parent_section_id,
                )
            )

    logger.info(
        "Chunked %s into %d chunks (language=%s)",
        document_name,
        len(chunks),
        language,
    )
    return chunks


# ---------------------------------------------------------------------------
# Metadata loading
# ---------------------------------------------------------------------------


def load_metadata(corpus_dir: Path) -> dict[str, Any]:
    """Load corpus metadata from ``metadata.json`` if present.

    Args:
        corpus_dir: Root directory of the legal corpus.

    Returns:
        Metadata dictionary, or empty dict if no metadata file exists.
    """
    meta_path = corpus_dir / "metadata.json"
    if not meta_path.exists():
        logger.debug("No metadata.json found in %s", corpus_dir)
        return {}

    try:
        with meta_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Loaded metadata from %s", meta_path)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load metadata from %s: %s", meta_path, exc)
        return {}


# ---------------------------------------------------------------------------
# Corpus loader
# ---------------------------------------------------------------------------


def load_legal_corpus(corpus_dir: Path) -> list[LegalChunk]:
    """Walk a directory tree and load all legal documents as chunks.

    Reads ``.txt`` files from the corpus directory and its subdirectories,
    detects language, and applies statute chunking to each file.

    Args:
        corpus_dir: Root directory of the legal corpus (e.g. ``legal_corpus/``).

    Returns:
        List of all :class:`LegalChunk` objects across all documents.

    Raises:
        FileNotFoundError: If ``corpus_dir`` does not exist.
    """
    corpus_dir = Path(corpus_dir)
    if not corpus_dir.exists():
        raise FileNotFoundError(f"Corpus directory not found: {corpus_dir}")

    # Load global metadata
    global_metadata = load_metadata(corpus_dir)
    # documents may be a list of dicts with 'filename' keys — convert to dict
    raw_docs = global_metadata.get("documents", {})
    if isinstance(raw_docs, list):
        doc_metadata: dict[str, dict[str, Any]] = {
            d.get("filename", ""): d for d in raw_docs if isinstance(d, dict)
        }
    else:
        doc_metadata = raw_docs

    all_chunks: list[LegalChunk] = []
    txt_files = sorted(corpus_dir.rglob("*.txt"))

    if not txt_files:
        logger.warning("No .txt files found in %s", corpus_dir)
        return all_chunks

    for txt_path in txt_files:
        try:
            text = txt_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to read %s: %s", txt_path, exc)
            continue

        if not text.strip():
            logger.debug("Skipping empty file: %s", txt_path)
            continue

        filename = txt_path.name
        language = detect_language(filename, text)

        # Resolve subdirectory as topic tag
        rel_path = txt_path.relative_to(corpus_dir)
        rel_path_str = str(rel_path)
        subdir = str(rel_path.parent)
        topic_tags = [subdir] if subdir != "." else []

        # Merge with per-document metadata from metadata.json
        # Try relative path first (e.g., "statutes/detention_law.txt"), then basename
        file_meta = doc_metadata.get(rel_path_str, doc_metadata.get(filename, {}))
        metadata: dict[str, Any] = {
            "document_name": filename,
            "language": language,
            "topic_tags": topic_tags + file_meta.get("topic_tags", []),
            "parent_section_id": file_meta.get("parent_section_id"),
        }

        chunks = chunk_statute(text, metadata)
        all_chunks.extend(chunks)

    logger.info(
        "Loaded %d chunks from %d files in %s",
        len(all_chunks),
        len(txt_files),
        corpus_dir,
    )
    return all_chunks
