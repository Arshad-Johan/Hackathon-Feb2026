"""
ARQ background worker: classify ticket (category + transformer urgency), push to Redis.
"""

from arq import run_worker
from arq.connections import RedisSettings

from app.broker import add_processed
from app.classifier import _match_category
from app.config import REDIS_URL
from app.models import IncomingTicket, RoutedTicket
from app.sentiment import compute_urgency_score
from app.webhook import trigger_high_urgency_webhook


async def process_ticket(ctx: dict, payload: dict) -> None:
    """ARQ job: classify ticket, compute S, add to processed queue; trigger webhook if S > 0.8."""
    ticket = IncomingTicket.model_validate(payload)
    text = f"{ticket.subject} {ticket.body}"
    category = _match_category(text)
    S = compute_urgency_score(text)
    is_urgent = S >= 0.5
    priority_score = min(10, int(round(S * 10)))
    routed = RoutedTicket(
        ticket_id=ticket.ticket_id,
        subject=ticket.subject,
        body=ticket.body,
        customer_id=ticket.customer_id,
        category=category,
        is_urgent=is_urgent,
        priority_score=priority_score,
        urgency_score=S,
    )
    add_processed(routed)
    await trigger_high_urgency_webhook(routed)


class WorkerSettings:
    functions = [process_ticket]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)


if __name__ == "__main__":
    run_worker(WorkerSettings)
