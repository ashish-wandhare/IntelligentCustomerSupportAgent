# Intelligent Customer Support Agent

An AI-powered customer support platform built with **Python, FastAPI, LangGraph, RAG, and Generative AI**. The system processes customer tickets, retrieves knowledge-base information, generates responses, and routes uncertain cases through a human-in-the-loop approval workflow.

## Overview

The Intelligent Customer Support Agent demonstrates an agentic AI workflow for automating customer support operations while maintaining human oversight, traceability, and controlled processing.

### Key Features

- **Ticket Management:** Create, retrieve, and track customer support tickets through REST APIs.
- **ML-Based Classification:** Predict ticket categories and priorities with confidence scores.
- **Knowledge Retrieval:** Retrieve relevant information from a Markdown-based knowledge base using TF-IDF and cosine similarity.
- **Agent Orchestration:** Use LangGraph to manage workflow execution and conditional routing.
- **Human-in-the-Loop:** Require approval for uncertain cases and support approval and rejection workflows.
- **Automated Response Generation:** Generate customer support responses using an LLM.
- **Asynchronous Processing:** Process tickets through a background worker and queue.
- **Persistent Storage:** Store tickets and review history in SQLite.
- **Monitoring Dashboard:** Visualize ticket activity and operational metrics using Streamlit.
- **Observability:** Inspect agent execution traces through LangSmith.

## Architecture

```text
Customer Ticket
      |
      v
FastAPI Ticket API
      |
      v
Ticket Queue and Background Worker
      |
      v
LangGraph Agent Workflow
      |
      v
Ticket Classification
      |
      v
Confidence-Based Routing
      |
      +----------------------+
      |                      |
      v                      v
Human Review          Knowledge Retrieval
      |                      |
      v                      v
Approval and          Response Generation
Resume Processing            |
      |                      |
      +-----------+----------+
                  |
                  v
          Ticket Resolution
                  |
          +-------+-------+
          |               |
          v               v
       SQLite          LangSmith
          |
          v
  Streamlit Dashboard
```

## Technology Stack

| Area | Technologies |
|---|---|
| Language | Python 3.12 |
| API | FastAPI, Uvicorn |
| Agent Framework | LangChain, LangGraph |
| Generative AI | Groq-hosted LLM |
| Machine Learning | scikit-learn |
| Knowledge Retrieval | TF-IDF, cosine similarity |
| Processing | Python asyncio |
| Database | SQLite |
| Dashboard | Streamlit, Plotly |
| Observability | LangSmith |
| Testing | pytest |
| Version Control | Git, GitHub |

## Project Structure

```text
IntelligentCustomerSupportAgent/
├── src/
│   └── customer_support/
│       ├── api.py
│       ├── agent_graph.py
│       ├── database.py
│       ├── schemas.py
│       ├── ticket_queue.py
│       ├── ticket_worker.py
│       ├── response_generator.py
│       ├── logging_config.py
│       └── knowledge_base/
├── data/
│   └── knowledge_base/
├── tests/
├── dashboard.py
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

*The structure above summarizes the main components; the repository itself is the source of truth for filenames and directories.*

## Getting Started

### Prerequisites

- Python 3.12
- Git
- A Groq API key for LLM-backed response generation
- A LangSmith API key for tracing (optional)

### 1. Clone the Repository

```bash
git clone https://github.com/ashish-wandhare/IntelligentCustomerSupportAgent.git
cd IntelligentCustomerSupportAgent
```

If the GitHub repository URL differs, use the actual repository URL.

### 2. Create a Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```dotenv
GROQ_API_KEY=your_groq_api_key

LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_PROJECT=intelligent-customer-support-agent-local
LANGSMITH_API_KEY=your_langsmith_api_key
```

Replace the placeholders with your own credentials. LangSmith settings are optional if tracing is disabled.

**Security:** Never commit API keys or the `.env` file to version control.

## Running the Application

Start the API from the project root:

```powershell
python -m uvicorn src.customer_support.api:app --reload
```

- API: http://127.0.0.1:8000
- Interactive API documentation: http://127.0.0.1:8000/docs

In a separate terminal, activate the virtual environment and start the dashboard:

```powershell
python -m streamlit run dashboard.py
```

- Dashboard: http://localhost:8501

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Check API health |
| `POST` | `/tickets` | Create a support ticket |
| `GET` | `/tickets` | List recent tickets |
| `GET` | `/tickets/pending-review` | List tickets awaiting review |
| `POST` | `/tickets/{ticket_id}/review` | Approve or reject a ticket |
| `GET` | `/tickets/{ticket_id}/reviews` | Retrieve review history |
| `GET` | `/tickets/{ticket_id}` | Retrieve ticket details |

Use Swagger UI at `/docs` to submit requests and inspect responses.

## Example Workflow

1. Submit a customer support ticket.
2. The API stores the ticket and places it in the processing queue.
3. The agent classifies the ticket and evaluates confidence.
4. The workflow routes uncertain cases for human approval.
5. Once approved, processing resumes and relevant knowledge is retrieved.
6. The LLM generates a customer response.
7. The final ticket state and review history are persisted.
8. LangSmith records the agent execution for inspection.

The exact execution path depends on the ticket and the configured routing rules.

## Testing

Run the automated test suite:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m pytest -v
```

**Latest verified result:** 65 tests passed.

Re-run the test suite after making changes and update this result if the outcome changes.

## Observability

LangSmith tracing has been verified for the local agent workflow. Captured traces include classification, conditional routing, human review, resumed execution, knowledge retrieval, and response generation.

LangSmith provides execution visibility; automated tests and application logs provide complementary validation.

## Safety and Design Principles

- Use synthetic tickets and simulated business workflows during development.
- Route uncertain cases to human review.
- Restrict automatic execution to explicitly authorized, low-risk actions.
- Preserve ticket history and review records.
- Evaluate retrieval relevance and response quality.
- Keep credentials out of source control.
- Prefer lightweight, cost-conscious infrastructure.
- Avoid requiring paid infrastructure for the local demonstration.

## Current Status

The core ticket-processing workflow, human-review process, dashboard, and LangSmith tracing have been exercised. The latest full test run passed all 65 tests.

Remaining finalization work includes reviewing retrieval relevance, verifying setup instructions against the repository, and preparing a reproducible demonstration.

## Future Improvements

- Improve semantic retrieval and relevance evaluation.
- Expand automated evaluation of generated responses.
- Strengthen error handling and retry policies.
- Add further operational metrics and failure-scenario tests.

## License

Add a license section if the repository has a selected open-source license.

---

**Project:** Intelligent Customer Support Agent  
**Language:** Python  
**Primary frameworks:** FastAPI, LangGraph, Streamlit  
**Observability:** LangSmith

## Snapshots
<img width="1398" height="881" alt="ICSA_LangGraph_Trace_runs" src="https://github.com/user-attachments/assets/fb0fcd3c-1fc6-4fa6-acef-91f69ea3998b" />
