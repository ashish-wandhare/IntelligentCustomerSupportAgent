
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.customer_support.knowledge_base.document_loader import (
    DEFAULT_KNOWLEDGE_DIR,
    chunk_documents,
    load_documents,
)


class KnowledgeBaseRetriever:
    """Retrieve relevant support passages using TF-IDF and cosine similarity."""

    def __init__(
        self,
        knowledge_dir: Path = DEFAULT_KNOWLEDGE_DIR,
        chunk_size: int = 900,
        overlap: int = 120,
    ) -> None:
        documents = load_documents(knowledge_dir)
        self.chunks = chunk_documents(
            documents,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        if not self.chunks:
            raise ValueError(
                f"No Markdown knowledge documents found in: {knowledge_dir}"
            )

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
        )

        self.document_matrix = self.vectorizer.fit_transform(
            [chunk["text"] for chunk in self.chunks]
        )

    def search(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.10,
    ) -> list[dict]:
        """Return relevant passages ranked by cosine similarity."""
        if not query or not query.strip():
            raise ValueError("query must not be empty.")

        if top_k < 1:
            raise ValueError("top_k must be at least 1.")

        if not 0.0 <= min_score <= 1.0:
            raise ValueError("min_score must be between 0 and 1.")

        query_vector = self.vectorizer.transform([query.strip()])
        scores = cosine_similarity(
            query_vector,
            self.document_matrix,
        ).flatten()

        ranked_indices = scores.argsort()[::-1]
        results = []

        for index in ranked_indices:
            score = float(scores[index])

            if score < min_score:
                continue

            chunk = self.chunks[index]
            results.append(
                {
                    "source": chunk["source"],
                    "section": chunk["section"],
                    "text": chunk["text"],
                    "score": score,
                }
            )

            if len(results) >= top_k:
                break

        return results
