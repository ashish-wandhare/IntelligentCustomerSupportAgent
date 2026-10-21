
import logging
import os
from typing import Any

from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)

MODEL_NAME = "openai/gpt-oss-20b"


def generate_customer_response(
    subject: str,
    knowledge: list[dict[str, Any]],
) -> str:
    """Generate a customer-facing response using retrieved knowledge and Groq."""
    clean_subject = subject.strip()

    usable_passages = []
    sources = []

    for passage in knowledge:
        text = str(passage.get("text", "")).strip()

        if not text:
            continue

        usable_passages.append(text)

        source = str(passage.get("source", "")).strip()
        section = str(passage.get("section", "")).strip()

        if source:
            reference = f"{source} — {section}" if section else source
            sources.append(reference)

    if not usable_passages:
        return (
            f"Thank you for contacting support about: {clean_subject}.\n\n"
            "No sufficiently relevant, usable guidance was found in the "
            "knowledge base. Your request needs further review by our "
            "support team."
        )

    if not os.environ.get("GROQ_API_KEY"):
        logger.error("GROQ_API_KEY is not configured.")
        return (
            f"Thank you for contacting support about: {clean_subject}.\n\n"
            "We could not generate a response automatically because the "
            "AI service is not configured. Your request needs further "
            "review by our support team."
        )

    unique_sources = list(dict.fromkeys(sources))

    knowledge_context = "\n\n".join(
        f"Knowledge passage {index}:\n{text}"
        for index, text in enumerate(usable_passages, start=1)
    )

    prompt = f"""
You are a professional customer support assistant.

Write a concise, clear, polite response to the customer's issue.

Customer subject:
{clean_subject}

Retrieved knowledge-base passages:
{knowledge_context}

Instructions:
- Use the retrieved passages as your source of support guidance.
- Give only the steps relevant to the customer's issue.
- Do not invent policies, procedures, links, or facts.
- Do not repeat headings or unrelated passages.
- Do not include internal reasoning or classification scores.
- If the passages do not sufficiently answer the issue, say that
  the support team needs to review it.
- Use simple language and numbered steps when useful.
- Do not claim the issue has been fixed.
- Return only the customer-facing response.
""".strip()

    try:
        llm = ChatGroq(
            model=MODEL_NAME,
            temperature=0,
            max_tokens=500,
            max_retries=1,
        )

        result = llm.invoke(prompt)
        customer_message = str(result.content).strip()

        if not customer_message:
            raise ValueError("Groq returned an empty response.")

    except Exception:
        logger.exception("Groq customer-response generation failed.")
        return (
            f"Thank you for contacting support about: {clean_subject}.\n\n"
            "We could not generate a customer response automatically. "
            "Your request needs further review by our support team."
        )

    if unique_sources:
        customer_message += (
            "\n\nReference articles:\n"
            + "\n".join(f"- {source}" for source in unique_sources)
        )

    return customer_message
