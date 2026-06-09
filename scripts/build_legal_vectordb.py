#!/usr/bin/env python3
"""Build the legal vector database from the legal corpus.

This script reads all legal documents from legal_corpus/, chunks them,
embeds them using Gemini's text-embedding-004, and stores them in ChromaDB.

Usage::

    python scripts/build_legal_vectordb.py
    python scripts/build_legal_vectordb.py --corpus-dir legal_corpus --db-dir data/vectordb
    python scripts/build_legal_vectordb.py --rebuild  # wipe and rebuild from scratch

"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(_PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build legal vector database")
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=_PROJECT_ROOT / "legal_corpus",
        help="Directory containing legal documents",
    )
    parser.add_argument(
        "--db-dir",
        type=Path,
        default=_PROJECT_ROOT / "data" / "vectordb",
        help="Directory for ChromaDB persistent storage",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Wipe existing DB and rebuild from scratch",
    )
    args = parser.parse_args()

    corpus_dir: Path = args.corpus_dir
    db_dir: Path = args.db_dir

    if not corpus_dir.exists():
        logger.error("Corpus directory not found: %s", corpus_dir)
        sys.exit(1)

    # Rebuild?
    if args.rebuild and db_dir.exists():
        logger.warning("Rebuilding: removing existing vector DB at %s", db_dir)
        shutil.rmtree(db_dir)

    db_dir.mkdir(parents=True, exist_ok=True)

    # Import RAG modules
    from benchassist.rag.corpus_loader import load_legal_corpus
    from benchassist.rag.vector_store import LegalVectorStore

    # 1. Load and chunk legal corpus
    logger.info("Loading legal corpus from %s ...", corpus_dir)
    chunks = load_legal_corpus(corpus_dir)
    logger.info("  Loaded %d chunks from legal corpus", len(chunks))

    if not chunks:
        logger.error("No chunks found! Check that legal_corpus/ contains .txt files.")
        sys.exit(1)

    # Show summary
    languages = set(c.language for c in chunks)
    documents = set(c.document_name for c in chunks)
    logger.info("  Languages: %s", ", ".join(sorted(languages)))
    logger.info("  Documents: %d", len(documents))
    for doc in sorted(documents):
        doc_chunks = [c for c in chunks if c.document_name == doc]
        logger.info("    - %s (%d chunks)", doc, len(doc_chunks))

    # 2. Build vector store
    logger.info("Building vector store at %s ...", db_dir)
    store = LegalVectorStore(db_path=db_dir)
    n_added = store.add_documents(chunks)
    logger.info("  Added %d chunks to vector store", n_added)

    # 3. Verify with a test query
    logger.info("Running verification queries...")
    test_queries = [
        "grounds for pretrial detention public safety",
        "alternatives to detention house arrest bail",
        "proportionality principle human dignity",
    ]
    for query in test_queries:
        results = store.search(query, n_results=3)
        logger.info("  Query: '%s'", query)
        for r in results:
            logger.info(
                "    [%.3f] %s — %s: %s",
                r.score,
                r.document_name,
                r.section_title or r.section_id,
                r.text[:80] + "...",
            )

    # 4. Show stats
    stats = store.get_stats()
    logger.info("Vector store stats: %s", stats)

    print("\n" + "=" * 60)
    print("Legal vector database built successfully!")
    print(f"  Chunks: {n_added}")
    print(f"  Location: {db_dir}")
    print(f"  Documents: {len(documents)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
