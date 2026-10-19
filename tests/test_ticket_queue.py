
import asyncio

import pytest

from unittest.mock import AsyncMock, patch

from src.customer_support.schemas import Ticket
from src.customer_support.ticket_queue import TicketQueue
from src.customer_support.ticket_worker import (
    process_ticket,
    run_ticket_worker,
)


@pytest.fixture
def sample_ticket():
    return Ticket(
        ticket_id="TKT-0001",
        customer_id="CUST-001",
        subject="Unable to log in",
        description="I cannot log in after resetting my password.",
    )


def test_enqueue_and_dequeue(sample_ticket):
    async def scenario():
        queue = TicketQueue()

        await queue.enqueue(sample_ticket)

        assert queue.size == 1
        assert queue.is_empty is False

        received = await queue.dequeue()

        assert received.ticket_id == sample_ticket.ticket_id
        assert queue.size == 0

        queue.task_done()
        await queue.join()

    asyncio.run(scenario())


def test_queue_preserves_fifo_order(sample_ticket):
    async def scenario():
        queue = TicketQueue()

        second_ticket = sample_ticket.model_copy(
            update={"ticket_id": "TKT-0002"}
        )

        await queue.enqueue(sample_ticket)
        await queue.enqueue(second_ticket)

        first = await queue.dequeue()
        queue.task_done()

        second = await queue.dequeue()
        queue.task_done()

        assert first.ticket_id == "TKT-0001"
        assert second.ticket_id == "TKT-0002"

        await queue.join()

    asyncio.run(scenario())


def test_queue_rejects_invalid_capacity():
    with pytest.raises(ValueError):
        TicketQueue(max_size=0)


def test_queue_blocks_enqueue_when_full(sample_ticket):
    async def scenario():
        queue = TicketQueue(max_size=1)

        await queue.enqueue(sample_ticket)

        second_ticket = sample_ticket.model_copy(
            update={"ticket_id": "TKT-0002"}
        )

        pending = asyncio.create_task(queue.enqueue(second_ticket))
        await asyncio.sleep(0)

        assert not pending.done()

        received = await queue.dequeue()
        assert received.ticket_id == "TKT-0001"
        queue.task_done()

        await pending

        received_second = await queue.dequeue()
        assert received_second.ticket_id == "TKT-0002"
        queue.task_done()

        await queue.join()

    asyncio.run(scenario())


@pytest.mark.asyncio
async def test_process_ticket_routes_for_review(sample_ticket):
    with patch(
        "src.customer_support.ticket_worker.run_agent_graph",
        new_callable=AsyncMock,
        return_value={
            "category": "account",
            "priority": "critical",
            "category_confidence": 0.95,
            "priority_confidence": 0.95,
            "requires_human_approval": True,
            "escalation_reason": "Critical priority predicted",
            "route": "human_review",
            "knowledge": [],
        },
    ):
        result = await process_ticket(sample_ticket)

    from src.customer_support.schemas import TicketStatus

    assert result.status == TicketStatus.WAITING_FOR_APPROVAL
    assert result.requires_human_approval is True


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
