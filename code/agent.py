"""
Core agent: orchestrates the triage pipeline for a single ticket.

Pipeline: Company Router -> Safety Gate -> Retriever -> Grounding Gate -> LLM -> Validator
"""

import logging

from classifier import pre_classify
from config import SYSTEM_PROMPT, TICKET_PROMPT_TEMPLATE
from indexer import SearchIndex
from llm_client import call_llm
from retriever import retrieve_context
from safety import check_safety_escalation
from utils import detect_language, normalize_company
from validators import validate_response

logger = logging.getLogger("triage_agent.agent")


def validate_output(resp: dict) -> dict:
    """
    Final evaluator-facing schema guard before writing output.csv.
    """
    required = ["status", "product_area", "response", "justification", "request_type"]
    for field in required:
        if field not in resp:
            return {
                "status": "escalated",
                "product_area": "unknown",
                "response": "This request requires human assistance.",
                "justification": f"Escalated because output field '{field}' was missing.",
                "request_type": "product_issue",
            }
    return resp


def process_ticket(
    ticket: dict,
    index: SearchIndex,
    ticket_num: int = 0,
) -> dict:
    """
    Process a single support ticket through the full triage pipeline.

    Args:
        ticket: Dict with keys: issue, subject, company
        index: The search index for retrieval
        ticket_num: Ticket number for logging

    Returns:
        Dict with: status, product_area, response, justification, request_type
    """
    issue = ticket.get("issue", "").strip()
    subject = ticket.get("subject", "").strip()
    raw_company = ticket.get("company", "").strip()

    logger.info("=== Ticket #%s ===", ticket_num)
    logger.info("  Company: %s", raw_company or "None")
    logger.info("  Subject: %s", subject[:80] or "(empty)")
    logger.info("  Issue: %s...", issue[:120])

    domain = normalize_company(raw_company)
    logger.info("  Domain routed to: %s", domain or "all (no company)")

    should_escalate, safety_reason = check_safety_escalation(issue, subject, domain)
    if should_escalate:
        logger.info("  Safety escalated: %s", safety_reason)
        return validate_output({
            "status": "escalated",
            "product_area": domain or "",
            "response": "This request requires human assistance because it involves a sensitive, high-risk, or unsupported issue.",
            "justification": f"Escalated: {safety_reason}. This type of request requires human review for safety and accuracy.",
            "request_type": "product_issue",
        })

    pre_result = pre_classify(issue, subject, domain)
    if pre_result is not None:
        logger.info("  Pre-classified: %s / %s", pre_result["status"], pre_result["request_type"])
        return validate_output(pre_result)

    lang = detect_language(issue)
    if lang != "english":
        logger.info("  Language detected: %s", lang)

    context, sources, retrieval_meta = retrieve_context(
        index=index,
        issue=issue,
        subject=subject,
        domain=domain,
    )

    if not sources:
        logger.info("  Escalating because retrieval found no supporting documentation")
        return validate_output({
            "status": "escalated",
            "product_area": domain or "",
            "response": "I could not find supporting documentation in the provided corpus for this request, so it needs human review.",
            "justification": "Escalated because no relevant support documentation was retrieved from the provided corpus.",
            "request_type": "product_issue",
        })

    if not retrieval_meta["strong_match"]:
        logger.info(
            "  Escalating because retrieval match is weak (top_score=%.3f, sources=%s)",
            retrieval_meta["top_score"],
            retrieval_meta["source_count"],
        )
        return validate_output({
            "status": "escalated",
            "product_area": sources[0].get("product_area", domain or ""),
            "response": "I found only weak or partial matches in the provided documentation, so this request should be reviewed by a human.",
            "justification": (
                "Escalated because retrieved documentation was not strong enough to answer safely "
                f"(top score {retrieval_meta['top_score']:.3f})."
            ),
            "request_type": "product_issue",
        })

    domain_label = domain or "all domains"
    user_prompt = TICKET_PROMPT_TEMPLATE.format(
        company=raw_company or "Unknown",
        subject=subject or "(no subject)",
        issue=issue,
        domain=domain_label,
        context=context,
    )

    result = call_llm(SYSTEM_PROMPT, user_prompt)
    result = validate_response(result, sources, retrieval_meta, raw_company)
    result = validate_output(result)

    logger.info(
        "  Result: status=%s, type=%s, area=%s",
        result["status"],
        result["request_type"],
        result["product_area"],
    )
    return result
