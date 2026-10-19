
import asyncio

import pytest

from src.customer_support.schemas import Ticket
from src.customer_support.ticket_queue import TicketQueue


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
