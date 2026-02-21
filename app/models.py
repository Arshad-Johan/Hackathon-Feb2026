"""Data models for the ticket routing engine."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TicketCategory(str, Enum):
    """Supported ticket categories."""

    BILLING = "Billing"
    TECHNICAL = "Technical"
    LEGAL = "Legal"


class IncomingTicket(BaseModel):
    """Payload for an incoming support ticket."""

    ticket_id: str = Field(..., description="Unique ticket identifier")
    subject: str = Field(..., description="Ticket subject line")
    body: str = Field(..., description="Ticket body/description")
    customer_id: Optional[str] = Field(None, description="Optional customer identifier")


class RoutedTicket(BaseModel):
    """Ticket after classification and urgency detection."""

    ticket_id: str
    subject: str
    body: str
    customer_id: Optional[str] = None
    category: TicketCategory
    is_urgent: bool
    priority_score: int = Field(
        ...,
        description="Higher = more urgent; used for queue ordering",
        ge=0,
    )
