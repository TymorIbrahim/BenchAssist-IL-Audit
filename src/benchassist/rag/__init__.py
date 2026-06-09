"""Agentic RAG pipeline for Israeli pretrial detention law.

Provides a 3-step LangGraph agent (analyze → retrieve → reason) backed by
ChromaDB vector search with Gemini embeddings, exposed via FastAPI.
"""

from benchassist.rag.schemas import (
    AgentOutput,
    AssessRequest,
    AssessResponse,
    LegalChunk,
    LegalCitation,
    RetrievedChunk,
)
from benchassist.rag.corpus_loader import chunk_statute, load_legal_corpus, load_metadata
from benchassist.rag.vector_store import LegalVectorStore
from benchassist.rag.agent import JudicialAgent

__all__ = [
    "AgentOutput",
    "AssessRequest",
    "AssessResponse",
    "JudicialAgent",
    "LegalChunk",
    "LegalCitation",
    "LegalVectorStore",
    "RetrievedChunk",
    "chunk_statute",
    "load_legal_corpus",
    "load_metadata",
]
