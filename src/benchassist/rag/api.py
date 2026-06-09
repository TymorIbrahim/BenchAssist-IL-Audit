"""FastAPI service for the Agentic RAG judicial reasoning pipeline.

Exposes endpoints for case assessment, corpus search, and health checks.
On startup, initialises the vector store and judicial agent.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from benchassist.rag.agent import JudicialAgent, set_vector_store
from benchassist.rag.schemas import (
    AssessRequest,
    AssessResponse,
    RetrievedChunk,
)
from benchassist.rag.vector_store import LegalVectorStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_vector_store: LegalVectorStore | None = None
_agent: JudicialAgent | None = None


# ---------------------------------------------------------------------------
# Project root resolution
# ---------------------------------------------------------------------------


def _find_project_root() -> Path:
    """Walk up from this file to locate the project root."""
    current = Path(__file__).resolve().parent
    for ancestor in [current, *list(current.parents)]:
        if (ancestor / "pyproject.toml").exists() or (ancestor / ".git").exists():
            return ancestor
    return Path(__file__).resolve().parent.parent.parent.parent


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Application lifespan: load vector store and create agent on startup."""
    global _vector_store, _agent

    project_root = _find_project_root()
    db_path = project_root / "data" / "vectordb"

    logger.info("Starting up: loading vector store from %s", db_path)

    try:
        _vector_store = LegalVectorStore(db_path=db_path)
        set_vector_store(_vector_store)
        _agent = JudicialAgent(vector_store=_vector_store)
        logger.info("Startup complete: corpus size = %d", _vector_store.get_stats().get("count", 0))
    except Exception as exc:
        logger.error("Startup failed: %s", exc)
        raise

    yield

    logger.info("Shutting down")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="BenchAssist-IL RAG API",
    description=(
        "Agentic RAG pipeline for Israeli pretrial detention law. "
        "Provides structured judicial reasoning with legal grounding."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models for search endpoint
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    """Request body for the /corpus/search endpoint."""

    query: str = Field(..., description="Search query text.")
    n_results: int = Field(default=5, ge=1, le=50, description="Number of results.")
    language: str | None = Field(
        default=None, description="Optional language filter ('he' or 'en')."
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, Any]:
    """Health check endpoint.

    Returns:
        Status and corpus size.
    """
    corpus_size = 0
    if _vector_store is not None:
        try:
            corpus_size = _vector_store.get_stats().get("count", 0)
        except Exception:
            pass

    return {"status": "ok", "corpus_size": corpus_size}


@app.get("/corpus/stats")
async def corpus_stats() -> dict[str, Any]:
    """Return vector store statistics.

    Returns:
        Collection count, languages, and document names.
    """
    if _vector_store is None:
        raise HTTPException(status_code=503, detail="Vector store not initialised")

    return _vector_store.get_stats()


@app.post("/corpus/search")
async def corpus_search(request: SearchRequest) -> list[RetrievedChunk]:
    """Debug endpoint: search the legal corpus.

    Args:
        request: Search parameters.

    Returns:
        List of retrieved chunks with relevance scores.
    """
    if _vector_store is None:
        raise HTTPException(status_code=503, detail="Vector store not initialised")

    try:
        if request.language:
            results = _vector_store.search(
                query=request.query,
                n_results=request.n_results,
                language=request.language,
            )
        else:
            results = _vector_store.hybrid_search(
                query=request.query,
                n_results=request.n_results,
            )
        return results
    except Exception as exc:
        logger.error("Search failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}")


@app.post("/assess")
async def assess(request: AssessRequest) -> AssessResponse:
    """Run the judicial reasoning pipeline on a case.

    Takes a case text, runs the 3-step agentic pipeline (analyse →
    retrieve → reason), and returns a structured assessment.

    Args:
        request: Case assessment request.

    Returns:
        Full assessment with reasoning, citations, and metadata.
    """
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialised")

    start_time = time.perf_counter()

    try:
        output = _agent.assess(
            case_text=request.case_text,
            case_id=request.case_id,
            language=request.language,
            prompt_mode=request.prompt_mode,
        )
    except Exception as exc:
        logger.error("Assessment failed for case %s: %s", request.case_id, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Assessment failed: {exc}",
        )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    return AssessResponse.from_agent_output(
        output,
        case_id=request.case_id,
        variant_id=request.variant_id,
        model_name=_agent.model_name,
        processing_time_ms=round(elapsed_ms, 2),
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    uvicorn.run(
        "benchassist.rag.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
