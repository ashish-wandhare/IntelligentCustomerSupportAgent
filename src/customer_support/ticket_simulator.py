
"""Simulate real-time customer support ticket submissions."""

import argparse
import asyncio
import json
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

DEFAULT_DATASET = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "synthetic"
    / "tickets.jsonl"
)


def load_tickets(dataset_path: Path) -> list[dict]:
    """Load synthetic tickets from a JSON Lines file."""
    if not dataset_path.is_file():
        raise FileNotFoundError(
            f"Synthetic dataset not found: {dataset_path}"
        )

    tickets = []

    with dataset_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                ticket = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}"
                ) from exc

            tickets.append(ticket)

    if not tickets:
        raise ValueError("The synthetic dataset contains no tickets.")

    return tickets


async def simulate_tickets(
    base_url: str,
    interval: float,
    limit: int | None = None,
    dataset_path: Path = DEFAULT_DATASET,
) -> None:
    """Submit synthetic tickets to the running FastAPI application."""
    if interval < 0:
        raise ValueError("Interval cannot be negative.")

    tickets = load_tickets(dataset_path)

    if limit is not None:
        if limit < 1:
            raise ValueError("Limit must be at least 1.")
        tickets = tickets[:limit]

    async with httpx.AsyncClient(
        base_url=base_url.rstrip("/"),
        timeout=10.0,
    ) as client:
        for index, ticket in enumerate(tickets):
            # Send only fields accepted by the ticket creation API.
            payload = {
                "customer_id": ticket["customer_id"],
                "subject": ticket["subject"],
                "description": ticket["description"],
            }

            try:
                response = await client.post(
                    "/tickets",
                    json=payload,
                )
                response.raise_for_status()
            except httpx.HTTPError:
                logger.exception(
                    "Failed to submit synthetic ticket %s.",
                    ticket.get("ticket_id", index + 1),
                )
                continue

            result = response.json()
            logger.info(
                "Submitted ticket %s (%d/%d).",
                result["ticket_id"],
                index + 1,
                len(tickets),
            )

            if index < len(tickets) - 1 and interval > 0:
                await asyncio.sleep(interval)

    logger.info("Ticket simulation finished.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate real-time customer support tickets."
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="Base URL of the FastAPI application.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Seconds between ticket submissions.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of tickets to submit.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Path to the synthetic JSONL dataset.",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    asyncio.run(
        simulate_tickets(
            base_url=args.url,
            interval=args.interval,
            limit=args.limit,
            dataset_path=args.dataset,
        )
    )


if __name__ == "__main__":
    main()
