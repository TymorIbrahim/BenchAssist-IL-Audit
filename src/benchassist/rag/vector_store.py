"""ChromaDB vector store with hybrid search for Israeli legal documents.

Wraps ChromaDB persistent storage with Gemini embeddings and provides
both vector similarity search and BM25 keyword search, plus a hybrid
mode that merges and re-ranks results from both methods.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from benchassist.rag.schemas import LegalChunk, RetrievedChunk

logger = logging.getLogger(__name__)

# Load environment for API key
load_dotenv()

_EMBEDDING_MODEL = "gemini-embedding-001"
_EMBED_BATCH_SIZE = 50


# ---------------------------------------------------------------------------
# Gemini embedding helper
# ---------------------------------------------------------------------------


def _get_genai_client() -> Any:
    """Create a google.genai Client using GEMINI_API_KEY from environment."""
    try:
        import google.genai as genai
    except ImportError as exc:
        raise ImportError(
            "google-genai is required for the RAG vector store. "
            "Install it with: pip install google-genai"
        ) from exc

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY or GOOGLE_API_KEY environment variable is required "
            "for embedding generation."
        )
    return genai.Client(api_key=api_key)


def _embed_texts(client: Any, texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using Gemini text-embedding-004.

    Args:
        client: A ``google.genai.Client`` instance.
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (list of floats).
    """
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[i : i + _EMBED_BATCH_SIZE]
        try:
            result = client.models.embed_content(
                model=_EMBEDDING_MODEL,
                contents=batch,
            )
            for emb in result.embeddings:
                embeddings.append(list(emb.values))
        except Exception as exc:
            logger.error(
                "Embedding batch %d–%d failed: %s",
                i,
                i + len(batch),
                exc,
            )
            raise
    return embeddings


def _embed_single(client: Any, text: str) -> list[float]:
    """Embed a single text string."""
    result = client.models.embed_content(
        model=_EMBEDDING_MODEL,
        contents=text,
    )
    return list(result.embeddings[0].values)


# ---------------------------------------------------------------------------
# BM25 helper
# ---------------------------------------------------------------------------


def _build_bm25_index(
    chunks: list[LegalChunk],
) -> Any:
    """Build a BM25 index from the chunk texts.

    Returns a ``BM25Okapi`` instance, or ``None`` if rank_bm25 is unavailable.
    """
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        logger.warning(
            "rank_bm25 not installed; BM25 keyword search will be unavailable"
        )
        return None

    if not chunks:
        return None

    tokenized = [chunk.text.lower().split() for chunk in chunks]
    return BM25Okapi(tokenized)


# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------


class LegalVectorStore:
    """ChromaDB-backed vector store with hybrid search for legal documents.

    Uses Gemini ``text-embedding-004`` for embeddings and ``rank_bm25``
    for keyword search.

    Args:
        db_path: Path to the ChromaDB persistent storage directory.
        collection_name: Name of the ChromaDB collection.
    """

    def __init__(
        self,
        db_path: Path,
        collection_name: str = "israeli_law",
    ) -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise ImportError(
                "chromadb is required for the RAG vector store. "
                "Install it with: pip install chromadb"
            ) from exc

        self._db_path = Path(db_path)
        self._db_path.mkdir(parents=True, exist_ok=True)
        self._collection_name = collection_name

        self._client = chromadb.PersistentClient(path=str(self._db_path))
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        self._genai_client = _get_genai_client()

        # BM25 index and cached chunks — rebuilt when documents are added
        self._chunks: list[LegalChunk] = []
        self._bm25_index: Any = None
        self._bm25_dirty = True

        logger.info(
            "LegalVectorStore initialised: db_path=%s, collection=%s, count=%d",
            self._db_path,
            collection_name,
            self._collection.count(),
        )

    # ------------------------------------------------------------------
    # Document management
    # ------------------------------------------------------------------

    def add_documents(self, chunks: list[LegalChunk]) -> int:
        """Embed and add legal chunks to the ChromaDB collection.

        Documents are batched in groups of 50 for embedding. Duplicate
        chunks (by deterministic ID) are skipped.

        Args:
            chunks: List of :class:`LegalChunk` objects to add.

        Returns:
            Number of chunks successfully added.
        """
        if not chunks:
            return 0

        added = 0
        for i in range(0, len(chunks), _EMBED_BATCH_SIZE):
            batch = chunks[i : i + _EMBED_BATCH_SIZE]
            texts = [c.text for c in batch]
            ids = [self._chunk_id(c) for c in batch]
            metadatas = [
                {
                    "document_name": c.document_name,
                    "section_id": c.section_id,
                    "section_title": c.section_title,
                    "language": c.language,
                    "topic_tags": ",".join(c.topic_tags),
                    "parent_section_id": c.parent_section_id or "",
                }
                for c in batch
            ]

            try:
                embeddings = _embed_texts(self._genai_client, texts)
            except Exception as exc:
                logger.error("Failed to embed batch %d: %s", i, exc)
                continue

            try:
                self._collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas,
                )
                added += len(batch)
            except Exception as exc:
                logger.error("Failed to upsert batch %d: %s", i, exc)
                continue

        # Update BM25 index
        self._chunks.extend(chunks)
        self._bm25_dirty = True

        logger.info(
            "Added %d/%d chunks to collection %s",
            added,
            len(chunks),
            self._collection_name,
        )
        return added

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        n_results: int = 5,
        language: str | None = None,
    ) -> list[RetrievedChunk]:
        """Vector similarity search over the legal corpus.

        Args:
            query: Search query string.
            n_results: Maximum number of results to return.
            language: Optional language filter (``'he'`` or ``'en'``).

        Returns:
            List of :class:`RetrievedChunk` objects ranked by similarity.
        """
        try:
            query_embedding = _embed_single(self._genai_client, query)
        except Exception as exc:
            logger.error("Failed to embed query: %s", exc)
            return []

        where_filter: dict[str, Any] | None = None
        if language:
            where_filter = {"language": language}

        try:
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.error("ChromaDB query failed: %s", exc)
            return []

        return self._parse_chroma_results(results, retrieval_method="vector")

    def hybrid_search(
        self,
        query: str,
        n_results: int = 5,
    ) -> list[RetrievedChunk]:
        """Hybrid search combining vector similarity and BM25 keyword search.

        Results from both methods are merged, deduplicated, and re-ranked
        using a combined score (0.7 × vector_score + 0.3 × bm25_score).

        Args:
            query: Search query string.
            n_results: Maximum number of results to return.

        Returns:
            List of :class:`RetrievedChunk` objects ranked by combined score.
        """
        # Vector search (fetch extra candidates for merging)
        vector_results = self.search(query, n_results=n_results * 2)

        # BM25 search
        bm25_results = self._bm25_search(query, n_results=n_results * 2)

        # Merge and re-rank
        return self._merge_results(vector_results, bm25_results, n_results)

    def _bm25_search(
        self,
        query: str,
        n_results: int = 10,
    ) -> list[RetrievedChunk]:
        """Keyword search using BM25 over cached chunks."""
        if self._bm25_dirty:
            self._rebuild_bm25()

        if self._bm25_index is None or not self._chunks:
            return []

        tokenized_query = query.lower().split()
        try:
            scores = self._bm25_index.get_scores(tokenized_query)
        except Exception as exc:
            logger.error("BM25 search failed: %s", exc)
            return []

        # Get top-N indices
        scored_indices = sorted(
            enumerate(scores), key=lambda x: x[1], reverse=True
        )[:n_results]

        results: list[RetrievedChunk] = []
        max_score = max(scores) if max(scores) > 0 else 1.0
        for idx, score in scored_indices:
            if score <= 0:
                continue
            chunk = self._chunks[idx]
            normalized_score = float(score / max_score)
            results.append(
                RetrievedChunk(
                    **chunk.model_dump(),
                    score=normalized_score,
                    retrieval_method="bm25",
                )
            )

        return results

    def _rebuild_bm25(self) -> None:
        """Rebuild the BM25 index from the current chunk cache."""
        if self._chunks:
            self._bm25_index = _build_bm25_index(self._chunks)
        else:
            # Load from ChromaDB
            self._chunks = self._load_all_chunks()
            self._bm25_index = _build_bm25_index(self._chunks)
        self._bm25_dirty = False

    def _load_all_chunks(self) -> list[LegalChunk]:
        """Load all documents from ChromaDB into LegalChunk objects."""
        try:
            count = self._collection.count()
            if count == 0:
                return []
            results = self._collection.get(
                include=["documents", "metadatas"],
            )
        except Exception as exc:
            logger.error("Failed to load chunks from ChromaDB: %s", exc)
            return []

        chunks: list[LegalChunk] = []
        documents = results.get("documents") or []
        metadatas = results.get("metadatas") or []

        for doc, meta in zip(documents, metadatas):
            if doc is None or meta is None:
                continue
            tags_raw = meta.get("topic_tags", "")
            topic_tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            parent = meta.get("parent_section_id", "")

            chunks.append(
                LegalChunk(
                    document_name=meta.get("document_name", "unknown"),
                    section_id=meta.get("section_id", "unknown"),
                    section_title=meta.get("section_title", ""),
                    text=doc,
                    language=meta.get("language", "en"),
                    topic_tags=topic_tags,
                    parent_section_id=parent if parent else None,
                )
            )

        return chunks

    @staticmethod
    def _merge_results(
        vector_results: list[RetrievedChunk],
        bm25_results: list[RetrievedChunk],
        n_results: int,
    ) -> list[RetrievedChunk]:
        """Merge vector and BM25 results with weighted scoring.

        Weighting: 0.7 × vector_score + 0.3 × bm25_score.
        """
        score_map: dict[str, dict[str, Any]] = {}

        for chunk in vector_results:
            key = f"{chunk.document_name}:{chunk.section_id}"
            if key not in score_map:
                score_map[key] = {
                    "chunk": chunk,
                    "vector_score": 0.0,
                    "bm25_score": 0.0,
                }
            # ChromaDB distances are L2/cosine distance; convert to similarity
            score_map[key]["vector_score"] = max(
                score_map[key]["vector_score"],
                chunk.score,
            )

        for chunk in bm25_results:
            key = f"{chunk.document_name}:{chunk.section_id}"
            if key not in score_map:
                score_map[key] = {
                    "chunk": chunk,
                    "vector_score": 0.0,
                    "bm25_score": 0.0,
                }
            score_map[key]["bm25_score"] = max(
                score_map[key]["bm25_score"],
                chunk.score,
            )

        # Compute combined score and re-rank
        ranked: list[tuple[float, RetrievedChunk]] = []
        for entry in score_map.values():
            combined = 0.7 * entry["vector_score"] + 0.3 * entry["bm25_score"]
            chunk = entry["chunk"]
            ranked.append((
                combined,
                RetrievedChunk(
                    document_name=chunk.document_name,
                    section_id=chunk.section_id,
                    section_title=chunk.section_title,
                    text=chunk.text,
                    language=chunk.language,
                    topic_tags=chunk.topic_tags,
                    parent_section_id=chunk.parent_section_id,
                    score=combined,
                    retrieval_method="hybrid",
                ),
            ))

        ranked.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in ranked[:n_results]]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return collection statistics.

        Returns:
            Dict with ``count``, ``languages``, and ``documents`` keys.
        """
        try:
            count = self._collection.count()
            if count == 0:
                return {"count": 0, "languages": [], "documents": []}

            results = self._collection.get(include=["metadatas"])
            metadatas = results.get("metadatas") or []

            languages: set[str] = set()
            documents: set[str] = set()
            for meta in metadatas:
                if meta is None:
                    continue
                lang = meta.get("language")
                if lang:
                    languages.add(lang)
                doc = meta.get("document_name")
                if doc:
                    documents.add(doc)

            return {
                "count": count,
                "languages": sorted(languages),
                "documents": sorted(documents),
            }
        except Exception as exc:
            logger.error("Failed to get collection stats: %s", exc)
            return {"count": 0, "languages": [], "documents": [], "error": str(exc)}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _chunk_id(chunk: LegalChunk) -> str:
        """Generate a deterministic ID for a chunk."""
        raw = f"{chunk.document_name}:{chunk.section_id}:{chunk.text[:200]}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _parse_chroma_results(
        results: dict[str, Any],
        retrieval_method: str = "vector",
    ) -> list[RetrievedChunk]:
        """Parse ChromaDB query results into RetrievedChunk objects."""
        chunks: list[RetrievedChunk] = []

        # ChromaDB returns nested lists (one per query)
        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            if doc is None or meta is None:
                continue

            # Convert cosine distance to similarity score
            similarity = max(0.0, 1.0 - dist)

            tags_raw = meta.get("topic_tags", "")
            topic_tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            parent = meta.get("parent_section_id", "")

            chunks.append(
                RetrievedChunk(
                    document_name=meta.get("document_name", "unknown"),
                    section_id=meta.get("section_id", "unknown"),
                    section_title=meta.get("section_title", ""),
                    text=doc,
                    language=meta.get("language", "en"),
                    topic_tags=topic_tags,
                    parent_section_id=parent if parent else None,
                    score=similarity,
                    retrieval_method=retrieval_method,
                )
            )

        return chunks
