from dotenv import load_dotenv

load_dotenv()

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, status

from src.customer_support.database import (
    get_all_tickets,
    get_pending_review_tickets,
    get_ticket,
    get_ticket_reviews,
    initialize_database,
    save_review,
    save_ticket,
)
from src.customer_support.logging_config import configure_logging
from src.customer_support.schemas import (
    ReviewDecision,
    ReviewResponse,
    Ticket,
    TicketCreate,
    TicketStatus,
)
from src.customer_support.ticket_queue import TicketQueue
from src.customer_support.ticket_worker import run_ticket_worker


logger = logging.getLogger(__name__)

ticket_queue = TicketQueue(max_size=100)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources and manage the background worker."""
    configure_logging()
    logger.info("Application starting.")

    initialize_database()
    logger.info("Database initialized.")

    stop_event = asyncio.Event()
    worker_task = asyncio.create_task(
        run_ticket_worker(ticket_queue, stop_event)
    )
    app.state.ticket_worker_task = worker_task

    try:
        yield
    finally:
        logger.info("Stopping ticket worker.")
        stop_event.set()
        await worker_task
        logger.info("Application shutting down.")


app = FastAPI(
    title="Intelligent Customer Support Agent",
    description="Ticket submission, tracking, and human review API",
    version="0.3.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Check whether the API is responding."""
    return {"status": "ok"}


@app.get("/tickets")
async def list_all_tickets(
    limit: int = Query(default=500, ge=1, le=1000),
):
    """Return recent tickets for monitoring and dashboard use."""
    tickets = get_all_tickets(limit)
    return {
        "count": len(tickets),
        "tickets": tickets,
    }


@app.post(
    "/tickets",
    response_model=Ticket,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_ticket(ticket_data: TicketCreate):
    """Create and queue a new customer support ticket."""
    now = datetime.now(timezone.utc)

    ticket = Ticket(
        **ticket_data.model_dump(),
        ticket_id=f"TKT-{uuid4().hex[:12].upper()}",
        created_at=now,
        updated_at=now,
    )

    save_ticket(ticket)
    logger.info("Ticket %s saved.", ticket.ticket_id)

    try:
        await ticket_queue.enqueue(ticket)
    except Exception as exc:
        logger.exception(
            "Ticket %s could not enter the processing queue.",
            ticket.ticket_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ticket queue is unavailable. Please try again.",
        ) from exc

    return ticket


@app.get(
    "/tickets/pending-review",
    response_model=list[Ticket],
)
async def list_pending_review_tickets():
    """Return tickets awaiting human approval."""
    tickets = get_pending_review_tickets()
    return [Ticket(**ticket) for ticket in tickets]


@app.post(
    "/tickets/{ticket_id}/review",
    response_model=ReviewResponse,
)
async def review_ticket(
    ticket_id: str,
    decision: ReviewDecision,
):
    """Approve or reject a ticket awaiting human review."""
    existing_ticket = get_ticket(ticket_id)

    if existing_ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    try:
        review = save_review(ticket_id, decision)
    except ValueError as exc:
        message = str(exc)

        if message == "Ticket not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        ) from exc

    # Preserve the status returned by the review operation.
    # The background worker may change the persisted status immediately.
    review_ticket_data = review["ticket"]
    response_status = review_ticket_data["status"]

    # Re-enqueue approved tickets so the background worker can resume them.
    if decision.action.value == "approve":
        approved_ticket = Ticket(**review_ticket_data)

        try:
            await ticket_queue.enqueue(approved_ticket)
        except Exception as exc:
            logger.exception(
                "Approved ticket %s could not enter the queue.",
                ticket_id,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Approval was recorded, but the ticket could not "
                    "be queued. Retry processing after checking the queue."
                ),
            ) from exc

    return ReviewResponse(
        ticket_id=review_ticket_data["ticket_id"],
        status=response_status,
        action=review["action"],
        reviewer_id=review["reviewer_id"],
        comment=review["comment"],
        reviewed_at=review["reviewed_at"],
    )


@app.get("/tickets/{ticket_id}/reviews")
async def list_ticket_reviews(ticket_id: str):
    """Return review history for a ticket."""
    if get_ticket(ticket_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    return {
        "ticket_id": ticket_id,
        "reviews": get_ticket_reviews(ticket_id),
    }


@app.get("/tickets/{ticket_id}", response_model=Ticket)
async def get_ticket_by_id(ticket_id: str):
    """Return a ticket by its ID."""
    ticket = get_ticket(ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    return Ticket(**ticket)