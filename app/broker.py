"""
Redis-backed processed queue for async broker.

Workers push classified tickets here (sorted set by urgency_score S).
API pops via ZPOPMAX (atomic). No pending list—ARQ holds pending jobs.
"""

import json
from typing import List, Optional

from app.config import REDIS_URL
from app.models import RoutedTicket

PROCESSED_ZSET = "ticket_queue:processed"
_redis_client = None


def _redis():
    import redis
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def add_processed(routed: RoutedTicket) -> None:
    """Add a processed ticket to the ready queue. Score = urgency_score (higher first)."""
    r = _redis()
    member = json.dumps(routed.model_dump())
    r.zadd(PROCESSED_ZSET, {member: routed.urgency_score})


def pop_next() -> Optional[RoutedTicket]:
    """Atomically pop the highest-urgency ticket. Returns None if empty."""
    r = _redis()
    result = r.zpopmax(PROCESSED_ZSET, count=1)
    if not result:
        return None
    member, _ = result[0]
    return RoutedTicket.model_validate(json.loads(member))


def peek_next() -> Optional[RoutedTicket]:
    """Peek highest-urgency ticket without removing."""
    r = _redis()
    members = r.zrange(PROCESSED_ZSET, -1, -1, withscores=False)
    if not members:
        return None
    return RoutedTicket.model_validate(json.loads(members[0]))


def processed_size() -> int:
    """Number of tickets ready to dequeue."""
    return _redis().zcard(PROCESSED_ZSET)


def list_snapshot() -> List[RoutedTicket]:
    """Return all processed tickets in priority order (highest urgency first)."""
    r = _redis()
    members = r.zrange(PROCESSED_ZSET, 0, -1, desc=True, withscores=False)
    return [RoutedTicket.model_validate(json.loads(m)) for m in members]


def clear_all() -> None:
    """Clear the processed queue (e.g. for tests)."""
    _redis().delete(PROCESSED_ZSET)
