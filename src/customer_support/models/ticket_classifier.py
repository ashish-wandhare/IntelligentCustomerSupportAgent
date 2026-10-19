
"""Train and use ML models to classify customer support tickets."""

import json
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "synthetic" / "tickets.jsonl"
DEFAULT_MODEL_DIR = PROJECT_ROOT / "models"


def load_training_data(dataset_path: Path = DEFAULT_DATASET):
    """Load synthetic ticket text and its category/priority labels."""
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    texts = []
    categories = []
    priorities = []

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

            required_fields = {
                "subject", "description", "category", "priority"
            }
            missing = required_fields - ticket.keys()
            if missing:
                raise ValueError(
                    f"Line {line_number} is missing fields: {sorted(missing)}"
                )

            texts.append(f"{ticket['subject']} {ticket['description']}")
            categories.append(ticket["category"])
            priorities.append(ticket["priority"])

    if len(texts) < 8:
        raise ValueError("At least 8 labeled tickets are required.")

    if len(set(categories)) < 2 or len(set(priorities)) < 2:
        raise ValueError(
            "Training data must contain at least two categories "
            "and two priority levels."
        )

    return texts, categories, priorities


def build_pipeline() -> Pipeline:
    """Create a lightweight TF-IDF + Logistic Regression pipeline."""
    return Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )


def train_models(
    dataset_path: Path = DEFAULT_DATASET,
    model_dir: Path = DEFAULT_MODEL_DIR,
) -> dict:
    """Train category and priority models and save them to disk."""
    texts, categories, priorities = load_training_data(dataset_path)

    category_model = build_pipeline()
    priority_model = build_pipeline()

    category_model.fit(texts, categories)
    priority_model.fit(texts, priorities)

    model_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(
        category_model, model_dir / "ticket_category_model.joblib"
    )
    joblib.dump(
        priority_model, model_dir / "ticket_priority_model.joblib"
    )

    return {
        "training_samples": len(texts),
        "category_labels": sorted(set(categories)),
        "priority_labels": sorted(set(priorities)),
        "model_directory": str(model_dir),
    }


def load_models(model_dir: Path = DEFAULT_MODEL_DIR) -> tuple[Pipeline, Pipeline]:
    """Load both previously trained models."""
    category_path = model_dir / "ticket_category_model.joblib"
    priority_path = model_dir / "ticket_priority_model.joblib"

    if not category_path.is_file() or not priority_path.is_file():
        raise FileNotFoundError(
            "Trained models not found. Run train_models() first."
        )

    return joblib.load(category_path), joblib.load(priority_path)


def predict_ticket(
    subject: str,
    description: str,
    model_dir: Path = DEFAULT_MODEL_DIR,
) -> dict:
    """Predict category and priority for one ticket."""
    if not subject.strip() or not description.strip():
        raise ValueError("Subject and description cannot be empty.")

    category_model, priority_model = load_models(model_dir)
    text = [f"{subject.strip()} {description.strip()}"]

    category = category_model.predict(text)[0]
    priority = priority_model.predict(text)[0]

    category_confidence = float(
        max(category_model.predict_proba(text)[0])
    )
    priority_confidence = float(
        max(priority_model.predict_proba(text)[0])
    )

    return {
        "category": category,
        "priority": priority,
        "category_confidence": round(category_confidence, 4),
        "priority_confidence": round(priority_confidence, 4),
    }


if __name__ == "__main__":
    result = train_models()
    print(json.dumps(result, indent=2))
