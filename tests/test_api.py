
import pytest
from fastapi.testclient import TestClient

from src.customer_support import api
from src.customer_support import database
from src.customer_support.ticket_queue import TicketQueue


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a test client with an isolated database and queue."""
    db_path = tmp_path / "test_api.db"

    monkeypatch.setattr(
        database,
        "get_database_path",
        lambda: db_path,
    )
    monkeypatch.setattr(api, "ticket_queue", TicketQueue(max_size=10))

    with TestClient(api.app) as test_client:
        yield test_client


def create_ticket(client):
    """Create a ticket and return its ID."""
    response = client.post(
        "/tickets",
        json={
            "customer_id": "CUST-API-TEST",
            "subject": "Unable to access my account",
            "description": (
                "I cannot access my account after resetting my password."
            ),
        },
    )

    assert response.status_code == 202
    return response.json()["ticket_id"]


def make_ticket_pending_review(ticket_id):
    """Set up a pending-review ticket directly in the test database."""
    from datetime import datetime, timezone

    from src.customer_support.schemas import Ticket, TicketStatus

    record = database.get_ticket(ticket_id)
    assert record is not None

    ticket = Ticket.model_validate(record)
    ticket.status = TicketStatus.WAITING_FOR_APPROVAL
    ticket.requires_human_approval = True
    ticket.escalation_reason = "Low model confidence"
    ticket.updated_at = datetime.now(timezone.utc)

    database.save_ticket(ticket)


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_ticket(client):
    response = client.post(
        "/tickets",
        json={
            "customer_id": "CUST-API-001",
            "subject": "Unable to log in",
            "description": "I cannot log in after resetting my password.",
        },
    )

    assert response.status_code == 202

    ticket = response.json()
    assert ticket["ticket_id"].startswith("TKT-")
    assert ticket["customer_id"] == "CUST-API-001"
    assert ticket["status"] == "open"


def test_created_ticket_can_be_retrieved(client):
    ticket_id = create_ticket(client)

    response = client.get(f"/tickets/{ticket_id}")

    assert response.status_code == 200
    assert response.json()["ticket_id"] == ticket_id


def test_missing_ticket_returns_404(client):
    response = client.get("/tickets/TKT-MISSING")

    assert response.status_code == 404


def test_invalid_ticket_returns_422(client):
    response = client.post(
        "/tickets",
        json={
            "customer_id": "CUST-API-003",
            "subject": "Hi",
            "description": "Help",
        },
    )

    assert response.status_code == 422


def test_list_pending_review_tickets(client):
    ticket_id = create_ticket(client)
    make_ticket_pending_review(ticket_id)

    response = client.get("/tickets/pending-review")

    assert response.status_code == 200
    ticket_ids = [ticket["ticket_id"] for ticket in response.json()]
    assert ticket_id in ticket_ids


def test_approve_pending_ticket(client):
    ticket_id = create_ticket(client)
    make_ticket_pending_review(ticket_id)

    response = client.post(
        f"/tickets/{ticket_id}/review",
        json={
            "action": "approve",
            "reviewer_id": "reviewer-test-001",
            "comment": "Approved for further processing.",
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["action"] == "approve"
    assert result["status"] == "processing"
    assert result["reviewer_id"] == "reviewer-test-001"

    ticket = client.get(f"/tickets/{ticket_id}").json()
    assert ticket["status"] == "processing"
    assert ticket["requires_human_approval"] is False


def test_reject_pending_ticket(client):
    ticket_id = create_ticket(client)
    make_ticket_pending_review(ticket_id)

    response = client.post(
        f"/tickets/{ticket_id}/review",
        json={
            "action": "reject",
            "reviewer_id": "reviewer-test-002",
            "comment": "Escalate for manual investigation.",
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["action"] == "reject"
    assert result["status"] == "escalated"

    ticket = client.get(f"/tickets/{ticket_id}").json()
    assert ticket["status"] == "escalated"
    assert ticket["requires_human_approval"] is True


def test_duplicate_review_returns_409(client):
    ticket_id = create_ticket(client)
    make_ticket_pending_review(ticket_id)

    decision = {
        "action": "approve",
        "reviewer_id": "reviewer-test-003",
        "comment": "Approved.",
    }

    first_response = client.post(
        f"/tickets/{ticket_id}/review",
        json=decision,
    )
    second_response = client.post(
        f"/tickets/{ticket_id}/review",
        json=decision,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409


def test_review_missing_ticket_returns_404(client):
    response = client.post(
        "/tickets/TKT-MISSING/review",
        json={
            "action": "approve",
            "reviewer_id": "reviewer-test-004",
        },
    )

    assert response.status_code == 404


def test_review_history_is_persisted(client):
    ticket_id = create_ticket(client)
    make_ticket_pending_review(ticket_id)

    client.post(
        f"/tickets/{ticket_id}/review",
        json={
            "action": "approve",
            "reviewer_id": "reviewer-test-005",
            "comment": "Reviewed and approved.",
        },
    )

    response = client.get(f"/tickets/{ticket_id}/reviews")

    assert response.status_code == 200
    history = response.json()

    assert len(history) == 1
    assert history[0]["ticket_id"] == ticket_id
    assert history[0]["action"] == "approve"
    assert history[0]["reviewer_id"] == "reviewer-test-005"
    assert history[0]["comment"] == "Reviewed and approved."
    assert history[0]["reviewed_at"] is not None
