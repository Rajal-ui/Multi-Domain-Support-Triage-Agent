"""
Safety rules for escalation-heavy support triage.
"""

import re

from config import ESCALATION_KEYWORDS, INJECTION_PATTERNS


def check_safety_escalation(issue: str, subject: str, company: str | None = None) -> tuple[bool, str]:
    """
    Return whether the ticket should be escalated before retrieval or generation.
    """
    combined = f"{issue} {subject}".lower()

    for pattern in INJECTION_PATTERNS:
        if pattern.lower() in combined:
            return True, f"Adversarial or injection pattern detected: '{pattern}'"

    for keyword in ESCALATION_KEYWORDS:
        if keyword.lower() in combined:
            return True, f"High-risk keyword detected: '{keyword}'"

    privilege_patterns = [
        r"restore\s+my\s+access",
        r"change\s+my\s+score",
        r"increase\s+my\s+score",
        r"move\s+me\s+to\s+the\s+next\s+round",
        r"ban\s+the\s+seller",
        r"refund\s+me\s+today",
        r"share\s+someone\s+else'?s\s+data",
    ]
    for pattern in privilege_patterns:
        if re.search(pattern, combined):
            return True, f"Request requires privileged access: '{pattern}'"

    out_of_scope_patterns = [
        r"actor in (iron man|avengers|batman)",
        r"recipe for",
        r"tell me a joke",
        r"write me a (poem|story|essay)",
    ]
    for pattern in out_of_scope_patterns:
        if re.search(pattern, combined):
            return True, f"Out-of-scope request: '{pattern}'"

    return False, ""
