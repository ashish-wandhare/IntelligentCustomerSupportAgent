
from src.customer_support.knowledge_base.retriever import (
    KnowledgeBaseRetriever,
)

_retriever: KnowledgeBaseRetriever | None = None


def retrieve_ticket_knowledge(
    subject: str,
    description: str,
    top_k: int = 3,
) -> list[dict]:
    """
    Retrieve support passages relevant to a ticket.

    Returns source, section, text, and similarity score for each result.
    """
    global _retriever

    query = f"{subject.strip()}\n{description.strip()}"

    if _retriever is None:
        _retriever = KnowledgeBaseRetriever()

    return _retriever.search(
        query=query,
        top_k=top_k,
    )
