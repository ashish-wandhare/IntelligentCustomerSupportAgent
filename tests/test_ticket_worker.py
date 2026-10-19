
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.customer_support import database
from src.customer_support.schemas import (
    Ticket,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)
from src.customer_support.ticket_queue import TicketQueue
from src.customer_support.ticket_worker import (
    process_ticket,
    run_ticket_worker,
)


@pytest.fixture
def sample_ticket():
    return Ticket(
        ticket_id="TKT-WORKER-001",
        customer_id="CUST-WORKER-001",
        subject="Unable to log in",
        description="I cannot log in after resetting my password.",
    )


@pytest.mark.asyncio
async def test_process_ticket_routes_for_review(sample_ticket):
    with patch(
        "src.customer_support.ticket_worker.run_agent_graph",
        new_callable=AsyncMock,
        return_value={
            "category": TicketCategory.ACCOUNT.value,
            "priority": TicketPriority.CRITICAL.value,
            "category_confidence": 0.95,
            "priority_confidence": 0.95,
            "requires_human_approval": True,
            "escalation_reason": "Critical priority predicted",
            "route": "human_review",
            "knowledge": [],
        },
    ):
        result = await process_ticket(sample_ticket)

    assert result.status == TicketStatus.WAITING_FOR_APPROVAL
    assert result.requires_human_approval is True
    assert result.escalation_reason == "Critical priority predicted"


@pytest.mark.asyncio
async def test_worker_consumes_queued_ticket(sample_ticket):
    queue = TicketQueue()
    await queue.enqueue(sample_ticket)

    stop_event = asyncio.Event()

    with patch(
        "src.customer_support.ticket_worker.process_ticket",
        new_callable=AsyncMock,
    ) as mock_process:
        worker_task = asyncio.create_task(
            run_ticket_worker(queue, stop_event)
        )

        try:
            for _ in range(40):
                if mock_process.await_count > 0:
                    break
                await asyncio.sleep(0.05)
        finally:
            stop_event.set()
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

    mock_process.assert_awaited_once_with(sample_ticket)


@pytest.mark.asyncio
async def test_approved_ticket_resumes_without_reclassification(
    sample_ticket,
):
    sample_ticket.status = TicketStatus.PROCESSING
    sample_ticket.category = TicketCategory.ACCOUNT
    sample_ticket.priority = TicketPriority.HIGH
    sample_ticket.category_confidence = 0.95
    sample_ticket.priority_confidence = 0.90
    sample_ticket.requires_human_approval = False
    sample_ticket.escalation_reason = None

    database.save_ticket(sample_ticket)

    with patch(
        "src.customer_support.ticket_worker.run_agent_graph",
        new_callable=AsyncMock,
        return_value={
            "route": "continue_processing",
            "knowledge": [],
        },
    ) as mock_graph:
        result = await process_ticket(sample_ticket)

    mock_graph.assert_awaited_once()

    graph_state = mock_graph.await_args.args[0]

    assert graph_state["resume_approved"] is True
    assert graph_state["category"] == TicketCategory.ACCOUNT.value
    assert graph_state["priority"] == TicketPriority.HIGH.value

    assert result.status == TicketStatus.RESOLVED
    assert result.resolution is not None
    assert "Automated processing completed" in result.resolution
    assert result.priority == TicketPriority.HIGH
    assert result.category_confidence == 0.95
    assert result.priority_confidence == 0.90
    assert result.requires_human_approval is False

    assert result.status == TicketStatus.RESOLVED
    assert result.resolution is not None
    assert "Automated processing completed" in result.resolution

    assert result.category == TicketCategory.ACCOUNT
    assert result.priority == TicketPriority.HIGH
    assert result.category_confidence == 0.95
    assert result.priority_confidence == 0.90
    assert result.requires_human_approval is False
    assert result.escalation_reason is None