"""
ARQ background worker: classify ticket (category + transformer urgency), push to Redis.
Milestone 3: semantic deduplication (embeddings + master incident), circuit breaker, routing.
"""

import logging
from dataclasses import replace

from arq import run_worker
from arq.connections import RedisSettings

from app.activity import publish_event
from app.broker import add_processed
from app.classifier import _match_category
from app.config import REDIS_CONN_TIMEOUT, REDIS_URL
from app.models import IncomingTicket, RoutedTicket
from app.services.dedup_service import check_and_record
from app.services.agent_registry import assign_ticket_to_agent, route_ticket
from app.ml.embedding_service import embed_ticket
from app.webhook import trigger_high_urgency_webhook, trigger_master_incident_webhook

logger = logging.getLogger(__name__)


def _compute_urgency_and_build_routed(ticket: IncomingTicket):
    """Compute urgency (via model router with circuit breaker) and build RoutedTicket."""
    from app.ml.model_router import score_urgency
    text = f"{ticket.subject} {ticket.body}"
    category = _match_category(text)
    S = score_urgency(text)
    is_urgent = S >= 0.5
    priority_score = min(10, int(round(S * 10)))
    return RoutedTicket(
        ticket_id=ticket.ticket_id,
        subject=ticket.subject,
        body=ticket.body,
        customer_id=ticket.customer_id,
        category=category,
        is_urgent=is_urgent,
        priority_score=priority_score,
        urgency_score=S,
    )


async def process_ticket(ctx: dict, payload: dict) -> None:
    """ARQ job: classify ticket, compute S, dedup, add to queue; webhook if S > 0.8 (or master incident)."""
    ticket_id = payload.get("ticket_id", "?")
    logger.info("Processing ticket %s...", ticket_id)
    try:
        ticket = IncomingTicket.model_validate(payload)
        routed = _compute_urgency_and_build_routed(ticket)
        embedding = embed_ticket(ticket.subject, ticket.body)
        is_master, incident_id, suppress_individual, created_new_incident = check_and_record(routed, embedding)
        add_processed(routed)
        agent_id = route_ticket(routed)
        if agent_id:
            assign_ticket_to_agent(routed.ticket_id, agent_id)
            publish_event(
                "ticket_assigned_to_agent",
                {"ticket_id": routed.ticket_id, "agent_id": agent_id},
            )
        logger.info("Ticket %s added to queue (urgency=%.2f).", ticket.ticket_id, routed.urgency_score)
        if is_master and incident_id:
            publish_event(
                "ticket_linked_to_master_incident",
                {
                    "ticket_id": routed.ticket_id,
                    "incident_id": incident_id,
                    "urgency_score": round(routed.urgency_score, 3),
                    "category": routed.category.value,
                },
            )
            if created_new_incident:
                from app.services.dedup_service import get_incident
                inc = get_incident(incident_id)
                if inc:
                    publish_event(
                        "master_incident_created",
                        {
                            "incident_id": incident_id,
                            "summary": inc.summary,
                            "root_ticket_id": inc.root_ticket_id,
                            "ticket_count": len(inc.ticket_ids),
                        },
                    )
                    await trigger_master_incident_webhook(inc)
        else:
            publish_event(
                "ticket_processed",
                {
                    "ticket_id": routed.ticket_id,
                    "urgency_score": round(routed.urgency_score, 3),
                    "category": routed.category.value,
                    "is_urgent": routed.is_urgent,
                },
            )
        if not suppress_individual:
            await trigger_high_urgency_webhook(routed)
    except Exception as e:
        logger.exception("Failed to process ticket %s: %s", ticket_id, e)
        raise


class WorkerSettings:
    functions = [process_ticket]
    redis_settings = replace(
        RedisSettings.from_dsn(REDIS_URL),
        conn_timeout=REDIS_CONN_TIMEOUT,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger.info("Worker starting (Redis: %s).", REDIS_URL.split("@")[-1] if "@" in REDIS_URL else REDIS_URL)
    run_worker(WorkerSettings)
