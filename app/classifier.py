"""Baseline classifier: category routing + regex-based urgency detection."""

import re
from typing import Optional, Tuple

from app.models import TicketCategory


# Category keywords (case-insensitive). First match wins in order: Billing, Technical, Legal.
CATEGORY_PATTERNS = {
    TicketCategory.BILLING: [
        r"\b(?:bill|invoice|payment|charge|refund|subscription|plan upgrade|plan downgrade)\b",
        r"\b(?:billing|overcharge|double charge|cancel subscription)\b",
    ],
    TicketCategory.TECHNICAL: [
        r"\b(?:bug|error|crash|login|api|integration|slow|timeout)\b",
        r"\b(?:broken|not working|doesn't work|failed|failure)\b",
        r"\b(?:technical|support|help|issue)\b",
    ],
    TicketCategory.LEGAL: [
        r"\b(?:legal|lawyer|attorney|compliance|gdpr|privacy|terms|contract)\b",
        r"\b(?:subpoena|litigation|dispute|liability)\b",
    ],
}

# Urgency: higher priority if any of these appear (case-insensitive).
URGENCY_PATTERNS = [
    r"\b(?:asap|as soon as possible)\b",
    r"\b(?:urgent|emergency|critical)\b",
    r"\b(?:broken|outage|down|not working)\b",
    r"\b(?:immediately|right now)\b",
    r"\b(?:P0|P1|severity 1)\b",
]

_urgency_re = re.compile("|".join(URGENCY_PATTERNS), re.IGNORECASE)


def _match_category(text: str) -> TicketCategory:
    """Classify ticket into Billing, Technical, or Legal using keyword heuristics."""
    for category, patterns in CATEGORY_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                return category
    return TicketCategory.TECHNICAL  # default


def _is_urgent(text: str) -> bool:
    """Detect urgency via regex (e.g. 'broken', 'ASAP')."""
    return bool(_urgency_re.search(text))


def classify(
    ticket_id: str,
    subject: str,
    body: str,
    customer_id: Optional[str] = None,
) -> Tuple[TicketCategory, bool, int]:
    """
    Run baseline classifier on ticket text.
    Returns (category, is_urgent, priority_score).
    priority_score: 1 = urgent, 0 = normal (higher = higher priority in queue).
    """
    text = f"{subject} {body}"
    category = _match_category(text)
    is_urgent = _is_urgent(text)
    priority_score = 1 if is_urgent else 0
    return category, is_urgent, priority_score
