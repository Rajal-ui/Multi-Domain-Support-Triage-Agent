"""
Validators: post-generation checks for hallucination and schema compliance.
"""

import logging
import re

from config import VALID_REQUEST_TYPES, VALID_STATUSES

logger = logging.getLogger("triage_agent.validators")


def _normalize_product_area(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")


def _build_corpus_terms(sources: list[dict]) -> set[str]:
    terms: set[str] = set()
    for source in sources:
        for field in ("title", "product_area", "file_path"):
            text = source.get(field, "")
            for token in re.findall(r"[a-z0-9]{4,}", text.lower()):
                terms.add(token)
    return terms


def validate_response(
    result: dict,
    sources: list[dict],
    retrieval_meta: dict,
    raw_company: str,
) -> dict:
    """
    Validate and sanitize the LLM response.

    Checks:
    1. status is a valid enum
    2. request_type is a valid enum
    3. response does not contain unsupported URLs
    4. product_area aligns with retrieved sources
    5. replied answers have minimum grounding in the retrieved corpus

    Returns corrected result dict.
    """
    if result.get("status", "").lower() not in VALID_STATUSES:
        logger.warning("Invalid status '%s', defaulting to 'escalated'", result.get("status"))
        result["status"] = "escalated"
    else:
        result["status"] = result["status"].lower()

    if result.get("request_type", "").lower() not in VALID_REQUEST_TYPES:
        logger.warning(
            "Invalid request_type '%s', defaulting to 'product_issue'",
            result.get("request_type"),
        )
        result["request_type"] = "product_issue"
    else:
        result["request_type"] = result["request_type"].lower()

    urls_in_response = re.findall(r'https?://[^\s,\)\"]+', result.get("response", ""))
    safe_domains = [
        "support.hackerrank.com", "hackerrank.com",
        "support.claude.com", "claude.com", "anthropic.com",
        "visa.co.in", "visa.com",
        "privacy.claude.com",
    ]
    for url in urls_in_response:
        is_safe = any(domain in url for domain in safe_domains)
        if not is_safe:
            logger.warning("Potentially fabricated URL detected: %s", url)
            return {
                "status": "escalated",
                "product_area": sources[0].get("product_area", ""),
                "response": "This request requires human assistance because the automated answer could not be validated safely.",
                "justification": f"Escalated because the draft response included an unsupported URL: {url}",
                "request_type": result.get("request_type", "product_issue"),
            }

    allowed_product_areas = {source.get("product_area", "") for source in sources}
    current_area = result.get("product_area", "")
    
    if current_area and current_area not in allowed_product_areas:
        matched = False
        for allowed in allowed_product_areas:
            if allowed.lower() in current_area.lower() or current_area.lower() in allowed.lower():
                result["product_area"] = allowed
                matched = True
                break
        
        if not matched and sources:
            logger.warning(
                "Product area '%s' not recognized; replacing with top source area '%s'",
                current_area, sources[0].get("product_area")
            )
            result["product_area"] = sources[0].get("product_area", "general")

    corpus_terms = _build_corpus_terms(sources)
    text_to_ground = f"{result.get('response', '')} {result.get('justification', '')}".lower()
    grounded_terms = set(re.findall(r"[a-z0-9]{4,}", text_to_ground))
    overlap_terms = corpus_terms.intersection(grounded_terms)
    if result["status"] == "replied" and len(overlap_terms) < 2:
        logger.warning("Low lexical overlap with retrieved sources; escalating for safety")
        return {
            "status": "escalated",
            "product_area": sources[0].get("product_area", ""),
            "response": "I found related documentation, but the automated answer could not be grounded with enough confidence, so this request should be reviewed by a human.",
            "justification": (
                "Escalated because the generated answer could not be grounded strongly enough in the retrieved corpus "
                f"(top score {retrieval_meta.get('top_score', 0.0):.3f})."
            ),
            "request_type": result.get("request_type", "product_issue"),
        }

    if result["status"] == "replied" and not result.get("product_area"):
        if sources:
            result["product_area"] = sources[0].get("product_area", "general_support")
        else:
            result["product_area"] = "general_support"

    if not result.get("response", "").strip():
        if result["status"] == "escalated":
            result["response"] = "This request requires human assistance."
        else:
            result["response"] = "I could not validate a supported answer from the provided documentation."

    if not result.get("justification", "").strip():
        result["justification"] = "Processed based on available corpus documentation."

    if result["status"] == "escalated" and not result.get("product_area"):
        result["product_area"] = sources[0].get("product_area", _normalize_product_area(raw_company))

    return result
