"""
In-memory activity log for backend events (ticket accepted, processed, popped, queue cleared).
Worker publishes "ticket_processed" via Redis pub/sub; API subscribes in a background thread.
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from app.config import REDIS_URL

logger = logging.getLogger(__name__)

ACTIVITY_CHANNEL = "ticket_activity"
MAX_EVENTS = 200


@dataclass
class ActivityEvent:
    """A single backend activity event."""

    ts: float = field(default_factory=time.time)
    type: str = ""
    data: dict[str, Any] = field(default_factory=dict)


_events: list[ActivityEvent] = []
_lock = threading.Lock()


def emit(event_type: str, data: dict[str, Any] | None = None) -> None:
    """Append an event to the activity log (call from API)."""
    with _lock:
        _events.append(ActivityEvent(type=event_type, data=data or {}))
        while len(_events) > MAX_EVENTS:
            _events.pop(0)


def get_recent(limit: int = 100) -> list[dict]:
    """Return the most recent events (newest last). Each item is dict with ts, type, data."""
    with _lock:
        out = [
            {"ts": e.ts, "type": e.type, "data": e.data}
            for e in _events[-limit:]
        ]
    return out


def _redis_subscriber_thread() -> None:
    """Run in a daemon thread: subscribe to Redis channel and append worker events."""
    try:
        import redis
        r = redis.from_url(REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        pubsub.subscribe(ACTIVITY_CHANNEL)
        logger.info("Activity subscriber listening on channel %s", ACTIVITY_CHANNEL)
        for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                payload = json.loads(message["data"])
                event_type = payload.get("type", "ticket_processed")
                emit(event_type, payload.get("data", payload))
            except Exception as e:
                logger.warning("Activity message parse error: %s", e)
    except Exception as e:
        logger.warning("Activity Redis subscriber failed: %s", e)


def start_redis_subscriber() -> None:
    """Start the background thread that listens for worker events."""
    t = threading.Thread(target=_redis_subscriber_thread, daemon=True)
    t.start()


def publish_event(event_type: str, data: dict[str, Any]) -> None:
    """Publish an event to Redis (call from worker). Subscribers will append to their activity log."""
    try:
        import redis
        r = redis.from_url(REDIS_URL, decode_responses=True)
        payload = json.dumps({"type": event_type, "data": data})
        r.publish(ACTIVITY_CHANNEL, payload)
    except Exception as e:
        logger.warning("Activity publish failed: %s", e)
