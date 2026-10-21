import pytest

from src.customer_support.knowledge_base.retriever import (
    KnowledgeBaseRetriever,
)


@pytest.fixture(scope="module")
def retriever():
    return KnowledgeBaseRetriever()


@pytest.mark.parametrize(
    ("query", "expected_source"),
    [
        (
            "I forgot my password and cannot log in",
            "account_access.md",
        ),
        (
            "My payment failed",
            "billing_support.md",
        ),
        (
            "The application is running very slowly",
            "technical_support.md",
        ),
        (
            "I want to update my customer profile",
            "general_support.md",
        ),
    ],
)
def test_retrieves_expected_document(retriever, query, expected_source):
    results = retriever.search(query, top_k=1)

    assert len(results) == 1
    assert results[0]["source"] == expected_source
    assert results[0]["score"] > 0


def test_empty_query_is_rejected(retriever):
    with pytest.raises(ValueError, match="query must not be empty"):
        retriever.search("   ")


def test_invalid_top_k_is_rejected(retriever):
    with pytest.raises(ValueError, match="top_k must be at least 1"):
        retriever.search("payment failed", top_k=0)


def test_results_include_source_section_text_and_score(retriever):
    results = retriever.search("password reset", top_k=1)

    assert results
    result = results[0]

    assert result["source"]
    assert result["section"]
    assert result["text"]
    assert 0 <= result["score"] <= 1
    

def test_unrelated_query_returns_no_results(retriever):
    results = retriever.search(
        "What is the weather on Mars?",
        top_k=3,
    )

    assert results == []
