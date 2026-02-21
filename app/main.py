"""REST API for the ticket routing engine (Minimum Viable Router)."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import IncomingTicket, RoutedTicket
from app.queue_store import enqueue, dequeue, size, peek, clear, list_snapshot

app = FastAPI(
    title="Ticket Routing Engine",
    description="High-throughput intelligent routing: categorize tickets, detect urgency, priority queue.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.post("/tickets", response_model=RoutedTicket)
def submit_ticket(payload: IncomingTicket) -> RoutedTicket:
    """
    Accept a ticket JSON payload, classify it (Billing/Technical/Legal),
    detect urgency via regex, and store in the in-memory priority queue.
    Returns the routed ticket (category, is_urgent, priority_score).
    """
    routed = enqueue(payload)
    return routed


@app.get("/tickets/next")
def get_next_ticket() -> RoutedTicket:
    """
    Pop and return the highest-priority ticket from the queue.
    Returns 404 if the queue is empty.
    """
    ticket = dequeue()
    if ticket is None:
        raise HTTPException(status_code=404, detail="No tickets in queue")
    return ticket


@app.get("/tickets/peek")
def peek_next_ticket() -> RoutedTicket:
    """Return the next ticket without removing it. 404 if empty."""
    ticket = peek()
    if ticket is None:
        raise HTTPException(status_code=404, detail="No tickets in queue")
    return ticket


@app.get("/queue/size")
def queue_size() -> dict:
    """Return current number of tickets in the queue."""
    return {"size": size()}


@app.get("/queue", response_model=list[RoutedTicket])
def list_queue() -> list[RoutedTicket]:
    """Return current queue contents in priority order (read-only snapshot)."""
    return list_snapshot()


@app.delete("/queue")
def reset_queue() -> dict:
    """Clear the in-memory queue (useful for testing)."""
    clear()
    return {"status": "queue cleared"}


@app.get("/health")
def health() -> dict:
    """Health check for load balancers / resilience checks."""
    return {"status": "ok"}
