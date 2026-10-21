
import asyncio
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from src.customer_support.knowledge_base.ticket_knowledge import (
    retrieve_ticket_knowledge,
)
from src.customer_support.models.ticket_classifier import predict_ticket
from src.customer_support.response_generator import (
    generate_customer_response,
)
from src.customer_support.schemas import (
    TicketCategory,
    TicketPriority,
)

MIN_CONFIDENCE = 0.60

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but",
    "by", "can", "could", "did", "do", "does", "for", "from",
    "had", "has", "have", "how", "i", "in", "is", "it", "me",
    "my", "of", "on", "or", "our", "please", "the", "their",
    "this", "to", "was", "we", "were", "what", "when", "where",
    "which", "who", "why", "with", "would", "you", "your",
}


class AgentState(TypedDict, total=False):
    ticket_id: str
    subject: str
    description: str
    category: str
    priority: str
    category_confidence: float
    priority_confidence: float
    requires_human_approval: bool
    escalation_reason: str | None
    knowledge: list[dict[str, Any]]
    customer_response: str
    route: str
    error: str | None
    resume_approved: bool


def classify_ticket(state: AgentState) -> dict:
    """Classify a new ticket and decide whether human approval is needed."""
    prediction = predict_ticket(state["subject"], state["description"])

    category = TicketCategory(str(prediction["category"]))
    priority = TicketPriority(str(prediction["priority"]).lower())

    category_confidence = float(prediction["category_confidence"])
    priority_confidence = float(prediction["priority_confidence"])

    reasons = []

    if priority == TicketPriority.CRITICAL:
        reasons.append("Critical priority predicted")

    if category_confidence < MIN_CONFIDENCE:
        reasons.append("Low category confidence")

    if priority_confidence < MIN_CONFIDENCE:
        reasons.append("Low priority confidence")

    requires_approval = bool(reasons)

    return {
        "category": category.value,
        "priority": priority.value,
        "category_confidence": category_confidence,
        "priority_confidence": priority_confidence,
        "requires_human_approval": requires_approval,
        "escalation_reason": "; ".join(reasons) if reasons else None,
        "route": (
            "human_review"
            if requires_approval
            else "retrieve_knowledge"
        ),
    }


def route_start(state: AgentState) -> str:
    """Resume approved tickets without running classification again."""
    if state.get("resume_approved", False):
        return "retrieve_knowledge"

    return "classify_ticket"


def route_after_classification(state: AgentState) -> str:
    """Route low-confidence or critical tickets to human review."""
    if state["requires_human_approval"]:
        return "human_review"

    return "retrieve_knowledge"


def human_review(state: AgentState) -> dict:
    """Stop automated processing while human approval is pending."""
    return {
        "route": "human_review",
        "knowledge": [],
        "customer_response": "",
    }


def retrieve_knowledge(state: AgentState) -> dict:
    """Retrieve relevant knowledge-base passages for the ticket."""
    passages = retrieve_ticket_knowledge(
        state["subject"],
        state["description"],
    )

    return {
        "knowledge": passages,
        "route": "check_evidence",
    }


def _meaningful_words(text: str) -> set[str]:
    """Extract meaningful words for a lightweight lexical evidence check."""
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return {word for word in words if word not in STOP_WORDS}


def check_evidence(state: AgentState) -> dict:
    """
    Check whether retrieved passages share meaningful terms with the ticket.

    This lexical baseline does not guarantee that a passage fully answers
    the customer's question.
    """
    knowledge = state.get("knowledge", [])
    ticket_text = f"{state['subject']} {state['description']}"
    ticket_words = _meaningful_words(ticket_text)

    matching_passages = []

    for passage in knowledge:
        # Support both the real retriever's "text" field and legacy
        # test fixtures that use "content".
        passage_text = str(
            passage.get("text") or passage.get("content") or ""
        ).strip()

        if not passage_text:
            continue

        passage_words = _meaningful_words(passage_text)

        if ticket_words.intersection(passage_words):
            matching_passages.append(passage)

    if not matching_passages:
        return {
            "knowledge": [],
            "route": "human_review",
            "requires_human_approval": True,
            "escalation_reason": (
                "Retrieved knowledge does not contain sufficient "
                "matching terms; human review is required."
            ),
        }

    return {
        "knowledge": matching_passages,
        "route": "generate_response",
    }


def route_after_evidence(state: AgentState) -> str:
    """Route tickets based on the evidence check result."""
    if state.get("route") == "human_review":
        return "human_review"

    return "generate_response"


def generate_response(state: AgentState) -> dict:
    """Generate a customer-facing response from retrieved passages."""
    response = generate_customer_response(
        subject=state["subject"],
        knowledge=state.get("knowledge", []),
    )

    return {
        "customer_response": response,
        "route": "continue_processing",
    }


def build_agent_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classify_ticket", classify_ticket)
    graph.add_node("human_review", human_review)
    graph.add_node("retrieve_knowledge", retrieve_knowledge)
    graph.add_node("check_evidence", check_evidence)
    graph.add_node("generate_response", generate_response)

    # Choose the entry point based on whether the ticket was approved.
    graph.add_conditional_edges(
        START,
        route_start,
        {
            "classify_ticket": "classify_ticket",
            "retrieve_knowledge": "retrieve_knowledge",
        },
    )

    # New tickets go to human review or knowledge retrieval.
    graph.add_conditional_edges(
        "classify_ticket",
        route_after_classification,
        {
            "human_review": "human_review",
            "retrieve_knowledge": "retrieve_knowledge",
        },
    )

    graph.add_edge("human_review", END)
    graph.add_edge("retrieve_knowledge", "check_evidence")

    graph.add_conditional_edges(
        "check_evidence",
        route_after_evidence,
        {
            "human_review": "human_review",
            "generate_response": "generate_response",
        },
    )

    graph.add_edge("generate_response", END)

    return graph.compile()


agent_graph = build_agent_graph()


async def run_agent_graph(state: AgentState) -> dict:
    """Run the graph without blocking the asynchronous event loop."""
    return await asyncio.to_thread(agent_graph.invoke, state)
