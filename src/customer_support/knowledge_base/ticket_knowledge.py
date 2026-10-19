from src.customer_support.knowledge_base.retriever import (
    KnowledgeBaseRetriever,
)


def retrieve_ticket_knowledge(
    subject: str,
    description: str,
    top_k: int = 3,
) -> list[dict]:
    """
    Retrieve support passages relevant to a ticket.

    Returns source, section, text, and similarity score for each result.
    """
    query = f"{subject.strip()}\n{description.strip()}"

    retriever = KnowledgeBaseRetriever()

    return retriever.search(
        query=query,
        top_k=top_k,
    )