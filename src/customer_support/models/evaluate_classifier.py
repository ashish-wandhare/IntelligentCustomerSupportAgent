
"""Evaluate ticket classification using a held-out test set."""

import json
from pathlib import Path

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split

from src.customer_support.models.ticket_classifier import (
    build_pipeline,
    load_training_data,
)

RANDOM_STATE = 42
TEST_SIZE = 0.25


def evaluate_classifier(dataset_path: Path) -> dict:
    """Evaluate category and priority models on unseen test examples."""
    texts, categories, priorities = load_training_data(dataset_path)

    results = {}

    for task_name, labels in [
        ("category", categories),
        ("priority", priorities),
    ]:
        # A stratified split keeps label proportions similar in both sets.
        train_texts, test_texts, train_labels, test_labels = (
            train_test_split(
                texts,
                labels,
                test_size=TEST_SIZE,
                random_state=RANDOM_STATE,
                stratify=labels,
            )
        )

        model = build_pipeline()
        model.fit(train_texts, train_labels)
        predictions = model.predict(test_texts)

        results[task_name] = {
            "training_samples": len(train_texts),
            "test_samples": len(test_texts),
            "accuracy": round(
                float(accuracy_score(test_labels, predictions)), 4
            ),
            "classification_report": classification_report(
                test_labels,
                predictions,
                labels=sorted(set(labels)),
                output_dict=True,
                zero_division=0,
            ),
            "confusion_matrix": confusion_matrix(
                test_labels,
                predictions,
                labels=sorted(set(labels)),
            ).tolist(),
            "label_order": sorted(set(labels)),
        }

    return results


def main() -> None:
    dataset_path = (
        Path(__file__).resolve().parents[3]
        / "data"
        / "synthetic"
        / "tickets.jsonl"
    )

    results = evaluate_classifier(dataset_path)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
