
import asyncio
import logging
from datetime import datetime, timezone

from src.customer_support.database import save_ticket
from src.customer_support.schemas import Ticket, TicketStatus
from src.customer_support.ticket_queue import TicketQueue

logger = logging.getLogger(__name__)


async def process_ticket(ticket: Ticket) -> Ticket:
    """Perform the initial processing step for a ticket."""
    ticket.status = TicketStatus.PROCESSING
    ticket.updated_at = datetime.now(timezone.utc)

    save_ticket(ticket)

    logger.info(
        "Started processing ticket %s.",
        ticket.ticket_id,
    )

    return ticket


async def run_ticket_worker(
    ticket_queue: TicketQueue,
    stop_event: asyncio.Event,
) -> None:
    """Consume queued tickets until a shutdown signal is received."""
    logger.info("Ticket worker started.")

    while not stop_event.is_set():
        try:
            ticket = await asyncio.wait_for(
                ticket_queue.dequeue(),
                timeout=1.0,
            )
        except asyncio.TimeoutError:
            continue

        try:
            await process_ticket(ticket)
        except Exception:
            logger.exception(
                "Failed to process ticket %s.",
                ticket.ticket_id,
            )
        finally:
            ticket_queue.task_done()

    logger.info("Ticket worker stopped.")
