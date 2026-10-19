
import pytest

from src.customer_support import database
from src.customer_support.schemas import (
    Ticket,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)


@pytest.fixture
def temporary_database(tmp_path, monkeypatch):
    """Use an isolated SQLite database for each test."""
    db_path = tmp_path / "test_customer_support.db"

    monkeypatch.setattr(
        database,
        "get_database_path",
        lambda: db_path,
    )

    database.initialize_database()
    return db_path


@pytest.fixture
def sample_ticket():
    return Ticket(
        ticket_id="TKT-0001",
        customer_id="CUST-001",
        subject="Unable to log in",
        description="I cannot log in after resetting my password.",
        category=TicketCategory.ACCOUNT,
        priority=TicketPriority.HIGH,
    )


def test_initialize_database_creates_tickets_table(temporary_database):
    with database.get_connection() as connection:
        result = connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'tickets'
            """
        ).fetchone()

    assert result is not None


def test_save_and_retrieve_ticket(temporary_database, sample_ticket):
    database.save_ticket(sample_ticket)

    saved = database.get_ticket("TKT-0001")

    assert saved is not None
    assert saved["customer_id"] == "CUST-001"
    assert saved["subject"] == "Unable to log in"
    assert saved["category"] == "account"
    assert saved["priority"] == "high"
    assert saved["status"] == "open"


def test_missing_ticket_returns_none(temporary_database):
    assert database.get_ticket("TKT-MISSING") is None


def test_saving_existing_ticket_updates_processing_fields(
    temporary_database,
    sample_ticket,
):
    database.save_ticket(sample_ticket)

    sample_ticket.status = TicketStatus.RESOLVED
    sample_ticket.resolution = "Password reset instructions provided."

    database.save_ticket(sample_ticket)

    saved = database.get_ticket("TKT-0001")

    assert saved["status"] == "resolved"
    assert saved["resolution"] == (
        "Password reset instructions provided."
    )
    assert saved["subject"] == "Unable to log in"
