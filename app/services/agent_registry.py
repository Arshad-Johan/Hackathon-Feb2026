"""
Agent registry: stateful store of agents with skill vectors and capacity.
Backed by Redis (AGENT:{id}, AGENTS_ONLINE, load and heartbeats).
"""

import json
import logging
from typing import Optional

from app.config import REDIS_URL
from app.models import Agent, RoutedTicket, SkillVector

logger = logging.getLogger(__name__)

AGENT_PREFIX = "agent:"
AGENTS_ONLINE_SET = "agents:online"
TICKET_ASSIGNEE_PREFIX = "ticket_assignee:"

_redis_client = None


def _redis():
    import redis
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def _agent_key(agent_id: str) -> str:
    return f"{AGENT_PREFIX}{agent_id}"


def register_agent(agent: Agent) -> None:
    """Upsert an agent. AGENTS_ONLINE set is kept in sync with agent.status."""
    r = _redis()
    key = _agent_key(agent.agent_id)
    payload = agent.model_dump_json()
    r.set(key, payload)
    if agent.status == "online":
        r.sadd(AGENTS_ONLINE_SET, agent.agent_id)
    else:
        r.srem(AGENTS_ONLINE_SET, agent.agent_id)
    logger.info("Agent %s registered (skills: tech=%.2f billing=%.2f legal=%.2f).",
                agent.agent_id, agent.skill_vector.tech, agent.skill_vector.billing, agent.skill_vector.legal)


# Mock agents for Technical, Billing, Legal, and Generalist (used at startup)
MOCK_AGENTS = [
    Agent(
        agent_id="tech-1",
        display_name="Tech Support",
        skill_vector=SkillVector(tech=0.9, billing=0.05, legal=0.05),
        max_concurrent_tickets=10,
        current_load=0,
        status="online",
    ),
    Agent(
        agent_id="billing-1",
        display_name="Billing Support",
        skill_vector=SkillVector(tech=0.05, billing=0.9, legal=0.05),
        max_concurrent_tickets=10,
        current_load=0,
        status="online",
    ),
    Agent(
        agent_id="legal-1",
        display_name="Legal & Compliance",
        skill_vector=SkillVector(tech=0.05, billing=0.05, legal=0.9),
        max_concurrent_tickets=8,
        current_load=0,
        status="online",
    ),
    Agent(
        agent_id="generalist-1",
        display_name="General Support",
        skill_vector=SkillVector(tech=0.34, billing=0.33, legal=0.33),
        max_concurrent_tickets=10,
        current_load=0,
        status="online",
    ),
]


def seed_mock_agents() -> None:
    """Register mock agents only if they don't exist. Preserves current_load and state on restart."""
    seeded = 0
    for agent in MOCK_AGENTS:
        if get_agent(agent.agent_id) is None:
            register_agent(agent)
            seeded += 1
    if seeded:
        logger.info("Seeded %d mock agents (existing agents left unchanged).", seeded)


def get_agent(agent_id: str) -> Optional[Agent]:
    """Load agent by id."""
    r = _redis()
    raw = r.get(_agent_key(agent_id))
    if not raw:
        return None
    return Agent.model_validate_json(raw)


def set_agent_online(agent_id: str, online: bool) -> None:
    """Mark agent online or offline."""
    r = _redis()
    if online:
        r.sadd(AGENTS_ONLINE_SET, agent_id)
    else:
        r.srem(AGENTS_ONLINE_SET, agent_id)


def set_agent_load(agent_id: str, load: int) -> None:
    """Update current_load for an agent (call after assign/release)."""
    r = _redis()
    agent = get_agent(agent_id)
    if not agent:
        return
    agent.current_load = max(0, load)
    r.set(_agent_key(agent_id), agent.model_dump_json())


def list_online_agents() -> list[Agent]:
    """Return all agents currently in AGENTS_ONLINE set with available capacity."""
    r = _redis()
    ids = r.smembers(AGENTS_ONLINE_SET)
    agents = []
    for aid in ids:
        a = get_agent(aid)
        if a and a.status == "online" and a.current_load < a.max_concurrent_tickets:
            agents.append(a)
    return agents


def assign_ticket_to_agent(ticket_id: str, agent_id: str) -> None:
    """Record assignment and increment agent load."""
    r = _redis()
    r.set(f"{TICKET_ASSIGNEE_PREFIX}{ticket_id}", agent_id)
    agent = get_agent(agent_id)
    if agent:
        agent.current_load = agent.current_load + 1
        r.set(_agent_key(agent_id), agent.model_dump_json())
    logger.info("Assigned ticket %s to agent %s.", ticket_id, agent_id)


def release_ticket_from_agent(ticket_id: str) -> None:
    """Decrement agent load when a ticket is done (e.g. popped from queue). Keeps load in sync."""
    r = _redis()
    key = f"{TICKET_ASSIGNEE_PREFIX}{ticket_id}"
    agent_id = r.get(key)
    if not agent_id:
        return
    agent = get_agent(agent_id)
    if agent:
        agent.current_load = max(0, agent.current_load - 1)
        r.set(_agent_key(agent_id), agent.model_dump_json())
    r.delete(key)


def get_assignee(ticket_id: str) -> Optional[str]:
    """Return agent_id assigned to this ticket, or None."""
    return _redis().get(f"{TICKET_ASSIGNEE_PREFIX}{ticket_id}")


def route_ticket(routed: RoutedTicket) -> Optional[str]:
    """
    Solve a constraint optimization (ILP) to route the ticket to the best available agent:
    maximize skill match minus load penalty, subject to assign-to-exactly-one-agent and capacity.
    Returns agent_id or None if no capacity.
    """
    from app.services.routing_optimizer import solve_routing_ilp

    agents = list_online_agents()
    if not agents:
        logger.warning("No online agents with capacity for ticket %s.", routed.ticket_id)
        return None
    return solve_routing_ilp(routed, agents)


def normalize_skill_vector(vec: list[float]) -> list[float]:
    """Normalize to unit length for cosine similarity."""
    import math
    norm = math.sqrt(sum(x * x for x in vec))
    if norm <= 0:
        return [1/3**0.5, 1/3**0.5, 1/3**0.5]
    return [x / norm for x in vec]


def release_all_assignments() -> int:
    """Release every ticket from its agent and delete all assignment keys. Use after queue clear so load goes to 0."""
    r = _redis()
    keys_to_release = [
        key.replace(TICKET_ASSIGNEE_PREFIX, "")
        for key in r.scan_iter(match=f"{TICKET_ASSIGNEE_PREFIX}*")
    ]
    for ticket_id in keys_to_release:
        release_ticket_from_agent(ticket_id)
    return len(keys_to_release)


def list_assignments(limit: int = 100) -> list[dict]:
    """Return recent ticket -> agent assignments (scan TICKET_ASSIGNEE:*)."""
    r = _redis()
    out = []
    for key in r.scan_iter(match=f"{TICKET_ASSIGNEE_PREFIX}*", count=limit * 2):
        ticket_id = key.replace(TICKET_ASSIGNEE_PREFIX, "")
        agent_id = r.get(key)
        if agent_id:
            out.append({"ticket_id": ticket_id, "agent_id": agent_id})
        if len(out) >= limit:
            break
    return out[:limit]


def tickets_for_agent(agent_id: str) -> list[str]:
    """Return ticket_ids assigned to this agent (scan assignments)."""
    r = _redis()
    out = []
    for key in r.scan_iter(match=f"{TICKET_ASSIGNEE_PREFIX}*"):
        if r.get(key) == agent_id:
            out.append(key.replace(TICKET_ASSIGNEE_PREFIX, ""))
    return out


def reconcile_agent_loads() -> int:
    """
    Set each agent's current_load to the count of tickets currently assigned to them.
    Fixes drift when queue was cleared without releasing or after restarts.
    Returns number of agents updated.
    """
    r = _redis()
    updated = 0
    for key in r.scan_iter(match=f"{AGENT_PREFIX}*"):
        if key == AGENTS_ONLINE_SET:
            continue
        agent_id = key.replace(AGENT_PREFIX, "")
        agent = get_agent(agent_id)
        if not agent:
            continue
        actual_load = len(tickets_for_agent(agent_id))
        if agent.current_load != actual_load:
            old_load = agent.current_load
            agent.current_load = actual_load
            r.set(_agent_key(agent_id), agent.model_dump_json())
            updated += 1
            logger.info("Reconciled agent %s load: %d -> %d.", agent_id, old_load, actual_load)
    return updated


def force_zero_all_loads() -> int:
    """
    Set every agent's current_load to 0. Use after queue clear to guarantee UI shows no load.
    Also deletes any remaining assignment keys so state is clean.
    """
    r = _redis()
    # Delete all assignment keys first so no orphan remains
    for key in list(r.scan_iter(match=f"{TICKET_ASSIGNEE_PREFIX}*")):
        r.delete(key)
    # Then set every agent's load to 0
    zeroed = 0
    for key in r.scan_iter(match=f"{AGENT_PREFIX}*"):
        if key == AGENTS_ONLINE_SET:
            continue
        agent_id = key.replace(AGENT_PREFIX, "")
        agent = get_agent(agent_id)
        if not agent:
            continue
        if agent.current_load != 0:
            agent.current_load = 0
            r.set(_agent_key(agent_id), agent.model_dump_json())
            zeroed += 1
    return zeroed
