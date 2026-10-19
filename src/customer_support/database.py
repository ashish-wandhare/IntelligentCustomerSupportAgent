
import sqlite3
from pathlib import Path

from src.customer_support.config import settings
from src.customer_support.schemas import Ticket


def get_database_path() -> Path:
    """Resolve the SQLite database path from the configured URL."""
    prefix = "sqlite:///"

    if not settings.database_url.startswith(prefix):
        raise ValueError("Only SQLite database URLs are supported.")

    configured_path = settings.database_url[len(prefix):]
    path = Path(configured_path)

    if not path.is_absolute():
        path = Path.cwd() / path

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection() -> sqlite3.Connection:
    """Create a SQLite connection with named-row access."""
    connection = sqlite3.connect(get_database_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    """Create the tickets table if it does not already exist."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolution TEXT,
                requires_human_approval INTEGER NOT NULL DEFAULT 0,
                escalation_reason TEXT
            )
            """
        )


def save_ticket(ticket: Ticket) -> None:
    """Insert a ticket or update its processing fields."""
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO tickets (
                ticket_id,
                customer_id,
                subject,
                description,
                category,
                priority,
                status,
                created_at,
                updated_at,
                resolution,
                requires_human_approval,
                escalation_reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticket_id) DO UPDATE SET
                category = excluded.category,
                priority = excluded.priority,
                status = excluded.status,
                updated_at = excluded.updated_at,
                resolution = excluded.resolution,
                requires_human_approval = excluded.requires_human_approval,
                escalation_reason = excluded.escalation_reason
            """,
            (
                ticket.ticket_id,
                ticket.customer_id,
                ticket.subject,
                ticket.description,
                ticket.category.value,
                ticket.priority.value,
                ticket.status.value,
                ticket.created_at.isoformat(),
                ticket.updated_at.isoformat(),
                ticket.resolution,
                int(ticket.requires_human_approval),
                ticket.escalation_reason,
            ),
        )


def get_ticket(ticket_id: str) -> dict | None:
    """Retrieve a ticket by ID, or return None if it does not exist."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?",
            (ticket_id,),
        ).fetchone()

    return dict(row) if row else None
