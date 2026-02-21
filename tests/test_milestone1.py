"""
Tests for Milestone 1: Minimum Viable Router (MVR).

Run against a live server:
  1. Start server: uvicorn app.main:app --host 127.0.0.1 --port 8000
  2. In another terminal: pytest tests/test_milestone1.py -v

Or use the run script (starts server, runs tests, stops server):
  python scripts/run_tests_live.py
"""

import os
import pytest

from tests.http_client import get, post, delete

# Use BASE_URL to hit a running server (default: localhost:8000)
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")


def _url(path):
    return f"{BASE_URL}{path}"


@pytest.fixture(autouse=True)
def reset_queue():
    """Clear queue before each test so tests don't affect each other."""
    delete(_url("/queue"))
    yield
    delete(_url("/queue"))


def test_health():
    """Health endpoint returns 200."""
    r = get(_url("/health"))
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_submit_ticket_returns_routed():
    """POST /tickets accepts JSON and returns category, is_urgent, priority_score, urgency_score S."""
    r = post(
        _url("/tickets"),
        {
            "ticket_id": "T-001",
            "subject": "Invoice wrong",
            "body": "I was charged twice last month.",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ticket_id"] == "T-001"
    assert data["category"] in ("Billing", "Technical", "Legal")
    assert data["category"] == "Billing"
    assert "is_urgent" in data
    assert "urgency_score" in data
    assert 0 <= data["urgency_score"] <= 1
    assert data["priority_score"] >= 0


def test_urgency_detection():
    """Tickets with ASAP/broken/urgent get high urgency (is_urgent=True, S high, priority_score>=1)."""
    r = post(
        _url("/tickets"),
        {
            "ticket_id": "T-urgent",
            "subject": "Login broken ASAP",
            "body": "Cannot login since morning. Need fix ASAP.",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["category"] == "Technical"
    assert data["is_urgent"] is True
    assert data["priority_score"] >= 1
    assert 0 <= data["urgency_score"] <= 1


def test_legal_category():
    """Tickets with legal keywords get Legal category."""
    r = post(
        _url("/tickets"),
        {
            "ticket_id": "T-legal",
            "subject": "GDPR request",
            "body": "I need my data under GDPR compliance.",
        },
    )
    assert r.status_code == 200
    assert r.json()["category"] == "Legal"


def test_queue_size():
    """Queue size increases on submit and decreases on next."""
    assert get(_url("/queue/size")).json()["size"] == 0
    post(_url("/tickets"), {"ticket_id": "A", "subject": "x", "body": "y"})
    assert get(_url("/queue/size")).json()["size"] == 1
    post(_url("/tickets"), {"ticket_id": "B", "subject": "x", "body": "y"})
    assert get(_url("/queue/size")).json()["size"] == 2
    get(_url("/tickets/next"))
    assert get(_url("/queue/size")).json()["size"] == 1


def test_next_returns_404_when_empty():
    """GET /tickets/next returns 404 when queue is empty."""
    r = get(_url("/tickets/next"))
    assert r.status_code == 404
    assert "No tickets" in r.json()["detail"]


def test_peek_does_not_remove():
    """Peek returns next ticket but does not remove it."""
    post(_url("/tickets"), {"ticket_id": "P", "subject": "s", "body": "b"})
    r1 = get(_url("/tickets/peek"))
    r2 = get(_url("/tickets/peek"))
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["ticket_id"] == r2.json()["ticket_id"] == "P"
    assert get(_url("/queue/size")).json()["size"] == 1


def test_priority_order_urgent_first():
    """Urgent tickets are popped before non-urgent ones."""
    post(
        _url("/tickets"),
        {"ticket_id": "normal", "subject": "Question", "body": "Just a question."},
    )
    post(
        _url("/tickets"),
        {
            "ticket_id": "urgent",
            "subject": "Outage ASAP",
            "body": "System is down. Need fix ASAP.",
        },
    )
    first = get(_url("/tickets/next")).json()
    assert first["ticket_id"] == "urgent" and first["is_urgent"] is True
    second = get(_url("/tickets/next")).json()
    assert second["ticket_id"] == "normal"


def test_clear_queue():
    """DELETE /queue clears the queue."""
    post(_url("/tickets"), {"ticket_id": "X", "subject": "s", "body": "b"})
    assert get(_url("/queue/size")).json()["size"] == 1
    r = delete(_url("/queue"))
    assert r.status_code == 200
    assert get(_url("/queue/size")).json()["size"] == 0
    assert get(_url("/tickets/next")).status_code == 404


def test_validation_rejects_missing_fields():
    """POST /tickets with missing required fields returns 422."""
    r = post(_url("/tickets"), {"ticket_id": "T"})  # missing subject, body
    assert r.status_code == 422
