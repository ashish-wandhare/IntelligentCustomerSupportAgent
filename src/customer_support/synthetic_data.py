
import json
import random
from pathlib import Path


CATEGORIES = {
    "billing": [
        {
            "subject": "Unexpected charge on my account",
            "description": "I noticed an unexpected charge on my latest invoice and need help understanding it.",
            "priority": "medium",
            "expected_action": "investigate_billing",
        },
        {
            "subject": "Refund has not arrived",
            "description": "My refund was approved, but the money has not appeared in my account.",
            "priority": "medium",
            "expected_action": "check_refund_status",
        },
        {
            "subject": "Duplicate payment charged",
            "description": "I appear to have been charged twice for the same order. Please investigate.",
            "priority": "high",
            "expected_action": "investigate_billing",
        },
    ],
    "technical": [
        {
            "subject": "Application crashes on startup",
            "description": "The application closes unexpectedly every time I try to open it.",
            "priority": "high",
            "expected_action": "troubleshoot",
        },
        {
            "subject": "Page is loading slowly",
            "description": "Pages take a long time to load, even when my internet connection is stable.",
            "priority": "medium",
            "expected_action": "troubleshoot",
        },
        {
            "subject": "Service unavailable",
            "description": "I cannot access the service and receive an error message on every attempt.",
            "priority": "critical",
            "expected_action": "escalate",
        },
    ],
    "account": [
        {
            "subject": "Unable to log in",
            "description": "I cannot log in after resetting my password.",
            "priority": "high",
            "expected_action": "troubleshoot",
        },
        {
            "subject": "Update account email",
            "description": "I want to change the email address associated with my account.",
            "priority": "low",
            "expected_action": "verify_identity",
        },
        {
            "subject": "Possible unauthorized account access",
            "description": "I noticed activity I do not recognize and am concerned someone accessed my account.",
            "priority": "critical",
            "expected_action": "escalate",
        },
    ],
    "general": [
        {
            "subject": "Question about service features",
            "description": "Could you explain which features are included in my current service plan?",
            "priority": "low",
            "expected_action": "provide_information",
        },
        {
            "subject": "Request for product information",
            "description": "I would like more information about the available product options.",
            "priority": "low",
            "expected_action": "provide_information",
        },
        {
            "subject": "Complaint about repeated service issues",
            "description": "I have experienced repeated problems and would like a support representative to review them.",
            "priority": "high",
            "expected_action": "escalate",
        },
    ],
}


def generate_tickets(count: int = 100, seed: int = 42) -> list[dict]:
    """Generate reproducible synthetic customer-support tickets."""
    if count < 1:
        raise ValueError("count must be at least 1.")

    rng = random.Random(seed)
    categories = list(CATEGORIES)
    tickets = []

    for index in range(1, count + 1):
        category = rng.choice(categories)
        scenario = rng.choice(CATEGORIES[category])

        requires_approval = scenario["expected_action"] in {
            "verify_identity",
            "escalate",
        }

        ticket = {
            "ticket_id": f"SYN-{index:06d}",
            "customer_id": f"CUST-{rng.randint(1, 50):03d}",
            "subject": scenario["subject"],
            "description": scenario["description"],
            "category": category,
            "priority": scenario["priority"],
            "status": "open",
            "requires_human_approval": requires_approval,
            "expected_action": scenario["expected_action"],
        }
        tickets.append(ticket)

    return tickets


def save_tickets(
    tickets: list[dict],
    output_path: Path | None = None,
) -> Path:
    """Save tickets as JSON Lines (one JSON object per line)."""
    if output_path is None:
        output_path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "synthetic"
            / "tickets.jsonl"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        for ticket in tickets:
            file.write(json.dumps(ticket, ensure_ascii=False) + "\n")

    return output_path


if __name__ == "__main__":
    generated_tickets = generate_tickets(count=100, seed=42)
    saved_path = save_tickets(generated_tickets)

    print(f"Generated {len(generated_tickets)} synthetic tickets.")
    print(f"Saved to: {saved_path}")
