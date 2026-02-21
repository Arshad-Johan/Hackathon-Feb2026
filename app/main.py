"""REST API for the ticket routing engine — async broker (202 Accepted)."""

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.broker import clear_all, peek_next, pop_next, processed_size
from app.config import REDIS_URL
from app.models import IncomingTicket, RoutedTicket, TicketAccepted
from app.sentiment import compute_urgency_score

_arq_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _arq_pool
    from arq import create_pool
    from arq.connections import RedisSettings
    _arq_pool = await create_pool(RedisSettings.from_dsn(REDIS_URL))
    yield
    await _arq_pool.close()
    _arq_pool = None


app = FastAPI(
    title="Ticket Routing Engine",
    description="Async broker: 202 Accepted, Redis + background workers.",
    version="0.2.0",
    lifespan=lifespan,
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
    return TicketAccepted(
        ticket_id=payload.ticket_id,
        job_id=job_id,
        message="Accepted for processing",
    )


@app.get("/tickets/next", response_model=RoutedTicket)
def get_next_ticket() -> RoutedTicket:
    """Pop the highest-urgency ticket from the processed queue. 404 if empty."""
    ticket = pop_next()
    if ticket is None:
        raise HTTPException(status_code=404, detail="No tickets in queue")
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


@app.delete("/queue")
def reset_queue() -> dict:
    """Clear the processed queue (for testing)."""
    clear_all()
    return {"status": "queue cleared"}


@app.get("/health")
def health() -> dict:
    """Health check."""
    return {"status": "ok"}


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
