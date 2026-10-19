
import asyncio

from src.customer_support.schemas import Ticket


class TicketQueue:
    """Lightweight asynchronous queue for customer support tickets."""

    def __init__(self, max_size: int = 100) -> None:
        if max_size < 1:
            raise ValueError("max_size must be at least 1.")

        self._queue: asyncio.Queue[Ticket] = asyncio.Queue(
            maxsize=max_size
        )

    async def enqueue(self, ticket: Ticket) -> None:
        """Add a ticket to the queue, waiting if the queue is full."""
        await self._queue.put(ticket)

    async def dequeue(self) -> Ticket:
        """Retrieve the next ticket, waiting if the queue is empty."""
        return await self._queue.get()

    def task_done(self) -> None:
        """Mark a dequeued ticket as processed."""
        self._queue.task_done()

    async def join(self) -> None:
        """Wait until all queued tickets have been marked processed."""
        await self._queue.join()

    @property
    def size(self) -> int:
        """Return the number of tickets currently waiting in the queue."""
        return self._queue.qsize()

    @property
    def is_empty(self) -> bool:
        """Return whether the queue has no waiting tickets."""
        return self._queue.empty()
