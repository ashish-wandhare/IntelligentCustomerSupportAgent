import pytest
from pydantic import ValidationError

from src.customer_support.schemas import (
    Ticket,
    TicketCategory,
    TicketCreate,
    TicketPriority,
    TicketStatus,
)


@pytest.fixture
def valid_ticket_data():
    return {
        "customer_id": "CUST-001",
        "subject": "Unable to log in",
        "description": (
            "I cannot log in to my account after resetting my password."
        ),
    }


def test_valid_ticket_create(valid_ticket_data):
    ticket = TicketCreate(**valid_ticket_data)

    assert ticket.customer_id == "CUST-001"
    assert ticket.subject == "Unable to log in"


def test_rejects_short_subject(valid_ticket_data):
    valid_ticket_data["subject"] = "Hi"

    with pytest.raises(ValidationError):
        TicketCreate(**valid_ticket_data)


def test_ticket_defaults(valid_ticket_data):
    ticket = Ticket(
        **valid_ticket_data,
        ticket_id="TKT-0001",
    )

    assert ticket.category == TicketCategory.GENERAL
    assert ticket.priority == TicketPriority.MEDIUM
    assert ticket.status == TicketStatus.OPEN
    assert ticket.requires_human_approval is False


def test_ticket_accepts_assigned_priority(valid_ticket_data):
    ticket = Ticket(
        **valid_ticket_data,
        ticket_id="TKT-0002",
        category=TicketCategory.ACCOUNT,
        priority=TicketPriority.HIGH,
    )

    assert ticket.category == TicketCategory.ACCOUNT
    assert ticket.priority == TicketPriority.HIGH
