
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status

from src.customer_support.database import (
    get_ticket,
    initialize_database,
    save_ticket,
)
from src.customer_support.logging_config import configure_logging
from src.customer_support.schemas import Ticket, TicketCreate
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

        # Wait for the worker to finish any current ticket.
        await worker_task

        logger.info("Application shutting down.")


app = FastAPI(
    title="Intelligent Customer Support Agent",
    description="Ticket submission and tracking API",
    version="0.1.0",
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

    # Persist the ticket before queueing it.
    save_ticket(ticket)
    logger.info("Ticket %s saved.", ticket.ticket_id)

    try:
        await ticket_queue.enqueue(ticket)
    except Exception:
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
        )

    logger.info("Ticket %s added to the queue.", ticket.ticket_id)
    return ticket


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
