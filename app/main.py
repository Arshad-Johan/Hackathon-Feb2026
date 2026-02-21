"""REST API for the ticket routing engine — async broker (202 Accepted)."""

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.activity import emit as activity_emit, get_recent as activity_get_recent, start_redis_subscriber
from app.broker import clear_all, list_snapshot, peek_next, pop_next, processed_size
from app.config import REDIS_URL
from app.models import IncomingTicket, RoutedTicket, TicketAccepted
from app.sentiment import compute_urgency_score

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
    """Clear the processed queue (for testing)."""
    clear_all()
    activity_emit("queue_cleared", {})
    return {"status": "queue cleared"}


@app.get("/health")
def health() -> dict:
    """Health check."""
    return {"status": "ok"}


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
    """Test the transformer urgency model only; does not enqueue."""
    S = compute_urgency_score(payload.text)
    return UrgencyTestResponse(urgency_score=S, is_urgent=(S >= 0.5))
