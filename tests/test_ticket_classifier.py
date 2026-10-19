
import json

import pytest

from src.customer_support.models.ticket_classifier import (
    load_training_data,
    predict_ticket,
    train_models,
)


def test_load_training_data_returns_expected_fields(tmp_path):
    dataset = tmp_path / "tickets.jsonl"

    records = [
        {
            "subject": f"Payment failed {i}",
            "description": f"The card payment failed, case {i}.",
            "category": "billing",
            "priority": "high",
        }
        for i in range(4)
    ] + [
        {
            "subject": f"Login failed {i}",
            "description": f"Cannot access my account, case {i}.",
            "category": "account",
            "priority": "medium",
        }
        for i in range(4)
    ]

    dataset.write_text(
        "\n".join(json.dumps(record) for record in records),
        encoding="utf-8",
    )

    texts, categories, priorities = load_training_data(dataset)

    assert len(texts) == 8
    assert categories == ["billing"] * 4 + ["account"] * 4
    assert priorities == ["high"] * 4 + ["medium"] * 4


def test_missing_dataset_raises_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_training_data(tmp_path / "missing.jsonl")


def test_training_saves_both_models(tmp_path):
    dataset = tmp_path / "tickets.jsonl"
    records = []

    for category, priority in [
        ("billing", "high"),
        ("account", "medium"),
        ("technical", "critical"),
        ("general", "low"),
    ]:
        for index in range(3):
            records.append(
                {
                    "subject": f"{category} issue {index}",
                    "description": (
                        f"Customer needs help with {category} "
                        f"problem number {index}."
                    ),
                    "category": category,
                    "priority": priority,
                }
            )

    dataset.write_text(
        "\n".join(json.dumps(record) for record in records),
        encoding="utf-8",
    )

    model_dir = tmp_path / "models"
    result = train_models(dataset, model_dir)

    assert result["training_samples"] == 12
    assert (model_dir / "ticket_category_model.joblib").is_file()
    assert (model_dir / "ticket_priority_model.joblib").is_file()


def test_prediction_returns_expected_keys(tmp_path):
    dataset = tmp_path / "tickets.jsonl"
    records = []

    for category, priority in [
        ("billing", "high"),
        ("account", "medium"),
        ("technical", "critical"),
        ("general", "low"),
    ]:
        for index in range(3):
            records.append(
                {
                    "subject": f"{category} issue {index}",
                    "description": (
                        f"Customer needs help with {category} "
                        f"problem number {index}."
                    ),
                    "category": category,
                    "priority": priority,
                }
            )

    dataset.write_text(
        "\n".join(json.dumps(record) for record in records),
        encoding="utf-8",
    )

    model_dir = tmp_path / "models"
    train_models(dataset, model_dir)

    result = predict_ticket(
        "Billing issue",
        "I need help with a payment.",
        model_dir,
    )

    assert result["category"] in {
        "billing",
        "account",
        "technical",
        "general",
    }
    assert result["priority"] in {
        "low",
        "medium",
        "high",
        "critical",
    }
    assert 0.0 <= result["category_confidence"] <= 1.0
    assert 0.0 <= result["priority_confidence"] <= 1.0


def test_empty_ticket_text_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="cannot be empty"):
        predict_ticket("", "Payment problem", tmp_path)
