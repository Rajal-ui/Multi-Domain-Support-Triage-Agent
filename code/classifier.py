"""
Classifier: lightweight invalid-request detection and request typing helpers.
"""

import logging
import re

logger = logging.getLogger("triage_agent.classifier")


def check_invalid(issue: str, subject: str) -> tuple[bool, str]:
    """
    Check if a ticket is invalid (off-topic, spam, greeting, etc.).
    Invalid tickets get status=replied with a polite out-of-scope response.

    Returns:
        Tuple of (is_invalid, reason)
    """
    combined = f"{issue} {subject}".strip().lower()

    if len(combined.split()) < 3:
        return True, "Ticket too short to be actionable"

    greeting_patterns = [
        r"^(thank you|thanks|thx|ty|cheers|merci)\s*[.!]?\s*$",
        r"^(thank you|thanks|thx|ty|cheers|merci)\b.*$",
        r"^(hi|hello|hey|good morning|good evening)\s*[.!]?\s*$",
        r"^happy to help\s*$",
    ]
    for pattern in greeting_patterns:
        if re.match(pattern, combined):
            return True, "Message is a greeting or acknowledgment, not a support request"

    offtopic_patterns = [
        r"actor in (iron man|avengers|batman)",
        r"recipe for",
        r"who is the president",
        r"what is the capital of",
        r"tell me a joke",
        r"write me a (poem|story|essay)",
    ]
    for pattern in offtopic_patterns:
        if re.search(pattern, combined):
            return True, f"Off-topic question: '{pattern}'"

    return False, ""


def pre_classify(issue: str, subject: str, company: str | None) -> dict | None:
    """
    Pre-classification gate for tickets that can be answered without retrieval.

    Returns:
        A partial result dict if the ticket is clearly invalid,
        or None if normal processing is needed.
    """
    is_invalid, reason = check_invalid(issue, subject)
    if is_invalid:
        logger.info("INVALID: %s", reason)
        return {
            "status": "replied",
            "product_area": "general_support",
            "response": "This does not appear to be a product support request I can handle. If you have a specific support issue, please share it.",
            "justification": f"Marked as invalid: {reason}",
            "request_type": "invalid",
        }

    return None
