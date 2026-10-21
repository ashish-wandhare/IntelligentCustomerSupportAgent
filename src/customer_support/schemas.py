
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TicketCategory(str, Enum):
    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    GENERAL = "general"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(str, Enum):
    OPEN = "open"
    PROCESSING = "processing"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    FAILED = "failed"


class TicketCreate(BaseModel):
    """Customer-submitted ticket."""

    model_config = ConfigDict(str_strip_whitespace=True)

    customer_id: str = Field(min_length=1, max_length=100)
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=5000)


class Ticket(TicketCreate):
    """Ticket enriched with processing and audit metadata."""

    ticket_id: str
    category: TicketCategory = TicketCategory.GENERAL
    priority: TicketPriority = TicketPriority.MEDIUM
    status: TicketStatus = TicketStatus.OPEN

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    resolution: str | None = None
    customer_response: str | None = None
    requires_human_approval: bool = False
    escalation_reason: str | None = None

    # ML prediction confidence scores, from 0.0 to 1.0.
    category_confidence: float | None = Field(
        default=None, ge=0.0, le=1.0
    )
    priority_confidence: float | None = Field(
        default=None, ge=0.0, le=1.0
    )


class ReviewAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"


class ReviewDecision(BaseModel):
    """Human review decision submitted by a reviewer."""

    action: ReviewAction
    reviewer_id: str = Field(min_length=1, max_length=100)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewResponse(BaseModel):
    """Result of a human-review action."""

    ticket_id: str
    status: TicketStatus
    action: ReviewAction
    reviewer_id: str
    comment: str | None = None
    reviewed_at: datetime
