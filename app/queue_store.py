"""In-memory priority queue for incoming tickets (heapq)."""

import heapq
from typing import List, Optional

from app.classifier import classify
from app.models import IncomingTicket, RoutedTicket


# Heap entries: (negated_priority, insertion_order, RoutedTicket)
# heapq is min-heap; we want high priority first, so we negate.
_heap: List[tuple] = []
_counter = 0


def _next_order() -> int:
    global _counter
    _counter += 1
    return _counter


def enqueue(ticket: IncomingTicket) -> RoutedTicket:
    """Classify ticket, compute priority, and push onto the priority queue."""
    category, is_urgent, priority_score = classify(
        ticket.ticket_id, ticket.subject, ticket.body, ticket.customer_id
    )
    routed = RoutedTicket(
        ticket_id=ticket.ticket_id,
        subject=ticket.subject,
        body=ticket.body,
        customer_id=ticket.customer_id,
        category=category,
        is_urgent=is_urgent,
        priority_score=priority_score,
    )
    # Min-heap: higher priority first => store (-priority_score, order, item)
    order = _next_order()
    entry = (-routed.priority_score, order, routed)
    heapq.heappush(_heap, entry)
    return routed


def dequeue() -> Optional[RoutedTicket]:
    """Pop the highest-priority ticket from the queue. Returns None if empty."""
    if not _heap:
        return None
    _neg_priority, _order, routed = heapq.heappop(_heap)
    return routed


def size() -> int:
    """Current number of tickets in the queue."""
    return len(_heap)


def peek() -> Optional[RoutedTicket]:
    """Return next ticket without removing it. None if empty."""
    if not _heap:
        return None
    _neg_priority, _order, routed = _heap[0]
    return routed


def list_snapshot() -> List[RoutedTicket]:
    """Return current queue contents in priority order (read-only; does not mutate)."""
    sorted_entries = sorted(_heap, key=lambda e: (e[0], e[1]))
    return [routed for _neg_priority, _order, routed in sorted_entries]


def clear() -> None:
    """Clear the queue (e.g. for tests)."""
    global _heap, _counter
    _heap = []
    _counter = 0
