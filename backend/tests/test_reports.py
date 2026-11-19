from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.dataset import CleanedEvent, Dataset


@pytest.fixture
def report_dataset(db: Session) -> Dataset:
    dataset = Dataset(
        id=uuid.uuid4(),
        name="Quarterly P2P",
        filename="quarterly_p2p.csv",
        file_path="quarterly_p2p.csv",
        status="processed",
        total_rows_raw=9,
    )
    db.add(dataset)
    db.commit()

    event_rows = [
        ("CASE-1", "Purchase Requisition", datetime(2025, 1, 1, 9, tzinfo=timezone.utc)),
        ("CASE-1", "Manager Approval", datetime(2025, 1, 1, 10, tzinfo=timezone.utc)),
        ("CASE-1", "Purchase Order Created", datetime(2025, 1, 1, 11, tzinfo=timezone.utc)),
        ("CASE-1", "Goods Received", datetime(2025, 1, 2, 9, tzinfo=timezone.utc)),
        ("CASE-1", "Invoice Received", datetime(2025, 1, 2, 10, tzinfo=timezone.utc)),
        ("CASE-1", "Invoice Verified", datetime(2025, 1, 2, 11, tzinfo=timezone.utc)),
        ("CASE-1", "Payment Completed", datetime(2025, 1, 2, 12, tzinfo=timezone.utc)),
        ("CASE-2", "Purchase Requisition", datetime(2025, 1, 3, 10, tzinfo=timezone.utc)),
        ("CASE-2", "Purchase Order Created", datetime(2025, 1, 3, 11, tzinfo=timezone.utc)),
    ]
    db.add_all(
        [
            CleanedEvent(
                id=index,
                dataset_id=dataset.id,
                case_id=case_id,
                activity=activity,
                timestamp=timestamp,
                extra_attributes={"vendor_id": "V-1", "department": "Procurement"},
            )
            for index, (case_id, activity, timestamp) in enumerate(event_rows, start=1)
        ]
    )
    db.commit()
    return dataset


def test_events_csv_includes_metadata_and_applies_date_filters(
    client: TestClient, report_dataset: Dataset
):
    response = client.get(
        "/api/reports/events-csv",
        params={
            "dataset_id": str(report_dataset.id),
            "start_date": "2025-01-01T10:00:00+00:00",
            "end_date": "2025-01-01T10:30:00+00:00",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(response.text)))
    assert [f"# Dataset ID: {report_dataset.id}"] in rows
    assert any(row[0].startswith("# Generated at UTC: ") for row in rows if row)

    header_index = next(index for index, row in enumerate(rows) if row[0] == "case_id")
    event_rows = rows[header_index + 1 :]
    assert len(event_rows) == 1
    assert event_rows[0][1] == "Manager Approval"


def test_conformance_json_includes_dataset_filters_kpis_bottlenecks_and_deviations(
    client: TestClient, report_dataset: Dataset
):
    response = client.get(
        "/api/v1/reports/conformance-json",
        params={
            "dataset_id": str(report_dataset.id),
            "start_date": "2025-01-01T00:00:00+00:00",
            "end_date": "2025-01-03T23:59:59+00:00",
        },
    )

    assert response.status_code == 200
    report = response.json()
    assert report["dataset"]["id"] == str(report_dataset.id)
    assert report["dataset"]["name"] == "Quarterly P2P"
    assert report["filters"]["start_date"] == "2025-01-01T00:00:00+00:00"
    assert report["generated_at"].endswith("+00:00")
    assert report["kpis"]["overview"]["total_purchase_cases"] == 2
    assert "cycle_time" in report["kpis"]
    assert "bottlenecks" in report["bottlenecks"]
    assert report["conformance_report"]["total_cases"] == 2
    assert any(
        item["deviation_type"] == "INCOMPLETE_PROCESS"
        for item in report["conformance_report"]["deviation_breakdown"]
    )


def test_kpi_pdf_is_downloadable(client: TestClient, report_dataset: Dataset):
    response = client.get(
        "/api/v1/reports/kpi-pdf",
        params={"dataset_id": str(report_dataset.id)},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.content.startswith(b"%PDF-")


def test_report_rejects_reversed_date_range(client: TestClient, report_dataset: Dataset):
    response = client.get(
        "/api/reports/events-csv",
        params={
            "dataset_id": str(report_dataset.id),
            "start_date": "2025-01-02T00:00:00+00:00",
            "end_date": "2025-01-01T00:00:00+00:00",
        },
    )

    assert response.status_code == 422
