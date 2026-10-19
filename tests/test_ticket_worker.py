
import asyncio
from datetime import datetime, timezone

import pytest

from src.customer_support.database import get_ticket, initialize_database
from src.customer_support.schemas import Ticket, TicketCreate, TicketStatus
from src.customer_support.ticket_queue import TicketQueue
from src.customer_support import database
from src.customer_support.ticket_worker import (
    process_ticket,
    run_ticket_worker,
)


@pytest.fixture
def sample_ticket(tmp_path, monkeypatch):
    """Create an isolated database and a sample ticket."""
    db_path = tmp_path / "worker_test.db"

    monkeypatch.setattr(
        database,
        "get_database_path",
        lambda: db_path,
    )
    initialize_database()

    now = datetime.now(timezone.utc)
    ticket = Ticket(
        ticket_id="TKT-WORKER-001",
        customer_id="CUST-WORKER-001",
        subject="Unable to access my account",
        description="I cannot access my account after changing my password.",
        created_at=now,
        updated_at=now,
    )
    database.save_ticket(ticket)
    return ticket


@pytest.mark.asyncio
async def test_process_ticket_updates_status(sample_ticket):
    processed = await process_ticket(sample_ticket)

    assert processed.status == TicketStatus.PROCESSING
    assert processed.updated_at >= processed.created_at

    saved = get_ticket(sample_ticket.ticket_id)
    assert saved["status"] == TicketStatus.PROCESSING.value


@pytest.mark.asyncio
async def test_worker_consumes_queued_ticket(sample_ticket):
    queue = TicketQueue(max_size=10)
    stop_event = asyncio.Event()

    await queue.enqueue(sample_ticket)

    worker_task = asyncio.create_task(
        run_ticket_worker(queue, stop_event)
    )

    try:
        await asyncio.wait_for(queue.join(), timeout=3)
    finally:
        stop_event.set()
        await asyncio.wait_for(worker_task, timeout=3)

    saved = get_ticket(sample_ticket.ticket_id)
    assert saved["status"] == TicketStatus.PROCESSING.value
    assert queue.is_empty
