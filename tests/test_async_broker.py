"""
Tests for async broker API: 202 Accepted, Redis-backed queue.

Requires: Redis running, API server running (worker optional for basic tests).
Run: pytest tests/test_async_broker.py -v
"""

import os
import pytest

from tests.http_client import get, post, delete

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")


def _url(path):
    return f"{BASE_URL}{path}"


@pytest.fixture(autouse=True)
def reset_queue():
    delete(_url("/queue"))
    yield
    delete(_url("/queue"))


def test_health():
    r = get(_url("/health"))
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_post_returns_202_accepted():
    """POST /tickets returns 202 with ticket_id and job_id."""
    r = post(
        _url("/tickets"),
        {"ticket_id": "T-001", "subject": "Invoice wrong", "body": "Charged twice."},
    )
    assert r.status_code == 202
    data = r.json()
    assert data["ticket_id"] == "T-001"
    assert "job_id" in data
    assert "Accepted" in data.get("message", "")


def test_next_404_when_empty():
    r = get(_url("/tickets/next"))
    assert r.status_code == 404
    assert "No tickets" in r.json().get("detail", "")


def test_queue_size_zero_when_empty():
    r = get(_url("/queue/size"))
    assert r.status_code == 200
    assert r.json()["size"] == 0


def test_clear_queue():
    delete(_url("/queue"))
    assert get(_url("/queue/size")).json()["size"] == 0
