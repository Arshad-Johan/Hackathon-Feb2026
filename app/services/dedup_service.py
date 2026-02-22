"""
Semantic deduplication: sliding-window cosine similarity and Master Incident creation.
When > DEDUP_MIN_COUNT tickets in DEDUP_WINDOW_SECONDS have similarity > DEDUP_SIM_THRESHOLD,
create a single Master Incident and suppress individual alerts.
"""

import json
import logging
import time
from typing import Optional

import numpy as np

from app.config import (
    DEDUP_MIN_COUNT,
    DEDUP_SIM_THRESHOLD,
    DEDUP_WINDOW_SECONDS,
    REDIS_URL,
)
from app.ml.embedding_service import cosine_similarity
from app.models import MasterIncident, RoutedTicket

logger = logging.getLogger(__name__)

DEDUP_WINDOW_ZSET = "dedup:window"
DEDUP_META_PREFIX = "dedup:meta:"
INCIDENT_NEXT_ID = "incident:next_id"
INCIDENT_PREFIX = "incident:"
INCIDENT_TICKETS_PREFIX = "incident_tickets:"
TICKET_INCIDENT_PREFIX = "ticket_incident:"

_redis_client = None


def _redis():
    import redis
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def _window_start() -> float:
    return time.time() - DEDUP_WINDOW_SECONDS


def _prune_window(r) -> None:
    """Remove entries older than the window."""
    r.zremrangebyscore(DEDUP_WINDOW_ZSET, "-inf", _window_start())


def _similar_ticket_ids_in_window(
    r,
    embedding: np.ndarray,
    threshold: float = DEDUP_SIM_THRESHOLD,
) -> list[str]:
    """Return ticket_ids in the current window whose embedding similarity to `embedding` is > threshold."""
    now = time.time()
    start = _window_start()
    ticket_ids = r.zrangebyscore(DEDUP_WINDOW_ZSET, start, now)
    similar = []
    pipe = r.pipeline()
    for tid in ticket_ids:
        pipe.get(f"{DEDUP_META_PREFIX}{tid}")
    metas = pipe.execute()
    for tid, meta_json in zip(ticket_ids, metas):
        if not meta_json:
            continue
        try:
            meta = json.loads(meta_json)
            emb = np.array(meta["embedding"], dtype=np.float32)
            if cosine_similarity(embedding, emb) > threshold:
                similar.append(tid)
        except (KeyError, TypeError, json.JSONDecodeError):
            continue
    return similar


def _get_incident_for_ticket(r, ticket_id: str) -> Optional[str]:
    """Return incident_id if this ticket is already linked to an incident."""
    return r.get(f"{TICKET_INCIDENT_PREFIX}{ticket_id}")


def _create_master_incident(
    r,
    root_ticket_id: str,
    summary: str,
    ticket_ids: list[str],
) -> str:
    """Create a new master incident and link all ticket_ids. Returns incident_id."""
    incident_id = str(r.incr(INCIDENT_NEXT_ID))
    key = f"{INCIDENT_PREFIX}{incident_id}"
    now = time.time()
    r.hset(key, mapping={
        "incident_id": incident_id,
        "summary": summary,
        "root_ticket_id": root_ticket_id,
        "created_at": str(now),
        "status": "open",
    })
    tickets_key = f"{INCIDENT_TICKETS_PREFIX}{incident_id}"
    for tid in ticket_ids:
        r.sadd(tickets_key, tid)
        r.set(f"{TICKET_INCIDENT_PREFIX}{tid}", incident_id)
    logger.info(
        "Dedup: created master incident %s with %d tickets (root=%s)",
        incident_id, len(ticket_ids), root_ticket_id,
    )
    return incident_id


def _add_ticket_to_incident(r, incident_id: str, ticket_id: str) -> None:
    """Link ticket to existing incident."""
    r.sadd(f"{INCIDENT_TICKETS_PREFIX}{incident_id}", ticket_id)
    r.set(f"{TICKET_INCIDENT_PREFIX}{ticket_id}", incident_id)
    logger.info("Dedup: linked ticket %s to master incident %s", ticket_id, incident_id)


def check_and_record(
    routed: RoutedTicket,
    embedding: np.ndarray,
) -> tuple[bool, Optional[str], bool, bool]:
    """
    Record the ticket in the sliding window and check for flash-flood.
    Returns (is_part_of_master_incident, master_incident_id or None, should_suppress_individual_alert, created_new_incident).
    """
    r = _redis()
    now = time.time()
    ticket_id = routed.ticket_id
    meta = {
        "embedding": embedding.tolist(),
        "category": routed.category.value,
        "urgency_score": routed.urgency_score,
        "subject": routed.subject,
    }
    r.zadd(DEDUP_WINDOW_ZSET, {ticket_id: now})
    r.set(f"{DEDUP_META_PREFIX}{ticket_id}", json.dumps(meta), ex=DEDUP_WINDOW_SECONDS + 10)
    _prune_window(r)

    similar = _similar_ticket_ids_in_window(r, embedding)
    # Spec: "more than 10 tickets" => need strictly > DEDUP_MIN_COUNT (e.g. 11+ when DEDUP_MIN_COUNT=10)
    if len(similar) <= DEDUP_MIN_COUNT:
        return False, None, False, False

    # Flash-flood: always create a new master incident (do not reuse existing)
    summary = routed.subject or f"Incident (root: {ticket_id})"
    incident_id = _create_master_incident(r, root_ticket_id=ticket_id, summary=summary, ticket_ids=similar)
    # Current ticket was already in similar; ensure it is linked
    r.sadd(f"{INCIDENT_TICKETS_PREFIX}{incident_id}", ticket_id)
    r.set(f"{TICKET_INCIDENT_PREFIX}{ticket_id}", incident_id)
    return True, incident_id, True, True


def remove_ticket_from_incident(ticket_id: str) -> None:
    """
    When a ticket is popped from the queue, remove it from its master incident.
    If the incident has no tickets left, mark it resolved.
    """
    r = _redis()
    incident_id = r.get(f"{TICKET_INCIDENT_PREFIX}{ticket_id}")
    if not incident_id:
        return
    r.srem(f"{INCIDENT_TICKETS_PREFIX}{incident_id}", ticket_id)
    r.delete(f"{TICKET_INCIDENT_PREFIX}{ticket_id}")
    remaining = r.scard(f"{INCIDENT_TICKETS_PREFIX}{incident_id}")
    if remaining == 0:
        r.hset(f"{INCIDENT_PREFIX}{incident_id}", "status", "resolved")
        logger.info("Incident %s resolved (no tickets left).", incident_id)
    else:
        logger.info("Removed ticket %s from incident %s (%d tickets left).", ticket_id, incident_id, remaining)


def close_incident(incident_id: str) -> bool:
    """Mark an incident as resolved (closed). Returns True if updated."""
    r = _redis()
    key = f"{INCIDENT_PREFIX}{incident_id}"
    if not r.exists(key):
        return False
    r.hset(key, "status", "resolved")
    logger.info("Incident %s closed by user.", incident_id)
    return True


def get_incident(incident_id: str) -> Optional[MasterIncident]:
    """Load a master incident by id."""
    r = _redis()
    key = f"{INCIDENT_PREFIX}{incident_id}"
    raw = r.hgetall(key)
    if not raw:
        return None
    ticket_ids = list(r.smembers(f"{INCIDENT_TICKETS_PREFIX}{incident_id}"))
    return MasterIncident(
        incident_id=raw["incident_id"],
        summary=raw["summary"],
        root_ticket_id=raw["root_ticket_id"],
        ticket_ids=sorted(ticket_ids),
        created_at=float(raw["created_at"]),
        status=raw.get("status", "open"),
    )


def list_incidents(limit: int = 50, status: Optional[str] = None) -> list[MasterIncident]:
    """List recent incidents (by id order). Optionally filter by status."""
    r = _redis()
    # We don't have a global list; we can scan INCIDENT:* keys
    keys = []
    for key in r.scan_iter(match=f"{INCIDENT_PREFIX}*"):
        if key == INCIDENT_NEXT_ID:
            continue
        if key.startswith(INCIDENT_TICKETS_PREFIX):
            continue
        keys.append(key)
    def _incident_sort_key(k: str) -> int:
        try:
            return int(k.replace(INCIDENT_PREFIX, ""))
        except ValueError:
            return 0
    incidents = []
    for key in sorted(keys, key=_incident_sort_key, reverse=True)[:limit * 2]:
        inc_id = key.replace(INCIDENT_PREFIX, "")
        inc = get_incident(inc_id)
        if inc and (status is None or inc.status == status):
            incidents.append(inc)
        if len(incidents) >= limit:
            break
    return incidents[:limit]
