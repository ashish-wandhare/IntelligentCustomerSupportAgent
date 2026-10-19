# Intelligent Customer Support Agent

## Project Objective

An enterprise-style customer support platform combining Generative AI,
Agentic AI, Retrieval-Augmented Generation (RAG), and controlled automation.

The system processes customer tickets, retrieves relevant knowledge,
selects appropriate actions, validates results, and escalates sensitive
or unresolved cases to a human.

This project is separate from the existing PDF-based GenAI Chatbot project.

## Finalized Architecture

1. Synthetic ticket generator
2. Real-time ticket simulator
3. FastAPI backend and lightweight ticket queue
4. ML/NLP ticket classification and priority detection
5. RAG knowledge engine
6. LangGraph agent with tool calling and conditional routing
7. Validation, controlled retries, and human approval
8. SQLite database and audit history
9. Streamlit monitoring dashboard
10. Automated testing and GenAI evaluation

## Expected Workflow

Customer ticket -> Classification -> Knowledge retrieval -> Agent decision
-> Tool execution -> Result validation -> Automatic low-risk action
or human escalation.

## Technology Stack

- Python 3.12
- Cloud LLM API with a verified suitable free tier
- LangChain and LangGraph
- Sentence Transformers
- ChromaDB
- FastAPI
- Python asyncio
- SQLite
- Streamlit
- pytest
- LangSmith, if its free tier meets project needs
- Python logging and lightweight metrics
- Git and GitHub

## Safety and Operating Principles

- Use synthetic tickets and simulated business tools initially.
- Execute only authorized, low-risk actions automatically.
- Require human approval for sensitive actions, such as refunds or account deletion.
- Escalate critical, unresolved, or uncertain cases.
- Maintain ticket history and audit records.
- Do not require paid APIs or services.
- Do not use Ollama or download local LLM models.
- Keep the initial implementation lightweight; Kafka and Kubernetes are excluded.

## Development Roadmap

1. Repository, environment, dependencies, configuration, and ticket schema.
2. Ticket simulator, queue, FastAPI endpoints, SQLite persistence, and status tracking.
3. ML/NLP classification, priority prediction, and evaluation.
4. Knowledge ingestion, embeddings, ChromaDB retrieval, and grounded answers.
5. LangGraph agent, tools, routing, validation, retries, and human approval.
6. Automated tests, GenAI evaluation, logging, tracing, monitoring, and metrics.
7. Streamlit dashboard, security hardening, documentation, and end-to-end demonstration.

## Definition of Completion

The application will continuously accept and process tickets, retrieve supporting
knowledge, execute authorized tools, request approval or escalate when required,
persist outcomes, and expose processing activity and quality metrics through a dashboard.

The repository will include setup instructions, architecture documentation,
automated tests, actual evaluation results, and a reproducible demonstration.

## Current Development Status

Phase 1: Initial project structure, Python 3.12 virtual environment,
configuration, and ticket schema.

Implementation is proceeding incrementally. Later phases will be marked complete
only after their functionality has been implemented and tested.
