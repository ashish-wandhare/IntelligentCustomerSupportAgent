from unittest.mock import patch

from src.customer_support.knowledge_base.ticket_knowledge import (
    retrieve_ticket_knowledge,
)


def test_retrieves_knowledge_for_ticket():
    fake_results = [
        {
            "source": "billing_support.md",
            "section": "1. Payment Failed",
            "text": "Check the payment status.",
            "score": 0.47,
        }
    ]

    with patch(
        "src.customer_support.knowledge_base.ticket_knowledge.KnowledgeBaseRetriever"
    ) as mock_retriever:
        mock_retriever.return_value.search.return_value = fake_results

        results = retrieve_ticket_knowledge(
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
    with patch(
        "src.customer_support.knowledge_base.ticket_knowledge.KnowledgeBaseRetriever"
    ) as mock_retriever:
        mock_retriever.return_value.search.return_value = []

        results = retrieve_ticket_knowledge(
            subject="Login problem",
            description="The customer cannot sign in.",
        )

    assert results == []
    mock_retriever.return_value.search.assert_called_once_with(
        query="Login problem\nThe customer cannot sign in.",
        top_k=3,
    )