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
    urgency_score: float = Field(
        ...,
        description="Continuous sentiment-based urgency S in [0, 1] (transformer regression)",
        ge=0.0,
        le=1.0,
    )


class TicketAccepted(BaseModel):
    """Response for 202 Accepted: ticket accepted for async processing."""

    ticket_id: str
    job_id: str = Field(..., description="Unique job id for this processing task")
    message: str = Field(default="Accepted for processing")
