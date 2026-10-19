
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status

from src.customer_support.database import (
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
            detail=(
                "Ticket was saved but could not enter "
                "the processing queue."
            ),
        ) from exc

    logger.info("Ticket %s added to the queue.", ticket.ticket_id)
    return ticket


@app.get(
    "/tickets/pending-review",
    response_model=list[Ticket],
)
async def list_pending_review_tickets():
    """List tickets awaiting a human decision."""
    records = get_pending_review_tickets()
    return [Ticket.model_validate(record) for record in records]


@app.post(
    "/tickets/{ticket_id}/review",
    response_model=ReviewResponse,
)
async def review_ticket(ticket_id: str, decision: ReviewDecision):
    """Approve or reject a ticket awaiting human review."""
    try:
        result = save_review(ticket_id, decision)
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

    if decision.action.value == "approve":
        record = get_ticket(ticket_id)

        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found after approval.",
            )

        approved_ticket = Ticket.model_validate(record)

        try:
            await ticket_queue.enqueue(approved_ticket)
        except Exception as exc:
            logger.exception(
                "Approved ticket %s could not be queued.",
                ticket_id,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Review was saved, but the approved ticket "
                    "could not be queued for processing."
                ),
            ) from exc

        logger.info(
            "Approved ticket %s added back to the processing queue.",
            ticket_id,
        )

    logger.info(
        "Ticket %s reviewed: action=%s reviewer=%s status=%s",
        ticket_id,
        result["action"],
        result["reviewer_id"],
        result["ticket"]["status"],
    )

    return ReviewResponse(
        ticket_id=ticket_id,
        status=TicketStatus(result["ticket"]["status"]),
        action=result["action"],
        reviewer_id=result["reviewer_id"],
        comment=result["comment"],
        reviewed_at=datetime.fromisoformat(result["reviewed_at"]),
    )


@app.get("/tickets/{ticket_id}/reviews")
async def read_ticket_reviews(ticket_id: str):
    """Retrieve review history for a ticket."""
    if get_ticket(ticket_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    return get_ticket_reviews(ticket_id)


@app.get("/tickets/{ticket_id}", response_model=Ticket)
async def read_ticket(ticket_id: str):
    """Retrieve a ticket by its ID."""
    record = get_ticket(ticket_id)

    if record is None:
        logger.warning("Ticket %s was not found.", ticket_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    return Ticket.model_validate(record)
