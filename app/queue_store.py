"""In-memory priority queue for incoming tickets (heapq)."""

import heapq
from typing import List, Optional

from app.classifier import _match_category
from app.models import IncomingTicket, RoutedTicket
from app.sentiment import compute_urgency_score


# Heap entries: (negated_urgency_score, insertion_order, RoutedTicket)
# heapq is min-heap; we want higher S first, so we negate S.
_heap: List[tuple] = []
_counter = 0


def _next_order() -> int:
    global _counter
    _counter += 1
    return _counter


def enqueue(ticket: IncomingTicket) -> RoutedTicket:
    """Classify category (baseline), compute urgency S (transformer), push onto priority queue."""
    text = f"{ticket.subject} {ticket.body}"
    category = _match_category(text)
    S = compute_urgency_score(text)
    is_urgent = S >= 0.5
    priority_score = min(10, int(round(S * 10)))
    routed = RoutedTicket(
        ticket_id=ticket.ticket_id,
        subject=ticket.subject,
        body=ticket.body,
        customer_id=ticket.customer_id,
        category=category,
        is_urgent=is_urgent,
        priority_score=priority_score,
        urgency_score=S,
    )
    order = _next_order()
    entry = (-routed.urgency_score, order, routed)
    heapq.heappush(_heap, entry)
    return routed


def dequeue() -> Optional[RoutedTicket]:
    """Pop the highest-urgency ticket (by S) from the queue. Returns None if empty."""
    if not _heap:
        return None
    _neg_s, _order, routed = heapq.heappop(_heap)
    return routed


def size() -> int:
    """Current number of tickets in the queue."""
    return len(_heap)


def peek() -> Optional[RoutedTicket]:
    """Return next ticket without removing it. None if empty."""
    if not _heap:
        return None
    _neg_s, _order, routed = _heap[0]
    return routed


def clear() -> None:
    """Clear the queue (e.g. for tests)."""
    global _heap, _counter
    _heap = []
    _counter = 0
