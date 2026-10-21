
from unittest.mock import patch

import src.customer_support.knowledge_base.ticket_knowledge as ticket_knowledge


def test_retrieves_knowledge_for_ticket():
    fake_results = [
        {
            "source": "billing_support.md",
            "section": "1. Payment Failed",
            "text": "Check the payment status.",
            "score": 0.47,
        }
    ]

    ticket_knowledge._retriever = None

    with patch(
        "src.customer_support.knowledge_base.ticket_knowledge.KnowledgeBaseRetriever"
    ) as mock_retriever:
        mock_retriever.return_value.search.return_value = fake_results

        results = ticket_knowledge.retrieve_ticket_knowledge(
            subject="Payment failed",
            description="The customer cannot complete a payment.",
            top_k=3,
        )

    assert results == fake_results
    mock_retriever.return_value.search.assert_called_once_with(
        query="Payment failed\nThe customer cannot complete a payment.",
        top_k=3,
    )


def test_retrieval_uses_default_top_k():
    ticket_knowledge._retriever = None

    with patch(
        "src.customer_support.knowledge_base.ticket_knowledge.KnowledgeBaseRetriever"
    ) as mock_retriever:
        mock_retriever.return_value.search.return_value = []

        results = ticket_knowledge.retrieve_ticket_knowledge(
            subject="Login problem",
            description="The customer cannot sign in.",
        )

    assert results == []
    mock_retriever.return_value.search.assert_called_once_with(
        query="Login problem\nThe customer cannot sign in.",
        top_k=3,
    )


def teardown_function():
    """Prevent cached retrievers from leaking between tests."""
    ticket_knowledge._retriever = None
