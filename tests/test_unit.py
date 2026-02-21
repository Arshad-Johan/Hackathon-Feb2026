"""
Unit tests for Milestone 1 (no server required).
Run: pytest tests/test_unit.py -v
"""

import pytest

from app.classifier import classify
from app.models import IncomingTicket, TicketCategory
from app.queue_store import enqueue, dequeue, size, peek, clear


class TestClassifier:
    def test_billing_category(self):
        category, is_urgent, score = classify("T1", "Invoice wrong", "I was charged twice.")
        assert category == TicketCategory.BILLING
        assert score == 0

    def test_technical_category(self):
        category, is_urgent, score = classify("T2", "Login broken", "Cannot log in.")
        assert category == TicketCategory.TECHNICAL

    def test_legal_category(self):
        category, _, _ = classify("T3", "GDPR request", "I need my data under compliance.")
        assert category == TicketCategory.LEGAL

    def test_urgency_asap(self):
        _, is_urgent, score = classify("T4", "Broken ASAP", "Fix ASAP please.")
        assert is_urgent is True
        assert score == 1

    def test_urgency_broken(self):
        _, is_urgent, score = classify("T5", "System broken", "Nothing works.")
        assert is_urgent is True
        assert score == 1

    def test_not_urgent(self):
        _, is_urgent, score = classify("T6", "Question", "Just a general question.")
        assert is_urgent is False
        assert score == 0


class TestQueue:
    @pytest.fixture(autouse=True)
    def reset(self):
        clear()
        yield
        clear()

    def test_enqueue_dequeue(self):
        t = IncomingTicket(ticket_id="A", subject="s", body="b")
        r = enqueue(t)
        assert r.ticket_id == "A"
        assert size() == 1
        out = dequeue()
        assert out.ticket_id == "A"
        assert size() == 0

    def test_priority_urgent_first(self):
        enqueue(IncomingTicket(ticket_id="low", subject="q", body="question"))
        enqueue(IncomingTicket(ticket_id="high", subject="ASAP", body="urgent ASAP"))
        first = dequeue()
        assert first.ticket_id == "high" and first.is_urgent
        second = dequeue()
        assert second.ticket_id == "low"

    def test_peek_does_not_remove(self):
        enqueue(IncomingTicket(ticket_id="P", subject="s", body="b"))
        assert peek().ticket_id == "P"
        assert peek().ticket_id == "P"
        assert size() == 1

    def test_clear(self):
        enqueue(IncomingTicket(ticket_id="X", subject="s", body="b"))
        clear()
        assert size() == 0
        assert dequeue() is None
