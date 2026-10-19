
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
        {
            "subject": "Invoice amount looks incorrect",
            "description": "The amount on my latest invoice does not match the price I expected to pay.",
            "priority": "medium",
            "expected_action": "investigate_billing",
        },
        {
            "subject": "Subscription renewal question",
            "description": "I want to understand when my subscription renews and what amount will be charged.",
            "priority": "low",
            "expected_action": "provide_information",
        },
        {
            "subject": "Payment failed but money was deducted",
            "description": "My payment failed on the website, but the amount appears to have been deducted from my bank account.",
            "priority": "high",
            "expected_action": "investigate_billing",
        },
        {
            "subject": "Request a copy of my invoice",
            "description": "I need a copy of the invoice for my most recent purchase.",
            "priority": "low",
            "expected_action": "provide_information",
        },
        {
            "subject": "Unexpected subscription renewal",
            "description": "My subscription renewed unexpectedly and I would like the charge reviewed.",
            "priority": "high",
            "expected_action": "investigate_billing",
        },
        {
            "subject": "Refund status is unclear",
            "description": "I received a refund confirmation but cannot determine when the funds will arrive.",
            "priority": "medium",
            "expected_action": "check_refund_status",
        },
        {
            "subject": "Dispute a billing transaction",
            "description": "There is a transaction on my bill that I do not recognize. Please review it.",
            "priority": "high",
            "expected_action": "escalate",
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
        {
            "subject": "File upload keeps failing",
            "description": "My file uploads fail repeatedly even though the file is within the size limit.",
            "priority": "medium",
            "expected_action": "troubleshoot",
        },
        {
            "subject": "Dashboard displays an error",
            "description": "The dashboard displays an error instead of showing my account information.",
            "priority": "high",
            "expected_action": "troubleshoot",
        },
        {
            "subject": "Notifications are not arriving",
            "description": "I have enabled notifications but no alerts are reaching my device.",
            "priority": "low",
            "expected_action": "troubleshoot",
        },
        {
            "subject": "Integration stopped working",
            "description": "An integration that worked yesterday now fails to synchronize data.",
            "priority": "high",
            "expected_action": "troubleshoot",
        },
        {
            "subject": "Multiple users cannot access service",
            "description": "Several users at our organization cannot access the service, affecting business operations.",
            "priority": "critical",
            "expected_action": "escalate",
        },
        {
            "subject": "Search results are incorrect",
            "description": "Searching for known records returns incomplete or unexpected results.",
            "priority": "medium",
            "expected_action": "troubleshoot",
        },
        {
            "subject": "Data synchronization outage",
            "description": "Important business data is no longer synchronizing between connected systems.",
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
        {
            "subject": "Account temporarily locked",
            "description": "My account became locked after several unsuccessful login attempts.",
            "priority": "high",
            "expected_action": "verify_identity",
        },
        {
            "subject": "Update profile information",
            "description": "I need to update the contact information saved in my profile.",
            "priority": "low",
            "expected_action": "verify_identity",
        },
        {
            "subject": "Password reset link expired",
            "description": "The password reset link expired before I could complete the reset process.",
            "priority": "medium",
            "expected_action": "troubleshoot",
        },
        {
            "subject": "Request to close my account",
            "description": "I would like guidance on closing my account and understanding the next steps.",
            "priority": "medium",
            "expected_action": "verify_identity",
        },
        {
            "subject": "Unexpected change to account details",
            "description": "Some account details appear to have changed without my knowledge.",
            "priority": "critical",
            "expected_action": "escalate",
        },
        {
            "subject": "Multi-factor authentication problem",
            "description": "I cannot complete sign-in because my authentication code is not being accepted.",
            "priority": "high",
            "expected_action": "troubleshoot",
        },
        {
            "subject": "Request access to an existing account",
            "description": "I need help restoring access to an account I previously used.",
            "priority": "medium",
            "expected_action": "verify_identity",
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
        {
            "subject": "How do I contact support?",
            "description": "Please explain how I can contact the appropriate support team for assistance.",
            "priority": "low",
            "expected_action": "provide_information",
        },
        {
            "subject": "Request an update on an existing case",
            "description": "I would like an update on the progress of my previously submitted support request.",
            "priority": "medium",
            "expected_action": "provide_information",
        },
        {
            "subject": "Request accessibility information",
            "description": "I would like to know which accessibility features are available in the service.",
            "priority": "low",
            "expected_action": "provide_information",
        },
        {
            "subject": "Service quality complaint",
            "description": "The service has not met my expectations and I would like my concerns reviewed.",
            "priority": "high",
            "expected_action": "escalate",
        },
        {
            "subject": "Question about service availability",
            "description": "I would like to know the usual service availability and maintenance schedule.",
            "priority": "low",
            "expected_action": "provide_information",
        },
        {
            "subject": "Request to speak to a representative",
            "description": "I would prefer to discuss my unresolved concern with a human support representative.",
            "priority": "medium",
            "expected_action": "escalate",
        },
        {
            "subject": "Urgent business service concern",
            "description": "An unresolved service issue is affecting an important business activity and needs prompt review.",
            "priority": "critical",
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
