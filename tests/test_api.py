
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
    create_response = client.post(
        "/tickets",
        json={
            "customer_id": "CUST-API-002",
            "subject": "Payment question",
            "description": "I need help understanding my latest invoice.",
        },
    )

    ticket_id = create_response.json()["ticket_id"]
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
