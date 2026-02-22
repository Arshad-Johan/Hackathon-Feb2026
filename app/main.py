"""REST API for the ticket routing engine — async broker (202 Accepted)."""

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.activity import emit as activity_emit, get_recent as activity_get_recent, start_redis_subscriber
from app.broker import clear_all, list_snapshot, peek_next, pop_next, processed_size
from app.config import REDIS_URL
from app.models import Agent, IncomingTicket, MasterIncident, RoutedTicket, TicketAccepted
from app.ml.model_router import score_urgency, get_circuit_state
from app.services.dedup_service import close_incident, get_incident, list_incidents, remove_ticket_from_incident
from app.services.agent_registry import (
    get_agent,
    list_assignments,
    list_online_agents,
    force_zero_all_loads,
    reconcile_agent_loads,
    register_agent,
    release_all_assignments,
    release_ticket_from_agent,
    seed_mock_agents,
    tickets_for_agent,
)

_arq_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _arq_pool
    _arq_pool = None
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        _arq_pool = await create_pool(RedisSettings.from_dsn(REDIS_URL))
    except Exception as e:
        import logging
        logging.warning("Redis/ARQ pool unavailable: %s. POST /tickets will return 503.", e)
    start_redis_subscriber()
    try:
        try:
            seed_mock_agents()
        except Exception as e:
            import logging
            logging.warning("Could not seed mock agents (Redis down?): %s", e)
        yield
    finally:
        if _arq_pool is not None:
            await _arq_pool.close()
            _arq_pool = None


app = FastAPI(
    title="Ticket Routing Engine",
    description="Async broker: 202 Accepted, Redis + background workers.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.post("/tickets", status_code=202, response_model=TicketAccepted)
async def submit_ticket(payload: IncomingTicket) -> TicketAccepted:
    """
    Accept a ticket and return 202 Accepted immediately.
    A background worker classifies it and enqueues to the processed queue.
    """
    pool = _arq_pool
    if pool is None:
        raise HTTPException(status_code=503, detail="Worker pool not ready")
    job = await pool.enqueue_job("process_ticket", payload.model_dump())
    job_id = job.job_id if job else str(uuid4())
    activity_emit("ticket_accepted", {"ticket_id": payload.ticket_id, "job_id": job_id})
    return TicketAccepted(
        ticket_id=payload.ticket_id,
        job_id=job_id,
        message="Accepted for processing",
    )


class BatchTicketsAccepted(BaseModel):
    """Response for 202 Accepted when submitting multiple tickets."""

    accepted: list[TicketAccepted] = Field(..., description="One entry per submitted ticket")


@app.post("/tickets/batch", status_code=202, response_model=BatchTicketsAccepted)
async def submit_tickets_batch(payloads: list[IncomingTicket]) -> BatchTicketsAccepted:
    """
    Accept multiple tickets and return 202 Accepted immediately.
    Each ticket is enqueued for background processing; responses are in the same order as the request.
    """
    pool = _arq_pool
    if pool is None:
        raise HTTPException(status_code=503, detail="Worker pool not ready")
    if not payloads:
        return BatchTicketsAccepted(accepted=[])
    accepted_list: list[TicketAccepted] = []
    for p in payloads:
        job = await pool.enqueue_job("process_ticket", p.model_dump())
        job_id = job.job_id if job else str(uuid4())
        accepted_list.append(
            TicketAccepted(
                ticket_id=p.ticket_id,
                job_id=job_id,
                message="Accepted for processing",
            )
        )
        activity_emit("ticket_accepted", {"ticket_id": p.ticket_id, "job_id": job_id})
    return BatchTicketsAccepted(accepted=accepted_list)


@app.get("/tickets/next", response_model=RoutedTicket)
def get_next_ticket() -> RoutedTicket:
    """Pop the highest-urgency ticket from the processed queue. 404 if empty."""
    ticket = pop_next()
    if ticket is None:
        raise HTTPException(status_code=404, detail="No tickets in queue")
    release_ticket_from_agent(ticket.ticket_id)
    remove_ticket_from_incident(ticket.ticket_id)
    activity_emit("ticket_popped", {"ticket_id": ticket.ticket_id, "urgency_score": ticket.urgency_score})
    return ticket


@app.get("/tickets/peek", response_model=RoutedTicket)
def peek_next_ticket() -> RoutedTicket:
    """Peek next ticket without removing. 404 if empty."""
    ticket = peek_next()
    if ticket is None:
        raise HTTPException(status_code=404, detail="No tickets in queue")
    return ticket


@app.get("/queue/size")
def queue_size() -> dict:
    """Number of processed tickets ready to dequeue."""
    return {"size": processed_size()}


@app.get("/queue", response_model=list[RoutedTicket])
def list_queue() -> list[RoutedTicket]:
    """Return current queue contents in priority order (read-only snapshot)."""
    return list_snapshot()


@app.delete("/queue")
def reset_queue() -> dict:
    """Clear the processed queue (for testing). Removes incidents for queued tickets, clears queue, then forces all agent loads to 0."""
    snapshot = list_snapshot()
    for routed in snapshot:
        remove_ticket_from_incident(routed.ticket_id)
    clear_all()
    force_zero_all_loads()  # Delete all assignment keys and set every agent current_load=0 so UI is consistent
    activity_emit("queue_cleared", {})
    return {"status": "queue cleared"}


@app.get("/activity")
def get_activity(limit: int = 100) -> dict:
    """Return recent backend activity events (ticket accepted, processed, popped, queue cleared)."""
    if limit < 1 or limit > 200:
        limit = 100
    return {"events": activity_get_recent(limit=limit)}


# --- Test endpoint for transformer only (no queue) ---


class UrgencyTestRequest(BaseModel):
    text: str = Field(..., description="Text to score")


class UrgencyTestResponse(BaseModel):
    urgency_score: float = Field(..., description="S in [0, 1]")
    is_urgent: bool = Field(..., description="True if S >= 0.5")


@app.post("/urgency-score", response_model=UrgencyTestResponse)
def test_urgency_score(payload: UrgencyTestRequest) -> UrgencyTestResponse:
    """Test the urgency model (transformer or baseline via circuit breaker); does not enqueue."""
    S = score_urgency(payload.text)
    return UrgencyTestResponse(urgency_score=S, is_urgent=(S >= 0.5))


# --- Milestone 3: Master Incidents (semantic deduplication) ---


@app.get("/incidents", response_model=list[MasterIncident])
def get_incidents_list(limit: int = 50, status: str | None = None) -> list[MasterIncident]:
    """List master incidents (flash-flood groupings). Optionally filter by status (open/resolved)."""
    if limit < 1 or limit > 100:
        limit = 50
    return list_incidents(limit=limit, status=status)


@app.get("/incidents/{incident_id}", response_model=MasterIncident)
def get_incident_by_id(incident_id: str) -> MasterIncident:
    """Get a single master incident by id."""
    inc = get_incident(incident_id)
    if inc is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc


@app.post("/incidents/{incident_id}/close", response_model=MasterIncident)
def close_incident_endpoint(incident_id: str) -> MasterIncident:
    """Close (resolve) an open incident."""
    if not close_incident(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")
    inc = get_incident(incident_id)
    assert inc is not None
    return inc


# --- Milestone 3: Skill-based routing (agents & assignments) ---


@app.post("/agents", response_model=Agent)
def register_agent_endpoint(agent: Agent) -> Agent:
    """Register or update an agent (skill vector, capacity)."""
    register_agent(agent)
    return get_agent(agent.agent_id) or agent


@app.get("/agents", response_model=list[Agent])
def list_agents_endpoint(online_only: bool = False) -> list[Agent]:
    """List agents. If online_only=True, only agents in AGENTS_ONLINE with capacity."""
    if online_only:
        return list_online_agents()
    import redis
    from app.config import REDIS_URL
    r = redis.from_url(REDIS_URL, decode_responses=True)
    agents = []
    for key in r.scan_iter(match="agent:*"):
        raw = r.get(key)
        if raw:
            try:
                agents.append(Agent.model_validate_json(raw))
            except Exception:
                pass
    return agents


@app.get("/agents/{agent_id}", response_model=Agent)
def get_agent_endpoint(agent_id: str) -> Agent:
    """Get agent by id."""
    a = get_agent(agent_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return a


@app.get("/assignments")
def get_assignments(limit: int = 100) -> dict:
    """List ticket -> agent assignments."""
    return {"assignments": list_assignments(limit=limit)}


@app.get("/agents/{agent_id}/tickets")
def get_agent_tickets(agent_id: str) -> dict:
    """List ticket_ids assigned to this agent."""
    if get_agent(agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"agent_id": agent_id, "ticket_ids": tickets_for_agent(agent_id)}


@app.post("/agents/loads/reconcile")
def reconcile_loads() -> dict:
    """Set each agent's current_load to the count of tickets currently assigned to them. Use after queue clear or to fix drift."""
    updated = reconcile_agent_loads()
    return {"status": "ok", "agents_updated": updated}


@app.post("/agents/loads/zero")
def zero_loads() -> dict:
    """Set every agent's current_load to 0 and remove all assignment keys. Use when queue is empty but loads still show (fix inconsistent state)."""
    zeroed = force_zero_all_loads()
    return {"status": "ok", "agents_zeroed": zeroed}


@app.get("/health")
def health() -> dict:
    """Health check (includes circuit breaker state for Milestone 3)."""
    out = {"status": "ok"}
    try:
        out["circuit_breaker"] = get_circuit_state()
    except Exception:
        pass
    return out


@app.get("/metrics")
def metrics() -> dict:
    """Milestone 3 metrics: incidents, circuit breaker, agents."""
    out = {}
    try:
        out["circuit_breaker"] = get_circuit_state()
        out["master_incidents_count"] = len(list_incidents(limit=1000))
        out["online_agents_count"] = len(list_online_agents())
    except Exception as e:
        out["error"] = str(e)
    return out
