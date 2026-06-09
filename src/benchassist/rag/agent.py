"""LangGraph agent for 3-step judicial reasoning pipeline.

Implements a stateful agent with three processing nodes:
1. **analyze_case** — Extracts legal issues and generates search queries
2. **retrieve_law** → **check_retrieval** — Retrieves and validates legal provisions
3. **judicial_reasoning** — Applies Israeli law and produces a structured assessment

The graph supports up to 2 retrieval rounds if the initial retrieval is
deemed insufficient by the checker.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, TypedDict

from dotenv import load_dotenv

from benchassist.rag.prompts import (
    CASE_ANALYZER_PROMPT,
    RETRIEVAL_CHECKER_PROMPT,
    get_reasoner_prompt,
)
from benchassist.rag.schemas import AgentOutput, LegalCitation, RetrievedChunk
from benchassist.rag.vector_store import LegalVectorStore

logger = logging.getLogger(__name__)

load_dotenv()

_MODEL_NAME = "gemini-2.5-flash"

# JSON fence pattern (same as model_client.py)
_JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*\n?(.*?)\n?```",
    re.DOTALL | re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Agent state
# ---------------------------------------------------------------------------


class AgentState(TypedDict, total=False):
    """Typed state dictionary passed through the LangGraph nodes."""

    case_text: str
    case_id: str
    language: str
    prompt_mode: str
    legal_issues: list[str]
    search_queries: list[str]
    retrieved_chunks: list[RetrievedChunk]
    retrieval_sufficient: bool
    reasoning_output: dict[str, Any]
    legal_citations: list[LegalCitation]
    final_output: AgentOutput | None
    error: str | None
    step_count: int


# ---------------------------------------------------------------------------
# Gemini client helper
# ---------------------------------------------------------------------------


def _get_genai_client() -> Any:
    """Create a google.genai Client using API key from environment."""
    import google.genai as genai

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required.")
    return genai.Client(api_key=api_key)


def _call_gemini(client: Any, prompt: str) -> str:
    """Call Gemini and return the raw text response.

    Uses the same pattern as the existing model_client.py.
    """
    try:
        response = client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt,
        )
        return response.text or ""
    except Exception as exc:
        logger.error("Gemini API call failed: %s", exc)
        raise


def _extract_json(raw_text: str) -> dict[str, Any]:
    """Extract and parse JSON from raw model output, stripping markdown fences."""
    text = raw_text.strip()
    match = _JSON_FENCE_RE.search(text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


# ---------------------------------------------------------------------------
# Graph node functions
# ---------------------------------------------------------------------------


def analyze_case(state: AgentState) -> dict[str, Any]:
    """Node: Analyse the case to extract legal issues and search queries.

    Calls Gemini with :data:`CASE_ANALYZER_PROMPT` and parses the
    structured JSON response.
    """
    case_text = state.get("case_text", "")
    logger.info("analyze_case: processing case %s", state.get("case_id", "unknown"))

    prompt = CASE_ANALYZER_PROMPT.replace("{case_text}", case_text)

    try:
        client = _get_genai_client()
        raw = _call_gemini(client, prompt)
        parsed = _extract_json(raw)

        legal_issues = parsed.get("legal_issues", [])
        search_queries = parsed.get("search_queries", [])
        language = parsed.get("language", state.get("language", "en"))

        logger.info(
            "analyze_case: found %d issues, %d queries, language=%s",
            len(legal_issues),
            len(search_queries),
            language,
        )

        return {
            "legal_issues": legal_issues,
            "search_queries": search_queries,
            "language": language,
            "step_count": state.get("step_count", 0),
        }
    except Exception as exc:
        logger.error("analyze_case failed: %s", exc)
        return {
            "legal_issues": [],
            "search_queries": [case_text[:200]],
            "language": state.get("language", "en"),
            "error": f"Case analysis failed: {exc}",
            "step_count": state.get("step_count", 0),
        }


def retrieve_law(state: AgentState) -> dict[str, Any]:
    """Node: Search the vector store with the generated queries.

    Uses hybrid search to retrieve relevant legal provisions.
    """
    search_queries = state.get("search_queries", [])
    step_count = state.get("step_count", 0) + 1

    logger.info(
        "retrieve_law: executing %d queries (round %d)",
        len(search_queries),
        step_count,
    )

    try:
        store = _get_vector_store()
    except Exception as exc:
        logger.error("Failed to load vector store: %s", exc)
        return {
            "retrieved_chunks": state.get("retrieved_chunks", []),
            "step_count": step_count,
            "error": f"Vector store unavailable: {exc}",
        }

    all_chunks: list[RetrievedChunk] = list(state.get("retrieved_chunks", []))
    seen_ids: set[str] = {
        f"{c.document_name}:{c.section_id}" for c in all_chunks
    }

    for query in search_queries:
        try:
            results = store.hybrid_search(query, n_results=5)
            for chunk in results:
                chunk_key = f"{chunk.document_name}:{chunk.section_id}"
                if chunk_key not in seen_ids:
                    all_chunks.append(chunk)
                    seen_ids.add(chunk_key)
        except Exception as exc:
            logger.warning("Search failed for query %r: %s", query, exc)
            continue

    logger.info(
        "retrieve_law: retrieved %d total chunks after round %d",
        len(all_chunks),
        step_count,
    )

    return {
        "retrieved_chunks": all_chunks,
        "step_count": step_count,
    }


def check_retrieval(state: AgentState) -> dict[str, Any]:
    """Node: Check if retrieved provisions sufficiently cover the legal issues.

    Calls Gemini with :data:`RETRIEVAL_CHECKER_PROMPT`. If insufficient
    and ``step_count < 2``, generates additional queries for another
    retrieval round.
    """
    legal_issues = state.get("legal_issues", [])
    retrieved_chunks = state.get("retrieved_chunks", [])
    step_count = state.get("step_count", 0)

    logger.info(
        "check_retrieval: %d issues, %d chunks, round %d",
        len(legal_issues),
        len(retrieved_chunks),
        step_count,
    )

    # Format retrieved provisions for the prompt
    provisions_text = "\n\n".join(
        f"[{c.document_name} — {c.section_title}]\n{c.text}"
        for c in retrieved_chunks
    )

    issues_text = "\n".join(f"- {issue}" for issue in legal_issues)

    prompt = (RETRIEVAL_CHECKER_PROMPT
        .replace("{legal_issues}", issues_text)
        .replace("{retrieved_provisions}", provisions_text or "(no provisions retrieved)")
    )

    try:
        client = _get_genai_client()
        raw = _call_gemini(client, prompt)
        parsed = _extract_json(raw)

        sufficient = parsed.get("sufficient", True)
        additional_queries = parsed.get("additional_queries", [])

        if not sufficient and step_count < 2 and additional_queries:
            logger.info(
                "check_retrieval: insufficient — %d additional queries for round %d",
                len(additional_queries),
                step_count + 1,
            )
            return {
                "retrieval_sufficient": False,
                "search_queries": additional_queries,
            }

        logger.info("check_retrieval: sufficient=%s", sufficient)
        return {"retrieval_sufficient": True}

    except Exception as exc:
        logger.warning("check_retrieval failed: %s — proceeding to reasoning", exc)
        return {"retrieval_sufficient": True}


def judicial_reasoning(state: AgentState) -> dict[str, Any]:
    """Node: Apply Israeli pretrial detention law and produce a structured assessment.

    Calls Gemini with the appropriate judicial reasoner prompt (based on
    ``prompt_mode``) and parses the response into an :class:`AgentOutput`.
    """
    case_text = state.get("case_text", "")
    prompt_mode = state.get("prompt_mode", "baseline")
    retrieved_chunks = state.get("retrieved_chunks", [])
    search_queries = state.get("search_queries", [])

    logger.info(
        "judicial_reasoning: mode=%s, %d provisions",
        prompt_mode,
        len(retrieved_chunks),
    )

    # Format retrieved provisions
    provisions_text = "\n\n".join(
        f"[{c.document_name} — {c.section_title}]\n{c.text}"
        for c in retrieved_chunks
    )

    # Select and fill the prompt template
    prompt_template = get_reasoner_prompt(prompt_mode)
    prompt = (prompt_template
        .replace("{case_text}", case_text)
        .replace("{retrieved_provisions}", provisions_text or "(no provisions available)")
    )

    try:
        client = _get_genai_client()
        raw = _call_gemini(client, prompt)
        parsed = _extract_json(raw)

        # Parse legal citations
        citations_raw = parsed.get("legal_citations", [])
        citations = []
        for cit in citations_raw:
            try:
                citations.append(LegalCitation(**cit))
            except Exception:
                logger.debug("Skipping malformed citation: %s", cit)

        # Build AgentOutput
        output = AgentOutput(
            recommendation=parsed.get("recommendation", "release_with_conditions"),
            public_safety_risk=parsed.get("public_safety_risk", "medium"),
            obstruction_risk=parsed.get("obstruction_risk", "low"),
            recidivism_risk=parsed.get("recidivism_risk", "medium"),
            confidence=float(parsed.get("confidence", 0.5)),
            reasoning=parsed.get("reasoning", ""),
            legal_citations=citations,
            legal_basis_summary=parsed.get("legal_basis_summary", ""),
            alternatives_considered=parsed.get("alternatives_considered", []),
            retrieved_provisions=[
                f"{c.document_name}: {c.section_title}" for c in retrieved_chunks
            ],
            retrieval_queries=search_queries,
            reasoning_steps=parsed.get("reasoning_steps", []),
        )

        logger.info(
            "judicial_reasoning: recommendation=%s, confidence=%.2f",
            output.recommendation,
            output.confidence,
        )

        return {
            "final_output": output,
            "legal_citations": citations,
            "reasoning_output": parsed,
        }

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse reasoning JSON: %s", exc)
        return {
            "error": f"Reasoning JSON parse error: {exc}",
            "final_output": None,
        }
    except Exception as exc:
        logger.error("judicial_reasoning failed: %s", exc)
        return {
            "error": f"Judicial reasoning failed: {exc}",
            "final_output": None,
        }


# ---------------------------------------------------------------------------
# Graph routing
# ---------------------------------------------------------------------------


def _should_retrieve_more(state: AgentState) -> str:
    """Routing function: decide whether to retrieve more or proceed to reasoning."""
    if not state.get("retrieval_sufficient", False):
        return "retrieve_law"
    return "judicial_reasoning"


# ---------------------------------------------------------------------------
# Vector store singleton
# ---------------------------------------------------------------------------

_vector_store: LegalVectorStore | None = None


def _find_project_root() -> Path:
    """Walk up from this file to locate the project root."""
    current = Path(__file__).resolve().parent
    for ancestor in [current, *list(current.parents)]:
        if (ancestor / "pyproject.toml").exists() or (ancestor / ".git").exists():
            return ancestor
    return Path(__file__).resolve().parent.parent.parent.parent


def _get_vector_store() -> LegalVectorStore:
    """Get or create the singleton vector store instance."""
    global _vector_store
    if _vector_store is None:
        project_root = _find_project_root()
        db_path = project_root / "data" / "vectordb"
        _vector_store = LegalVectorStore(db_path=db_path)
    return _vector_store


def set_vector_store(store: LegalVectorStore) -> None:
    """Inject a vector store instance (useful for testing or custom configs).

    Args:
        store: The :class:`LegalVectorStore` to use.
    """
    global _vector_store
    _vector_store = store


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_agent_graph(*, fast: bool = False) -> Any:
    """Build and compile the LangGraph state graph.

    Args:
        fast: If ``True``, skip the retrieval-checking step for ~40% faster
            processing. The graph becomes:
            ``analyze_case → retrieve_law → judicial_reasoning → END``

    Graph topology (full)::

        analyze_case → retrieve_law → check_retrieval
            ↗ (if insufficient & step_count < 2)  ↘
        retrieve_law ←——————————————  judicial_reasoning → END

    Graph topology (fast)::

        analyze_case → retrieve_law → judicial_reasoning → END

    Returns:
        A compiled LangGraph ``StateGraph``.
    """
    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:
        raise ImportError(
            "langgraph is required for the judicial agent. "
            "Install it with: pip install langgraph"
        ) from exc

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("analyze_case", analyze_case)
    graph.add_node("retrieve_law", retrieve_law)
    graph.add_node("judicial_reasoning", judicial_reasoning)

    # Set entry point
    graph.set_entry_point("analyze_case")

    # Add edges
    graph.add_edge("analyze_case", "retrieve_law")

    if fast:
        # Fast mode: skip retrieval checking, go straight to reasoning
        graph.add_edge("retrieve_law", "judicial_reasoning")
        logger.info("Built FAST agent graph (no retrieval check)")
    else:
        # Full mode: check retrieval, possibly retrieve again
        graph.add_node("check_retrieval", check_retrieval)
        graph.add_edge("retrieve_law", "check_retrieval")
        graph.add_conditional_edges(
            "check_retrieval",
            _should_retrieve_more,
            {
                "retrieve_law": "retrieve_law",
                "judicial_reasoning": "judicial_reasoning",
            },
        )
        logger.info("Built FULL agent graph (with retrieval check)")

    graph.add_edge("judicial_reasoning", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# JudicialAgent wrapper
# ---------------------------------------------------------------------------


class JudicialAgent:
    """High-level wrapper around the LangGraph judicial reasoning pipeline.

    Provides a simple ``assess()`` method that runs the full pipeline and
    returns an :class:`AgentOutput`.

    Example::

        agent = JudicialAgent()
        output = agent.assess(
            case_text="...",
            case_id="case-001",
            language="en",
            prompt_mode="baseline",
        )
        print(output.recommendation)
    """

    def __init__(
        self,
        vector_store: LegalVectorStore | None = None,
        *,
        fast: bool = False,
    ) -> None:
        """Initialise the agent.

        Args:
            vector_store: Optional vector store to use. If not provided,
                the default store at ``data/vectordb/`` is used.
            fast: If ``True``, skip the retrieval-checking step for ~40%
                faster processing. Recommended for batch runs where retrieval
                quality is already validated.
        """
        if vector_store is not None:
            set_vector_store(vector_store)

        self._graph = build_agent_graph(fast=fast)
        self._model_name = _MODEL_NAME
        self._fast = fast
        logger.info(
            "JudicialAgent initialised with model %s (fast=%s)",
            self._model_name,
            fast,
        )

    @property
    def model_name(self) -> str:
        """Return the name of the Gemini model used for reasoning."""
        return self._model_name

    def assess(
        self,
        case_text: str,
        case_id: str,
        language: str = "en",
        prompt_mode: str = "baseline",
    ) -> AgentOutput:
        """Run the full judicial reasoning pipeline on a case.

        Args:
            case_text: Full text of the case to assess.
            case_id: Unique case identifier.
            language: Language of the case text (``'en'`` or ``'he'``).
            prompt_mode: Prompt variant — ``'baseline'``, ``'fairness_aware'``,
                or ``'demographic_blind'``.

        Returns:
            :class:`AgentOutput` with the structured assessment.

        Raises:
            RuntimeError: If the pipeline fails to produce an output.
        """
        logger.info(
            "JudicialAgent.assess: case_id=%s, language=%s, mode=%s",
            case_id,
            language,
            prompt_mode,
        )

        initial_state: AgentState = {
            "case_text": case_text,
            "case_id": case_id,
            "language": language,
            "prompt_mode": prompt_mode,
            "legal_issues": [],
            "search_queries": [],
            "retrieved_chunks": [],
            "retrieval_sufficient": False,
            "reasoning_output": {},
            "legal_citations": [],
            "final_output": None,
            "error": None,
            "step_count": 0,
        }

        try:
            final_state = self._graph.invoke(initial_state)
        except Exception as exc:
            logger.error("Agent pipeline failed for case %s: %s", case_id, exc)
            raise RuntimeError(
                f"Judicial reasoning pipeline failed: {exc}"
            ) from exc

        output = final_state.get("final_output")
        if output is None:
            error = final_state.get("error", "Unknown error")
            raise RuntimeError(
                f"Pipeline produced no output for case {case_id}: {error}"
            )

        return output
