
from unittest.mock import patch

import pytest

from src.customer_support.agent_graph import agent_graph


@pytest.mark.parametrize(
    ("priority", "category_confidence", "priority_confidence", "expected_route"),
    [
        ("critical", 0.95, 0.95, "human_review"),
        ("high", 0.95, 0.95, "continue_processing"),
        ("medium", 0.95, 0.95, "continue_processing"),
        ("low", 0.95, 0.95, "continue_processing"),
        ("high", 0.40, 0.95, "human_review"),
        ("high", 0.95, 0.40, "human_review"),
    ],
)
def test_agent_graph_routes_classified_tickets(
    priority,
    category_confidence,
    priority_confidence,
    expected_route,
):
    prediction = {
        "category": "technical",
        "priority": priority,
        "category_confidence": category_confidence,
        "priority_confidence": priority_confidence,
    }

    with (
        patch(
            "src.customer_support.agent_graph.predict_ticket",
            return_value=prediction,
        ),
        patch(
            "src.customer_support.agent_graph.retrieve_ticket_knowledge",
            return_value=[
                {
                    "source": "technical_support.md",
                    "section": "Troubleshooting",
                    "score": 0.85,
                    "content": "Check the service logs.",
                }
            ],
        ) as mock_retrieve,
    ):
        result = agent_graph.invoke(
            {
                "ticket_id": "TEST-001",
                "subject": "Application connection failed",
                "description": "The application cannot connect to the service.",
            }
        )

    if expected_route == "human_review":
        assert result["route"] == "human_review"
        assert result["requires_human_approval"] is True
        assert result["knowledge"] == []
        mock_retrieve.assert_not_called()
    else:
        assert result["route"] == "continue_processing"
        assert result["requires_human_approval"] is False
        assert len(result["knowledge"]) == 1
        mock_retrieve.assert_called_once()


def test_critical_priority_is_case_insensitive():
    prediction = {
        "category": "technical",
        "priority": "CRITICAL",
        "category_confidence": 0.95,
        "priority_confidence": 0.95,
    }

    with patch(
        "src.customer_support.agent_graph.predict_ticket",
        return_value=prediction,
    ):
        result = agent_graph.invoke(
            {
                "ticket_id": "TEST-002",
                "subject": "Production outage",
                "description": "The production service is unavailable.",
            }
        )

    assert result["priority"] == "critical"
    assert result["route"] == "human_review"
    assert result["requires_human_approval"] is True


@pytest.mark.asyncio
async def test_approved_ticket_skips_classification():
    from unittest.mock import patch

    from src.customer_support.agent_graph import run_agent_graph

    with (
        patch(
            "src.customer_support.agent_graph.predict_ticket"
        ) as mock_predict,
        patch(
            "src.customer_support.agent_graph.retrieve_ticket_knowledge",
            return_value=[{"content": "Account access troubleshooting"}],
        ) as mock_retrieve,
    ):
        result = await run_agent_graph(
            {
                "ticket_id": "TICKET-APPROVED-001",
                "subject": "Account access issue",
                "description": "My account is locked.",
                "category": "account",
                "priority": "high",
                "category_confidence": 0.95,
                "priority_confidence": 0.90,
                "requires_human_approval": False,
                "resume_approved": True,
            }
        )

    mock_predict.assert_not_called()
    mock_retrieve.assert_called_once_with(
        "Account access issue",
        "My account is locked.",
    )

    assert result["route"] == "continue_processing"
    assert result["knowledge"] == [
        {"content": "Account access troubleshooting"}
    ]


from src.customer_support.agent_graph import check_evidence


def test_check_evidence_rejects_unrelated_passages():
    state = {
        "subject": "Delete my account",
        "description": "I want to permanently delete my account.",
        "knowledge": [
            {
                "source": "billing_support.md",
                "section": "Payments",
                "text": "You can update your payment method and billing details.",
            }
        ],
    }

    result = check_evidence(state)

    assert result["knowledge"] == []
    assert result["route"] == "human_review"
    assert result["requires_human_approval"] is True


def test_check_evidence_rejects_empty_knowledge():
    state = {
        "subject": "Application connection failure",
        "description": "My application cannot connect to the service.",
        "knowledge": [],
    }

    result = check_evidence(state)

    assert result["knowledge"] == []
    assert result["route"] == "human_review"
    assert result["requires_human_approval"] is True


def test_check_evidence_accepts_relevant_passage():
    state = {
        "subject": "Password reset",
        "description": "I cannot reset my password and need account access.",
        "knowledge": [
            {
                "source": "account_access.md",
                "section": "Password Reset",
                "text": (
                    "To reset your password, use the password reset link "
                    "and follow the account verification steps."
                ),
            }
        ],
    }

    result = check_evidence(state)

    assert len(result["knowledge"]) == 1
    assert result["route"] == "generate_response"
