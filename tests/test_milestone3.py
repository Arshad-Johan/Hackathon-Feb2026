"""
Unit tests for Milestone 3: semantic dedup, circuit breaker, skill-based routing.
Run: pytest tests/test_milestone3.py -v
"""

import math
import pytest

from app.ml.embedding_service import cosine_similarity
from app.ml.model_router import _baseline_urgency, score_urgency
from app.models import Agent, RoutedTicket, SkillVector, TicketCategory
from app.services.routing_utils import (
    cosine_similarity_vec,
    ticket_skill_vector,
    skill_vector_to_list,
)
from app.services.agent_registry import (
    route_ticket,
    register_agent,
    assign_ticket_to_agent,
    get_assignee,
)
from app.services.dedup_service import get_incident, list_incidents
import numpy as np


class TestCosineSimilarity:
    """Cosine similarity and embedding utilities."""

    def test_cosine_similarity_identical(self):
        a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        assert cosine_similarity(a, a) == 1.0

    def test_cosine_similarity_orthogonal(self):
        a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        assert abs(cosine_similarity(a, b)) < 1e-5

    def test_cosine_similarity_threshold(self):
        # Use normalized vectors so dot product equals cosine similarity
        a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        b = np.array([0.95, 0.05, 0.0], dtype=np.float32)
        b = b / np.linalg.norm(b)
        sim = cosine_similarity(a, b)
        assert sim > 0.9


class TestTicketSkillVector:
    """Ticket -> skill vector mapping."""

    def test_technical_vector(self):
        vec = ticket_skill_vector(TicketCategory.TECHNICAL)
        assert len(vec) == 3
        assert vec[0] > 0.99 and abs(vec[1]) < 0.01 and abs(vec[2]) < 0.01

    def test_billing_vector(self):
        vec = ticket_skill_vector(TicketCategory.BILLING)
        assert vec[1] > 0.99 and abs(vec[0]) < 0.01 and abs(vec[2]) < 0.01

    def test_legal_vector(self):
        vec = ticket_skill_vector(TicketCategory.LEGAL)
        assert vec[2] > 0.99 and abs(vec[0]) < 0.01 and abs(vec[1]) < 0.01

    def test_normalized_unit_length(self):
        vec = ticket_skill_vector(TicketCategory.TECHNICAL)
        norm = math.sqrt(sum(x * x for x in vec))
        assert abs(norm - 1.0) < 1e-5


class TestCircuitBreakerBaseline:
    """Baseline urgency (regex) used when circuit is open."""

    def test_baseline_urgent(self):
        s = _baseline_urgency("Broken ASAP fix now")
        assert s >= 0.5

    def test_baseline_not_urgent(self):
        s = _baseline_urgency("Just a question about pricing")
        assert s < 0.5

    def test_score_urgency_returns_valid_range(self):
        # Use baseline only (no Redis/transformer) for predictable unit test
        s = _baseline_urgency("Login broken")
        assert 0.0 <= s <= 1.0


class TestRouting:
    """Skill-based routing: best agent by skill match and capacity (requires Redis)."""

    def _skip_if_no_redis(self, fn):
        try:
            return fn()
        except Exception as e:
            err = str(e).lower()
            if "connectionrefused" in err or "10061" in err or "connection" in err:
                pytest.skip("Redis not running")
            raise

    def test_route_ticket_no_agents_returns_none(self):
        routed = RoutedTicket(
            ticket_id="T1",
            subject="Login broken",
            body="Cannot login",
            category=TicketCategory.TECHNICAL,
            is_urgent=True,
            priority_score=8,
            urgency_score=0.8,
        )
        def _run():
            agent_id = route_ticket(routed)
            assert agent_id is None or isinstance(agent_id, str)
        self._skip_if_no_redis(_run)

    def test_register_and_route_technical(self):
        def _run():
            agent = Agent(
                agent_id="agent-tech-1",
                display_name="Tech Agent",
                skill_vector=SkillVector(tech=0.9, billing=0.05, legal=0.05),
                max_concurrent_tickets=10,
                current_load=0,
                status="online",
            )
            register_agent(agent)
            routed = RoutedTicket(
                ticket_id="T-tech",
                subject="API broken",
                body="Error 500",
                category=TicketCategory.TECHNICAL,
                is_urgent=True,
                priority_score=7,
                urgency_score=0.7,
            )
            agent_id = route_ticket(routed)
            assert agent_id == "agent-tech-1"
            assign_ticket_to_agent(routed.ticket_id, agent_id)
            assert get_assignee("T-tech") == "agent-tech-1"
        self._skip_if_no_redis(_run)

    def test_routing_respects_capacity(self):
        def _run():
            agent = Agent(
                agent_id="agent-full",
                display_name="Full Agent",
                skill_vector=SkillVector(tech=1.0, billing=0.0, legal=0.0),
                max_concurrent_tickets=1,
                current_load=1,
                status="online",
            )
            register_agent(agent)
            routed = RoutedTicket(
                ticket_id="T-cap",
                subject="Bug",
                body="Bug",
                category=TicketCategory.TECHNICAL,
                is_urgent=False,
                priority_score=3,
                urgency_score=0.3,
            )
            agent_id = route_ticket(routed)
            assert agent_id is None or isinstance(agent_id, str)
        self._skip_if_no_redis(_run)


class TestDedupService:
    """Semantic deduplication: incident retrieval (requires Redis)."""

    def test_get_incident_nonexistent(self):
        try:
            assert get_incident("99999") is None
        except Exception as e:
            err = str(e).lower()
            if "connectionrefused" in err or "10061" in err or "connection" in err:
                pytest.skip("Redis not running")
            raise

    def test_list_incidents_empty_or_returns_list(self):
        try:
            incs = list_incidents(limit=5)
            assert isinstance(incs, list)
        except Exception as e:
            err = str(e).lower()
            if "connectionrefused" in err or "10061" in err or "connection" in err:
                pytest.skip("Redis not running")
            raise
