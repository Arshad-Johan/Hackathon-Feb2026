"""
Model router with circuit breaker: route urgency scoring to transformer or baseline.
If transformer latency exceeds TRANSFORMER_LATENCY_MS, failover to Milestone 1 (regex) model.
"""

import logging
import time
from enum import Enum

from app.classifier import _is_urgent
from app.config import (
    CIRCUIT_COOLDOWN_SECONDS,
    CIRCUIT_HALF_OPEN_PROBES,
    REDIS_URL,
    TRANSFORMER_LATENCY_MS,
)
from app.sentiment import compute_urgency_score as _transformer_urgency

logger = logging.getLogger(__name__)

CIRCUIT_STATE_KEY = "circuit_breaker:state"
CIRCUIT_OPENED_AT_KEY = "circuit_breaker:opened_at"
CIRCUIT_PROBES_KEY = "circuit_breaker:probes"

_redis_client = None


def _redis():
    import redis
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


def _get_state(r) -> tuple[str, float, int]:
    """Return (state, opened_at_ts, probes_used). Probes key may be missing (use 0)."""
    state = r.get(CIRCUIT_STATE_KEY) or CircuitState.CLOSED.value
    opened = float(r.get(CIRCUIT_OPENED_AT_KEY) or 0)
    probes = int(r.get(CIRCUIT_PROBES_KEY) or 0)
    return state, opened, probes


def _set_state(r, state: str, opened_at: float = 0, probes: int = 0) -> None:
    r.set(CIRCUIT_STATE_KEY, state)
    r.set(CIRCUIT_OPENED_AT_KEY, str(opened_at))
    if probes == 0:
        r.delete(CIRCUIT_PROBES_KEY)
    else:
        r.set(CIRCUIT_PROBES_KEY, str(probes))


def _baseline_urgency(text: str) -> float:
    """Milestone 1 baseline: map regex urgency to S in [0, 1]."""
    if not text or not text.strip():
        return 0.0
    return 0.85 if _is_urgent(text) else 0.25


def score_urgency(text: str) -> float:
    """
    Compute urgency score S in [0, 1]. Uses transformer when circuit is closed;
    on latency > 500ms or errors, fails over to baseline and opens circuit.
    """
    r = _redis()
    state, opened_at, probes = _get_state(r)
    now = time.time()

    # Open -> after cooldown try half-open
    if state == CircuitState.OPEN:
        if now - opened_at < CIRCUIT_COOLDOWN_SECONDS:
            logger.debug("Circuit open; using baseline.")
            return _baseline_urgency(text)
        r.set(CIRCUIT_STATE_KEY, CircuitState.HALF_OPEN.value)
        r.set(CIRCUIT_PROBES_KEY, "0")
        state = CircuitState.HALF_OPEN
        probes = 0

    # Half-open: allow a few probes (atomic INCR); if ok close, else reopen
    if state == CircuitState.HALF_OPEN:
        if probes >= CIRCUIT_HALF_OPEN_PROBES:
            r.set(CIRCUIT_STATE_KEY, CircuitState.CLOSED.value)
            r.delete(CIRCUIT_PROBES_KEY)
            state = CircuitState.CLOSED
        else:
            start = time.perf_counter()
            try:
                S = _transformer_urgency(text)
                latency_ms = (time.perf_counter() - start) * 1000
                if latency_ms > TRANSFORMER_LATENCY_MS:
                    r.set(CIRCUIT_STATE_KEY, CircuitState.OPEN.value)
                    r.set(CIRCUIT_OPENED_AT_KEY, str(now))
                    r.delete(CIRCUIT_PROBES_KEY)
                    logger.warning(
                        "Circuit open: transformer latency %.0f ms > %d ms; failing over to baseline.",
                        latency_ms, TRANSFORMER_LATENCY_MS,
                    )
                    return _baseline_urgency(text)
                r.incr(CIRCUIT_PROBES_KEY)
                return S
            except Exception as e:
                logger.warning("Circuit half-open probe failed: %s; reopening.", e)
                r.set(CIRCUIT_STATE_KEY, CircuitState.OPEN.value)
                r.set(CIRCUIT_OPENED_AT_KEY, str(now))
                r.delete(CIRCUIT_PROBES_KEY)
                return _baseline_urgency(text)

    # Closed: use transformer, measure latency
    start = time.perf_counter()
    try:
        S = _transformer_urgency(text)
        latency_ms = (time.perf_counter() - start) * 1000
        if latency_ms > TRANSFORMER_LATENCY_MS:
            _set_state(r, CircuitState.OPEN.value, now, 0)
            logger.warning(
                "Circuit open: transformer latency %.0f ms > %d ms; failing over to baseline.",
                latency_ms, TRANSFORMER_LATENCY_MS,
            )
            return _baseline_urgency(text)
        return S
    except Exception as e:
        _set_state(r, CircuitState.OPEN.value, now, 0)
        logger.warning("Circuit open: transformer error %s; failing over to baseline.", e)
        return _baseline_urgency(text)


def get_circuit_state() -> dict:
    """Return current circuit breaker state for /health or /metrics."""
    r = _redis()
    state, opened_at, probes = _get_state(r)
    return {"state": state, "opened_at": opened_at, "half_open_probes": probes}
