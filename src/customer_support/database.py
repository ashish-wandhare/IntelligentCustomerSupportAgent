
import sqlite3

from datetime import datetime, timezone
from pathlib import Path

from src.customer_support.config import settings
from src.customer_support.schemas import (
    ReviewAction,
    ReviewDecision,
    Ticket,
)


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
    """Create tables and safely migrate older ticket databases."""
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
                customer_response TEXT,
                requires_human_approval INTEGER NOT NULL DEFAULT 0,
                escalation_reason TEXT,
                category_confidence REAL,
                priority_confidence REAL
            )
            """
        )

        existing_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(tickets)"
            ).fetchall()
        }

        if "customer_response" not in existing_columns:
            connection.execute(
                "ALTER TABLE tickets ADD COLUMN customer_response TEXT"
            )

        if "category_confidence" not in existing_columns:
            connection.execute(
                "ALTER TABLE tickets ADD COLUMN category_confidence REAL"
            )

        if "priority_confidence" not in existing_columns:
            connection.execute(
                "ALTER TABLE tickets ADD COLUMN priority_confidence REAL"
            )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ticket_reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL,
                action TEXT NOT NULL
                    CHECK (action IN ('approve', 'reject')),
                reviewer_id TEXT NOT NULL,
                comment TEXT,
                reviewed_at TEXT NOT NULL,
                FOREIGN KEY (ticket_id)
                    REFERENCES tickets(ticket_id)
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tickets_status
            ON tickets(status)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ticket_reviews_ticket_id
            ON ticket_reviews(ticket_id)
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
                customer_response,
                requires_human_approval,
                escalation_reason,
                category_confidence,
                priority_confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticket_id) DO UPDATE SET
                category = excluded.category,
                priority = excluded.priority,
                status = excluded.status,
                updated_at = excluded.updated_at,
                resolution = excluded.resolution,
                customer_response = excluded.customer_response,
                requires_human_approval =
                    excluded.requires_human_approval,
                escalation_reason = excluded.escalation_reason,
                category_confidence = excluded.category_confidence,
                priority_confidence = excluded.priority_confidence
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
                ticket.customer_response,
                int(ticket.requires_human_approval),
                ticket.escalation_reason,
                ticket.category_confidence,
                ticket.priority_confidence,
            ),
        )


def get_ticket(ticket_id: str) -> dict | None:
    """Retrieve a ticket by ID, or return None if not found."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?",
            (ticket_id,),
        ).fetchone()

    return dict(row) if row else None


def get_all_tickets(limit: int = 500) -> list[dict]:
    """Return the most recently updated tickets for monitoring."""
    if limit < 1:
        raise ValueError("Limit must be at least 1.")

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM tickets
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_pending_review_tickets() -> list[dict]:
    """Return tickets waiting for human approval."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM tickets
            WHERE status = 'waiting_for_approval'
              AND requires_human_approval = 1
            ORDER BY created_at ASC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def save_review(
    ticket_id: str,
    decision: ReviewDecision,
) -> dict:
    """Record a review and update the ticket atomically.

    Only tickets currently awaiting approval can be reviewed.
    """
    reviewed_at = datetime.now(timezone.utc).isoformat()
    action = decision.action

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        row = connection.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?",
            (ticket_id,),
        ).fetchone()

        if row is None:
            raise ValueError("Ticket not found.")

        if (
            row["status"] != "waiting_for_approval"
            or row["requires_human_approval"] != 1
        ):
            raise ValueError(
                "Ticket is not currently awaiting human approval."
            )

        if action == ReviewAction.APPROVE:
            new_status = "processing"
            requires_human_approval = 0
            escalation_reason = None
        else:
            new_status = "escalated"
            requires_human_approval = 1
            escalation_reason = (
                decision.comment
                or "Human reviewer rejected the ticket."
            )

        connection.execute(
            """
            INSERT INTO ticket_reviews (
                ticket_id,
                action,
                reviewer_id,
                comment,
                reviewed_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                ticket_id,
                action.value,
                decision.reviewer_id,
                decision.comment,
                reviewed_at,
            ),
        )

        connection.execute(
            """
            UPDATE tickets
            SET status = ?,
                requires_human_approval = ?,
                escalation_reason = ?,
                updated_at = ?
            WHERE ticket_id = ?
            """,
            (
                new_status,
                requires_human_approval,
                escalation_reason,
                reviewed_at,
                ticket_id,
            ),
        )

        updated_row = connection.execute(
            "SELECT * FROM tickets WHERE ticket_id = ?",
            (ticket_id,),
        ).fetchone()

    return {
        "ticket": dict(updated_row),
        "action": action.value,
        "reviewer_id": decision.reviewer_id,
        "comment": decision.comment,
        "reviewed_at": reviewed_at,
    }


def get_ticket_reviews(ticket_id: str) -> list[dict]:
    """Retrieve review history for a ticket."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT review_id, ticket_id, action, reviewer_id,
                   comment, reviewed_at
            FROM ticket_reviews
            WHERE ticket_id = ?
            ORDER BY review_id ASC
            """,
            (ticket_id,),
        ).fetchall()

    return [dict(row) for row in rows]
