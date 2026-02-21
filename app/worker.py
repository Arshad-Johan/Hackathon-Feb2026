"""
ARQ background worker: classify ticket (category + transformer urgency), push to Redis.
"""

import logging

from arq import run_worker
from arq.connections import RedisSettings

from app.activity import publish_event
from app.broker import add_processed
from app.classifier import _match_category
from app.config import REDIS_URL
from app.models import IncomingTicket, RoutedTicket
from app.sentiment import compute_urgency_score
from app.webhook import trigger_high_urgency_webhook

logger = logging.getLogger(__name__)


async def process_ticket(ctx: dict, payload: dict) -> None:
    """ARQ job: classify ticket, compute S, add to processed queue; trigger webhook if S > 0.8."""
    ticket_id = payload.get("ticket_id", "?")
    logger.info("Processing ticket %s...", ticket_id)
    try:
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
        logger.info("Ticket %s added to queue (urgency=%.2f).", ticket.ticket_id, S)
        publish_event(
            "ticket_processed",
            {
                "ticket_id": routed.ticket_id,
                "urgency_score": round(routed.urgency_score, 3),
                "category": routed.category.value,
                "is_urgent": routed.is_urgent,
            },
        )
        await trigger_high_urgency_webhook(routed)
    except Exception as e:
        logger.exception("Failed to process ticket %s: %s", ticket_id, e)
        raise


class WorkerSettings:
    functions = [process_ticket]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger.info("Worker starting (Redis: %s).", REDIS_URL.split("@")[-1] if "@" in REDIS_URL else REDIS_URL)
    run_worker(WorkerSettings)
