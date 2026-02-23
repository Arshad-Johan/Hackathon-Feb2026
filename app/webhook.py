"""
Mock Slack/Discord webhook: POST when urgency score S > 0.8.
Uses WEBHOOK_URL from config; no-op if unset.
"""

import asyncio
import json
import ssl
import urllib.request
from typing import Any

from app.config import WEBHOOK_URL
from app.models import MasterIncident, RoutedTicket


def _build_slack_payload(routed: RoutedTicket) -> dict[str, Any]:
    """Build a Slack-compatible webhook payload (mock)."""
    return {
        "text": f"High-urgency ticket (S={routed.urgency_score:.2f}): {routed.ticket_id}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Ticket:* `{routed.ticket_id}`\n*Subject:* {routed.subject}\n*Category:* {routed.category}\n*Urgency score:* {routed.urgency_score:.2f}",
                },
            },
        ],
    }


def _do_post(url: str, payload: dict[str, Any]) -> None:
    """Synchronous POST (run in thread)."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    ctx = ssl.create_default_context()
    urllib.request.urlopen(req, timeout=5, context=ctx)


async def trigger_high_urgency_webhook(routed: RoutedTicket) -> None:
    """
    If WEBHOOK_URL is set and S > 0.8, POST a mock payload to Slack/Discord.
    Does not raise; fire-and-forget (errors ignored in mock).
    """
    if not WEBHOOK_URL or routed.urgency_score <= 0.8:
        return
    payload = _build_slack_payload(routed)
    try:
        await asyncio.to_thread(_do_post, WEBHOOK_URL, payload)
    except Exception:
        pass  # mock: do not fail the job


def _build_master_incident_payload(incident: MasterIncident) -> dict[str, Any]:
    """Build webhook payload for a master incident (flash-flood)."""
    assert isinstance(incident, MasterIncident)
    return {
        "text": f"Master Incident (flash-flood): {incident.incident_id} – {incident.summary}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Master Incident:* `{incident.incident_id}`\n*Summary:* {incident.summary}\n*Root ticket:* {incident.root_ticket_id}\n*Tickets:* {len(incident.ticket_ids)}",
                },
            },
        ],
    }


async def trigger_master_incident_webhook(incident: MasterIncident) -> None:
    """If WEBHOOK_URL is set, POST once for the master incident (suppresses individual alerts)."""
    if not WEBHOOK_URL:
        return
    payload = _build_master_incident_payload(incident)
    try:
        await asyncio.to_thread(_do_post, WEBHOOK_URL, payload)
    except Exception:
        pass
