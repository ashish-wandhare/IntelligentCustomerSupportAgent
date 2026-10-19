
import json

import pytest

from src.customer_support.synthetic_data import (
    generate_tickets,
    save_tickets,
)


def test_generate_requested_number_of_tickets():
    tickets = generate_tickets(count=25, seed=42)

    assert len(tickets) == 25


def test_generation_is_reproducible():
    first = generate_tickets(count=20, seed=42)
    second = generate_tickets(count=20, seed=42)

    assert first == second


def test_ticket_ids_are_unique():
    tickets = generate_tickets(count=100, seed=42)
    ticket_ids = [ticket["ticket_id"] for ticket in tickets]

    assert len(ticket_ids) == len(set(ticket_ids))


def test_generated_tickets_have_required_fields():
    tickets = generate_tickets(count=10, seed=42)

    required_fields = {
        "ticket_id",
        "customer_id",
        "subject",
        "description",
        "category",
        "priority",
        "status",
        "requires_human_approval",
        "expected_action",
    }

    for ticket in tickets:
        assert required_fields.issubset(ticket.keys())


def test_invalid_count_is_rejected():
    with pytest.raises(ValueError):
        generate_tickets(count=0)


def test_save_tickets_creates_jsonl_file(tmp_path):
    tickets = generate_tickets(count=3, seed=42)
    output_path = tmp_path / "synthetic" / "tickets.jsonl"

    saved_path = save_tickets(tickets, output_path)

    assert saved_path.exists()

    lines = saved_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3

    loaded_tickets = [json.loads(line) for line in lines]
    assert loaded_tickets == tickets
