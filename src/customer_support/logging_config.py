import logging
from pathlib import Path

from src.customer_support.config import settings


def configure_logging() -> None:
    """Configure application logging to the console and a log file."""
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / "app.log", encoding="utf-8"),
        ],
        force=True,
    )