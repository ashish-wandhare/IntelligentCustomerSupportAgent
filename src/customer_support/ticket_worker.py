import asyncio
import logging
from datetime import datetime, timezone

from src.customer_support.database import save_ticket
from src.customer_support.models.ticket_classifier import predict_ticket
from src.customer_support.knowledge_base.ticket_knowledge import (
    retrieve_ticket_knowledge,
)
from src.customer_support.schemas import (
    Ticket,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)
from src.customer_support.ticket_queue import TicketQueue

logger = logging.getLogger(__name__)

MIN_CONFIDENCE = 0.60


async def retrieve_knowledge_for_ticket(ticket: Ticket) -> list[dict]:
    """Retrieve support passages without blocking the async event loop."""
    return await asyncio.to_thread(
        retrieve_ticket_knowledge,
        ticket.subject,
        ticket.description,
    )


async def process_ticket(ticket: Ticket) -> Ticket:
    """
    Classify new tickets and retrieve support knowledge when permitted.

    Tickets needing human approval wait for review.
    Approved tickets resume without repeating ML classification.
    """
    # An approved ticket already has classification results.
    # Retrieve knowledge without repeating classification.
    if (
        ticket.status == TicketStatus.PROCESSING
        and ticket.category_confidence is not None
        and ticket.priority_confidence is not None
        and not ticket.requires_human_approval
    ):
        try:
            passages = await retrieve_knowledge_for_ticket(ticket)

            logger.info(
                "Retrieved %d knowledge passages for approved ticket %s.",
                len(passages),
                ticket.ticket_id,
            )

            for passage in passages:
                logger.info(
                    "Ticket %s knowledge match: source=%s section=%s score=%.3f",
                    ticket.ticket_id,
                    passage["source"],
                    passage["section"],
                    passage["score"],
                )

            ticket.updated_at = datetime.now(timezone.utc)
            save_ticket(ticket)

        except Exception:
            logger.exception(
                "Knowledge retrieval failed for approved ticket %s.",
                ticket.ticket_id,
            )

        return ticket

    ticket.status = TicketStatus.PROCESSING
    ticket.updated_at = datetime.now(timezone.utc)
    save_ticket(ticket)

    logger.info("Started processing ticket %s.", ticket.ticket_id)

    try:
        # Run CPU-bound model prediction outside the event loop.
        prediction = await asyncio.to_thread(
            predict_ticket,
            ticket.subject,
            ticket.description,
        )

        ticket.category = TicketCategory(str(prediction["category"]))
        ticket.priority = TicketPriority(str(prediction["priority"]))

        ticket.category_confidence = float(
            prediction["category_confidence"]
        )
        ticket.priority_confidence = float(
            prediction["priority_confidence"]
        )

        # Determine whether human review is required.
        review_reasons = []

        if ticket.priority == TicketPriority.CRITICAL:
            review_reasons.append("Critical priority predicted")

        if ticket.category_confidence < MIN_CONFIDENCE:
            review_reasons.append("Low category confidence")

        if ticket.priority_confidence < MIN_CONFIDENCE:
            review_reasons.append("Low priority confidence")

        if review_reasons:
            ticket.requires_human_approval = True
            ticket.escalation_reason = "; ".join(review_reasons)
            ticket.status = TicketStatus.WAITING_FOR_APPROVAL
        else:
            ticket.requires_human_approval = False
            ticket.escalation_reason = None
            ticket.status = TicketStatus.PROCESSING

        ticket.updated_at = datetime.now(timezone.utc)
        save_ticket(ticket)

        logger.info(
            (
                "Ticket %s classified: category=%s, priority=%s, "
                "category_confidence=%.3f, priority_confidence=%.3f, "
                "status=%s"
            ),
            ticket.ticket_id,
            ticket.category.value,
            ticket.priority.value,
            ticket.category_confidence,
            ticket.priority_confidence,
            ticket.status.value,
        )

        if ticket.requires_human_approval:
            logger.warning(
                "Ticket %s requires human review: %s",
                ticket.ticket_id,
                ticket.escalation_reason,
            )
            return ticket

        # Only tickets that do not require approval proceed to RAG.
        passages = await retrieve_knowledge_for_ticket(ticket)

        logger.info(
            "Retrieved %d knowledge passages for ticket %s.",
            len(passages),
            ticket.ticket_id,
        )

        for passage in passages:
            logger.info(
                "Ticket %s knowledge match: source=%s section=%s score=%.3f",
                ticket.ticket_id,
                passage["source"],
                passage["section"],
                passage["score"],
            )

        ticket.updated_at = datetime.now(timezone.utc)
        save_ticket(ticket)

    except Exception:
        logger.exception(
            "Failed to process ticket %s.",
            ticket.ticket_id,
        )

        ticket.status = TicketStatus.FAILED
        ticket.requires_human_approval = True
        ticket.escalation_reason = (
            "Automated processing failed; human review required."
        )
        ticket.updated_at = datetime.now(timezone.utc)
        save_ticket(ticket)

    return ticket


async def run_ticket_worker(
    ticket_queue: TicketQueue,
    stop_event: asyncio.Event,
) -> None:
    """Continuously process tickets from the asynchronous queue."""
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
                "Unexpected worker error while processing ticket %s.",
                ticket.ticket_id,
            )

        finally:
            ticket_queue.task_done()

    logger.info("Ticket worker stopped.")
