from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.assistant import classify_assistant_intent
from app.ai.llm import AssistantGenerationError, generate_grounded_answer
from app.models.dataset import CleanedEvent, Dataset
from app.schemas.ai import (
    AssistantIntentEnum,
    AssistantMetricFact,
)


@pytest.mark.parametrize(
    ("question", "expected_intent"),
    [
        ("What is our biggest bottleneck?", AssistantIntentEnum.BOTTLENECK),
        ("Which vendors have the highest SLA breach rate?", AssistantIntentEnum.VENDOR_SLA),
        ("Why are cases taking longer than expected?", AssistantIntentEnum.CYCLE_TIME),
        ("Which activities contribute most to rework?", AssistantIntentEnum.REWORK),
        ("What percentage of cases violate the reference process?", AssistantIntentEnum.CONFORMANCE),
        ("What actions should management prioritize?", AssistantIntentEnum.PRIORITIES),
    ],
)
def test_classifies_supported_questions(question, expected_intent):
    assert classify_assistant_intent(question) == expected_intent


@pytest.fixture
def assistant_dataset(db: Session) -> Dataset:
    dataset = Dataset(
        id=uuid.uuid4(),
        name="Assistant test dataset",
        filename="assistant.csv",
        file_path="assistant.csv",
        status="processed",
    )
    db.add(dataset)
    db.commit()
    db.add_all(
        [
            CleanedEvent(
                id=1,
                dataset_id=dataset.id,
                case_id="CASE-1",
                activity="Purchase Requisition",
                timestamp=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
            ),
            CleanedEvent(
                id=2,
                dataset_id=dataset.id,
                case_id="CASE-1",
                activity="Manager Approval",
                timestamp=datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc),
            ),
        ]
    )
    db.commit()
    return dataset


def test_query_returns_measured_facts_separately_from_llm(
    client: TestClient, assistant_dataset: Dataset, monkeypatch
):
    monkeypatch.setattr(
        "app.ai.assistant.generate_grounded_answer",
        lambda *_args: "The measured transition evidence identifies an approval delay.",
    )
    response = client.post(
        "/api/v1/ai/assistant/query",
        json={
            "dataset_id": str(assistant_dataset.id),
            "question": "What is our biggest bottleneck?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "BOTTLENECK"
    assert body["answer"] == "The measured transition evidence identifies an approval delay."
    assert body["measured_facts"]
    assert body["recommendations"] == []
    assert body["generation_model"] == "qwen3:8b"
    fact_map = {fact["key"]: fact for fact in body["measured_facts"]}
    assert fact_map["bottleneck.1.activity"]["value"] == "Manager Approval"
    assert fact_map["bottleneck.1.average_wait_hours"]["value"] == 2.0


def test_query_returns_measured_facts_when_safe_narrative_generation_fails(
    client: TestClient, assistant_dataset: Dataset, monkeypatch
):
    def reject_narrative(*_args):
        raise AssistantGenerationError(
            "Ollama returned an unsupported numeric claim; the answer was rejected."
        )

    monkeypatch.setattr("app.ai.assistant.generate_grounded_answer", reject_narrative)
    response = client.post(
        "/api/v1/ai/assistant/query",
        json={
            "dataset_id": str(assistant_dataset.id),
            "question": "What is cycle time?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["generation_model"] is None
    assert "could not provide a safe narrative" in body["answer"]
    fact_map = {fact["key"]: fact for fact in body["measured_facts"]}
    assert fact_map["cycle_time.average_hours"]["value"] == 2.0


def test_query_returns_configured_sla_baseline_separately(
    client: TestClient, assistant_dataset: Dataset, monkeypatch
):
    monkeypatch.setattr(
        "app.ai.assistant.generate_grounded_answer",
        lambda *_args: "The measured cycle time is below the configured target.",
    )
    response = client.post(
        "/api/v1/ai/assistant/query",
        json={
            "dataset_id": str(assistant_dataset.id),
            "question": "Why are cases taking longer than expected?",
            "recommendations_config": {"sla_hours": 240},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert any(fact["key"] == "cycle_time.average_hours" for fact in body["measured_facts"])
    assert body["configured_baselines"] == [
        {
            "key": "cycle_time.sla_target_hours",
            "label": "Configured cycle-time target",
            "value": 240.0,
            "display_value": "240 hours",
            "source": "assistant.request.recommendations_config.sla_hours",
        }
    ]


def test_unknown_questions_return_unavailable_without_calling_the_llm(
    client: TestClient, assistant_dataset: Dataset, monkeypatch
):
    def fail_if_called(*_args):
        raise AssertionError("Unsupported intents must not call Ollama.")

    monkeypatch.setattr("app.ai.assistant.generate_grounded_answer", fail_if_called)
    response = client.post(
        "/api/v1/ai/assistant/query",
        json={
            "dataset_id": str(assistant_dataset.id),
            "question": "What is the current exchange rate?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["intent"] == "UNSUPPORTED"
    assert "can't answer" in body["answer"]
    assert body["measured_facts"] == []


def test_greeting_returns_supported_topics_without_calling_the_llm(
    client: TestClient, assistant_dataset: Dataset, monkeypatch
):
    def fail_if_called(*_args):
        raise AssertionError("A greeting must not call Ollama.")

    monkeypatch.setattr("app.ai.assistant.generate_grounded_answer", fail_if_called)
    response = client.post(
        "/api/v1/ai/assistant/query",
        json={"dataset_id": str(assistant_dataset.id), "question": "hi"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["intent"] == "UNSUPPORTED"
    assert body["answer"].startswith("Hi!")
    assert body["measured_facts"] == []


def test_local_llm_receives_only_structured_evidence():
    fact = AssistantMetricFact(
        key="cases",
        label="Total analyzed cases",
        value=12,
        display_value="12",
        source="analytics.overview",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url.path == "/api/chat"
        assert payload["model"] == "qwen3:8b"
        user_content = json.loads(payload["messages"][1]["content"])
        assert user_content["measured_facts"][0]["value"] == 12
        assert "execute or suggest SQL" in payload["messages"][0]["content"]
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps({"answer": "The dataset contains observed cases."})}},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        answer = generate_grounded_answer(
            "How many cases?",
            "CYCLE_TIME",
            [fact],
            [],
            [],
            client=client,
        )

    assert answer == "The dataset contains observed cases."


def test_rejects_numeric_claims_from_local_llm():
    fact = AssistantMetricFact(
        key="rate",
        label="Rate",
        value=0.25,
        display_value="25%",
        source="analytics.overview",
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps({"answer": "The rate is 25%."})}},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AssistantGenerationError, match="unsupported numeric claim"):
            generate_grounded_answer(
                "What is the rate?",
                "CONFORMANCE",
                [fact],
                [],
                [],
                client=client,
            )


def test_rejects_number_words_from_local_llm():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"message": {"content": json.dumps({"answer": "One process stands out."})}},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AssistantGenerationError, match="unsupported numeric claim"):
            generate_grounded_answer(
                "What stands out?",
                "BOTTLENECK",
                [],
                [],
                [],
                client=client,
            )
