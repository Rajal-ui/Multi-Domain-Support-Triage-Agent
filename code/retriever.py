"""
Retriever: queries the search index and formats context for the LLM.
"""

import logging
from statistics import mean

from config import MIN_RELEVANCE_SCORE, MIN_SOURCE_COUNT, STRONG_MATCH_SCORE, TOP_K
from indexer import SearchIndex

logger = logging.getLogger("triage_agent.retriever")


def build_query(issue: str, subject: str) -> str:
    """Construct a search query from ticket fields."""
    parts = []
    if issue:
        parts.append(issue.strip())
    if subject and subject.strip().lower() not in ("help", "none", ""):
        parts.append(subject.strip())
    return " ".join(parts)


def retrieve_context(
    index: SearchIndex,
    issue: str,
    subject: str,
    domain: str | None = None,
    top_k: int = TOP_K,
) -> tuple[str, list[dict], dict]:
    """
    Retrieve relevant documentation chunks for a ticket.

    Returns:
        Tuple of (formatted context string, list of source metadata dicts, retrieval metadata)
    """
    query = build_query(issue, subject)
    if not query:
        return "No documentation found - query is empty.", [], {
            "query": query,
            "used_fallback_domain": False,
            "top_score": 0.0,
            "avg_score": 0.0,
            "source_count": 0,
            "strong_match": False,
        }

    results = index.search(query=query, top_k=top_k, domain=domain, min_score=MIN_RELEVANCE_SCORE)
    used_fallback_domain = False

    if not results and domain:
        logger.info("No results in domain '%s', searching all domains...", domain)
        results = index.search(query=query, top_k=top_k, domain=None, min_score=MIN_RELEVANCE_SCORE)
        used_fallback_domain = True

    if not results:
        return "No relevant documentation found in the support corpus.", [], {
            "query": query,
            "used_fallback_domain": used_fallback_domain,
            "top_score": 0.0,
            "avg_score": 0.0,
            "source_count": 0,
            "strong_match": False,
        }

    context_parts = []
    sources = []
    seen_files = set()

    for i, (chunk, score) in enumerate(results, 1):
        if chunk.file_path in seen_files:
            continue
        seen_files.add(chunk.file_path)

        context_parts.append(
            f"--- Document {i} ---\n"
            f"Source: {chunk.file_path}\n"
            f"Title: {chunk.title}\n"
            f"Domain: {chunk.domain} / {chunk.product_area}\n"
            f"Relevance: {score:.3f}\n\n"
            f"{chunk.text}\n"
        )
        sources.append({
            "file_path": chunk.file_path,
            "title": chunk.title,
            "domain": chunk.domain,
            "product_area": chunk.product_area,
            "score": score,
        })

    top_score = max(source["score"] for source in sources) if sources else 0.0
    avg_score = mean(source["score"] for source in sources) if sources else 0.0
    retrieval_meta = {
        "query": query,
        "used_fallback_domain": used_fallback_domain,
        "top_score": top_score,
        "avg_score": avg_score,
        "source_count": len(sources),
        "strong_match": len(sources) >= MIN_SOURCE_COUNT and top_score >= STRONG_MATCH_SCORE,
    }

    context = "\n".join(context_parts)
    logger.info(
        "Retrieved %s unique docs for query (domain=%s): %s",
        len(sources),
        domain or "all",
        ", ".join(source["product_area"] for source in sources[:3]),
    )
    return context, sources, retrieval_meta
