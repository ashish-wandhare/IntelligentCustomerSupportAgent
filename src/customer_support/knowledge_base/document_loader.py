from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge_base"


def load_documents(knowledge_dir: Path = DEFAULT_KNOWLEDGE_DIR) -> list[dict]:
    """Load Markdown support documents and split them by section."""
    documents = []

    for file_path in sorted(knowledge_dir.glob("*.md")):
        text = file_path.read_text(encoding="utf-8-sig")
        sections = re.split(r"(?=^## )", text, flags=re.MULTILINE)

        current_title = file_path.stem.replace("_", " ").title()

        for section in sections:
            section = section.strip()
            if not section:
                continue

            heading_match = re.match(r"^#{1,2}\s+(.+)$", section, re.MULTILINE)
            if heading_match:
                current_title = heading_match.group(1).strip()

            documents.append(
                {
                    "source": file_path.name,
                    "section": current_title,
                    "text": section,
                }
            )

    return documents


def chunk_documents(
    documents: list[dict],
    chunk_size: int = 900,
    overlap: int = 120,
) -> list[dict]:
    """Split document sections into overlapping character-based chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size.")

    chunks = []

    for document in documents:
        text = document["text"].strip()
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(
                    {
                        "source": document["source"],
                        "section": document["section"],
                        "text": chunk_text,
                    }
                )

            if end == len(text):
                break

            start = end - overlap

    return chunks
