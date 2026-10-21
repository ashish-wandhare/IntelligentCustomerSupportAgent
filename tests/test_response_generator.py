
from unittest.mock import MagicMock, patch

from src.customer_support.response_generator import (
    generate_customer_response,
)


@patch("src.customer_support.response_generator.ChatGroq")
def test_generates_response_with_knowledge_and_references(mock_chat_groq):
    knowledge = [
        {
            "text": "Reset your password using the Forgot Password link.",
            "source": "account_access.md",
            "section": "Password Reset",
            "score": 0.85,
        },
        {
            "text": "Check your registered email for the reset link.",
            "source": "account_access.md",
            "section": "Email Verification",
            "score": 0.72,
        },
    ]

    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = (
        "Unable to log in? Please use the Forgot Password link "
        "and check your registered email for the reset instructions."
    )
    mock_chat_groq.return_value = mock_llm

    with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}):
        response = generate_customer_response(
            subject="Unable to log in",
            knowledge=knowledge,
        )

    assert "Unable to log in" in response
    assert "Forgot Password link" in response
    assert "registered email" in response
    assert "Reference articles:" in response
    assert "account_access.md — Password Reset" in response
    assert "account_access.md — Email Verification" in response

    mock_chat_groq.assert_called_once()
    mock_llm.invoke.assert_called_once()


def test_empty_knowledge_requests_further_review():
    response = generate_customer_response(
        subject="Payment issue",
        knowledge=[],
    )

    assert "Payment issue" in response
    assert "further review" in response
    assert "knowledge base" in response


def test_empty_passages_do_not_create_empty_recommendations():
    knowledge = [
        {
            "text": "   ",
            "source": "billing_support.md",
            "section": "Billing",
            "score": 0.0,
        }
    ]

    response = generate_customer_response(
        subject="Billing question",
        knowledge=knowledge,
    )

    assert "further review" in response
    assert "Reference articles:" not in response


@patch("src.customer_support.response_generator.ChatGroq")
def test_duplicate_references_are_listed_only_once(mock_chat_groq):
    knowledge = [
        {
            "text": "Check your account settings.",
            "source": "account_access.md",
            "section": "Account Access",
        },
        {
            "text": "Verify your registered email.",
            "source": "account_access.md",
            "section": "Account Access",
        },
    ]

    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = (
        "Please check your account settings and verify your registered email."
    )
    mock_chat_groq.return_value = mock_llm

    with patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}):
        response = generate_customer_response(
            subject="Account access",
            knowledge=knowledge,
        )

    assert response.count("- account_access.md — Account Access") == 1
