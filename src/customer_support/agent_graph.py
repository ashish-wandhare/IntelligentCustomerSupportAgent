
import asyncio
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from src.customer_support.knowledge_base.ticket_knowledge import (
    retrieve_ticket_knowledge,
)
from src.customer_support.models.ticket_classifier import predict_ticket
from src.customer_support.schemas import (
    TicketCategory,
    TicketPriority,
)

MIN_CONFIDENCE = 0.60


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
    }


def retrieve_knowledge(state: AgentState) -> dict:
    """Retrieve relevant knowledge-base passages for the ticket."""
    passages = retrieve_ticket_knowledge(
        state["subject"],
        state["description"],
    )

    return {
        "knowledge": passages,
        "route": "continue_processing",
    }


def build_agent_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classify_ticket", classify_ticket)
    graph.add_node("human_review", human_review)
    graph.add_node("retrieve_knowledge", retrieve_knowledge)

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
    graph.add_edge("retrieve_knowledge", END)

    return graph.compile()


agent_graph = build_agent_graph()


async def run_agent_graph(state: AgentState) -> dict:
    """Run the graph without blocking the asynchronous event loop."""
    return await asyncio.to_thread(agent_graph.invoke, state)
