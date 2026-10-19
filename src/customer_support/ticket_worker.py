
import asyncio
import logging
from datetime import datetime, timezone

from src.customer_support.agent_graph import run_agent_graph
from src.customer_support.database import save_ticket
from src.customer_support.schemas import Ticket, TicketStatus
from src.customer_support.ticket_queue import TicketQueue

logger = logging.getLogger(__name__)


def ticket_has_existing_classification(ticket: Ticket) -> bool:
    """Check whether the ticket already has ML classification results."""
    return (
        ticket.category_confidence is not None
        and ticket.priority_confidence is not None
    )


def ticket_is_resuming_after_approval(ticket: Ticket) -> bool:
    """Check whether an approved ticket is resuming processing."""
    return (
        ticket.status == TicketStatus.PROCESSING
        and ticket_has_existing_classification(ticket)
        and not ticket.requires_human_approval
    )


async def process_ticket(ticket: Ticket) -> Ticket:
    """Process a ticket using classification, LangGraph, and RAG."""
    resuming_approved_ticket = ticket_is_resuming_after_approval(ticket)

    try:
        if resuming_approved_ticket:
            logger.info(
                "Resuming approved ticket %s without reclassification.",
                ticket.ticket_id,
            )
        else:
            ticket.status = TicketStatus.PROCESSING
            ticket.updated_at = datetime.now(timezone.utc)
            save_ticket(ticket)

        graph_state = {
            "ticket_id": ticket.ticket_id,
            "subject": ticket.subject,
            "description": ticket.description,
            "resume_approved": resuming_approved_ticket,
        }

        # Preserve the original ML classification after human approval.
        if resuming_approved_ticket:
            graph_state.update(
                {
                    "category": ticket.category.value,
                    "priority": ticket.priority.value,
                    "category_confidence": ticket.category_confidence,
                    "priority_confidence": ticket.priority_confidence,
                    "requires_human_approval": False,
                    "escalation_reason": None,
                }
            )

        result = await run_agent_graph(graph_state)

        # Apply classification results for tickets processed for the first time.
        if not resuming_approved_ticket:
            from src.customer_support.schemas import (
                TicketCategory,
                TicketPriority,
            )

            ticket.category = TicketCategory(result["category"])
            ticket.priority = TicketPriority(result["priority"])
            ticket.category_confidence = result["category_confidence"]
            ticket.priority_confidence = result["priority_confidence"]
            ticket.requires_human_approval = result[
                "requires_human_approval"
            ]
            ticket.escalation_reason = result.get("escalation_reason")

            # Pause automated processing when human review is required.
            if ticket.requires_human_approval:
                ticket.status = TicketStatus.WAITING_FOR_APPROVAL
                ticket.updated_at = datetime.now(timezone.utc)
                save_ticket(ticket)

                logger.info(
                    "Ticket %s requires human approval.",
                    ticket.ticket_id,
                )
                return ticket

        # Log the knowledge passages returned by the RAG retriever.
        knowledge = result.get("knowledge", [])

        for passage in knowledge:
            logger.info(
                "Knowledge retrieved for ticket %s: %s",
                ticket.ticket_id,
                passage,
            )

        # Mark successful automated processing as resolved.
        ticket.status = TicketStatus.RESOLVED
        ticket.resolution = (
            "Automated processing completed. "
            "Relevant knowledge articles were retrieved."
        )
        ticket.requires_human_approval = False
        ticket.escalation_reason = None
        ticket.updated_at = datetime.now(timezone.utc)
        save_ticket(ticket)

        logger.info(
            "Ticket %s processing completed successfully.",
            ticket.ticket_id,
        )

        return ticket

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
    queue: TicketQueue,
    stop_event: asyncio.Event,
) -> None:
    """Continuously consume and process tickets from the queue."""
    while not stop_event.is_set():
        try:
            ticket = await asyncio.wait_for(
                queue.dequeue(),
                timeout=1.0,
            )
        except asyncio.TimeoutError:
            continue

        try:
            await process_ticket(ticket)
        except Exception:
            logger.exception(
                "Worker encountered an error processing ticket %s.",
                ticket.ticket_id,
            )
        finally:
            queue.task_done()
