"""Data models for the ticket routing engine."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --- Milestone 3: Master Incident (semantic deduplication) ---


class MasterIncident(BaseModel):
    """A single master incident grouping similar tickets (flash-flood suppression)."""

    incident_id: str = Field(..., description="Unique incident identifier")
    summary: str = Field(..., description="Short summary (e.g. from root ticket subject)")
    root_ticket_id: str = Field(..., description="First ticket that triggered the incident")
    ticket_ids: list[str] = Field(default_factory=list, description="All ticket IDs in this incident")
    created_at: float = Field(..., description="Unix timestamp when incident was created")
    status: str = Field(default="open", description="open | resolved")


# --- Milestone 3: Agent registry (skill-based routing) ---


class SkillVector(BaseModel):
    """Agent skill vector: tech, billing, legal (normalized weights)."""

    tech: float = Field(default=0.0, ge=0.0, le=1.0)
    billing: float = Field(default=0.0, ge=0.0, le=1.0)
    legal: float = Field(default=0.0, ge=0.0, le=1.0)


class Agent(BaseModel):
    """An agent with skill vector and capacity."""

    agent_id: str = Field(..., description="Unique agent identifier")
    display_name: str = Field(default="", description="Display name")
    skill_vector: SkillVector = Field(default_factory=lambda: SkillVector(tech=0.34, billing=0.33, legal=0.33))
    max_concurrent_tickets: int = Field(default=10, ge=1)
    current_load: int = Field(default=0, ge=0)
    status: str = Field(default="online", description="online | offline")


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
