"""
Comprehensive tests for ETL Extraction, Transformation, Validation, Loading,
and Data Quality reporting.
"""
from __future__ import annotations

import io
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.etl.detector import detect_columns_and_preview, detect_delimiter, suggest_column_mapping
from app.etl.normalizer import normalize_activity_name, parse_timestamp_to_utc
from app.etl.pipeline import run_etl_pipeline
from app.etl.validator import EventLogValidator
from app.models.dataset import CleanedEvent, DataQualityIssue, Dataset, ETLExecution, RawEvent
from data.sample.generate_p2p_dataset import generate_p2p_event_log


# ── 1. Unit Tests: Normalization & Detection ──────────────────────────────────

def test_detect_delimiter():
    with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as f:
        f.write("case_id;activity;timestamp\n1;Review;2025-01-01\n")
        f_path = f.name
    try:
        delim = detect_delimiter(f_path)
        assert delim == ";"
    finally:
        os.remove(f_path)


def test_suggest_column_mapping():
    cols = ["Case ID", "Event_Name", "Time", "User", "Amount"]
    mapping = suggest_column_mapping(cols)
    assert mapping["case_id"] == "Case ID"
    assert mapping["activity"] == "Event_Name"
    assert mapping["timestamp"] == "Time"
    assert mapping["resource"] == "User"


def test_normalize_activity_name():
    assert normalize_activity_name("po_created") == "PO Created"
    assert normalize_activity_name("manager  approval") == "Manager Approval"
    assert normalize_activity_name("INVOICE_RECEIVED") == "Invoice Received"
    assert normalize_activity_name("goods-received") == "Goods Received"
    assert normalize_activity_name("") == ""
    assert normalize_activity_name(None) == ""


def test_parse_timestamp_to_utc():
    # ISO 8601 with Z
    dt1 = parse_timestamp_to_utc("2025-05-10T15:30:00Z")
    assert dt1 is not None
    assert dt1.tzinfo == timezone.utc
    assert dt1.hour == 15

    # Standard format
    dt2 = parse_timestamp_to_utc("2025-05-10 17:30:00")
    assert dt2 is not None
    assert dt2.tzinfo == timezone.utc

    # Invalid timestamp
    assert parse_timestamp_to_utc("not-a-date") is None
    assert parse_timestamp_to_utc(None) is None


# ── 2. Unit Tests: Validation Rules ───────────────────────────────────────────

def test_validator_detects_missing_and_malformed():
    val = EventLogValidator()
    # Missing case_id
    r1 = val.validate_row(1, "", "Approval", datetime.now(timezone.utc), "Alice", {})
    assert r1.is_rejected is True
    assert any(iss["issue_type"] == "MISSING_REQUIRED_FIELD" for iss in r1.issues)

    # Missing activity
    r2 = val.validate_row(2, "PO-001", "", datetime.now(timezone.utc), "Alice", {})
    assert r2.is_rejected is True

    # Invalid datetime
    r3 = val.validate_row(3, "PO-001", "Approval", None, "Alice", {})
    assert r3.is_rejected is True
    assert any(iss["issue_type"] == "INVALID_TIMESTAMP" for iss in r3.issues)


def test_validator_detects_duplicates_and_out_of_order():
    val = EventLogValidator()
    t1 = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)  # earlier than t1!

    # Normal row
    r1 = val.validate_row(1, "PO-100", "Review", t1, "Alice", {})
    assert r1.is_valid is True

    # Duplicate row
    r2 = val.validate_row(2, "PO-100", "Review", t1, "Alice", {})
    assert r2.is_duplicate is True
    assert any(iss["issue_type"] == "DUPLICATE_EVENT" for iss in r2.issues)

    # Out of order row
    r3 = val.validate_row(3, "PO-100", "Payment", t2, "Bob", {})
    assert r3.is_out_of_order is True
    assert any(iss["issue_type"] == "OUT_OF_ORDER_EVENT" for iss in r3.issues)


# ── 3. Integration Tests: API Endpoints ───────────────────────────────────────

SAMPLE_CSV = """case_id,activity,timestamp,resource,amount
PO-001,Purchase Requisition,2025-01-01T10:00:00Z,Alice,500.00
PO-001,Manager Approval,2025-01-01T14:00:00Z,Bob,500.00
PO-001,PO Created,2025-01-02T09:00:00Z,System,500.00
PO-002,Purchase Requisition,2025-01-01T11:00:00Z,Charlie,1200.00
PO-002,,2025-01-01T12:00:00Z,Charlie,1200.00
PO-002,Manager Approval,2025-01-01T10:00:00Z,Diana,1200.00
PO-002,Purchase Requisition,2025-01-01T11:00:00Z,Charlie,1200.00
"""


def test_dataset_upload_endpoint(client: TestClient):
    csv_bytes = SAMPLE_CSV.encode("utf-8")
    resp = client.post(
        "/api/datasets/upload",
        files={"file": ("p2p_sample.csv", csv_bytes, "text/csv")},
        data={"name": "Sample P2P Log"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Sample P2P Log"
    assert data["status"] == "uploaded"
    assert "case_id" in data["detected_columns"]
    assert "suggested_mapping" in data
    assert len(data["preview_rows"]) > 0


def test_list_and_get_dataset(client: TestClient):
    # Upload
    csv_bytes = SAMPLE_CSV.encode("utf-8")
    up_resp = client.post(
        "/api/datasets/upload",
        files={"file": ("p2p_sample2.csv", csv_bytes, "text/csv")},
    )
    dataset_id = up_resp.json()["id"]

    # List
    list_resp = client.get("/api/datasets")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # Get One
    get_resp = client.get(f"/api/datasets/{dataset_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == dataset_id


def test_process_dataset_and_quality_audit(client: TestClient):
    csv_bytes = SAMPLE_CSV.encode("utf-8")
    up_resp = client.post(
        "/api/datasets/upload",
        files={"file": ("p2p_sample3.csv", csv_bytes, "text/csv")},
        data={"name": "P2P Audit Log"},
    )
    dataset_id = up_resp.json()["id"]

    # Process
    proc_resp = client.post(
        f"/api/datasets/{dataset_id}/process",
        json={"drop_duplicates": True, "normalize_activities": True},
    )
    assert proc_resp.status_code == 200
    proc_data = proc_resp.json()
    assert proc_data["status"] == "completed"
    metrics = proc_data["metrics"]
    assert metrics["total_records_received"] == 7
    assert metrics["duplicate_records"] >= 1
    assert metrics["missing_value_records"] >= 1
    assert metrics["records_loaded"] >= 4

    # Quality Report
    qual_resp = client.get(f"/api/datasets/{dataset_id}/quality")
    assert qual_resp.status_code == 200
    qual_data = qual_resp.json()
    assert qual_data["dataset_id"] == dataset_id
    assert qual_data["dataset_status"] == "processed"
    assert "MISSING_REQUIRED_FIELD" in qual_data["issue_breakdown"]
    assert len(qual_data["recent_issues"]) > 0


# ── 4. 100K+ Event Dataset Test & Benchmark ───────────────────────────────────

def test_100k_event_dataset_pipeline(db: Session):
    """
    Validates that the ETL pipeline can process 100K+ records efficiently
    with chunked streaming, full raw preservation, and complete audit tracking.
    """
    tmp_csv = Path(tempfile.gettempdir()) / "p2p_benchmark_100k.csv"
    try:
        # Generate 102,000 events
        generate_p2p_event_log(tmp_csv, target_event_count=102000)
        assert tmp_csv.exists()
        assert tmp_csv.stat().st_size > 5_000_000  # > 5 MB

        # Create dataset entity
        dataset = Dataset(
            name="100K Benchmark Dataset",
            filename=tmp_csv.name,
            file_path=str(tmp_csv.resolve()),
            file_size_bytes=tmp_csv.stat().st_size,
            delimiter=",",
            status="uploaded",
            column_mapping={
                "case_id": "Case ID",
                "activity": "Activity",
                "timestamp": "Timestamp",
                "resource": "Resource",
            },
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        # Run ETL
        execution = run_etl_pipeline(
            db=db,
            dataset_id=dataset.id,
            drop_duplicates=True,
            normalize_activities=True,
        )

        assert execution.status == "completed"
        assert execution.total_records_received >= 100_000
        assert execution.records_loaded > 90_000
        assert execution.records_rejected > 0
        assert execution.duration_seconds is not None
        assert execution.duration_seconds > 0.0

        # Verify raw events were preserved for audit
        raw_count = db.query(RawEvent).filter(RawEvent.dataset_id == dataset.id).count()
        assert raw_count == execution.total_records_received

        # Verify cleaned events
        cleaned_count = db.query(CleanedEvent).filter(CleanedEvent.dataset_id == dataset.id).count()
        assert cleaned_count == execution.records_loaded

        # Verify data quality issues logged
        issue_count = db.query(DataQualityIssue).filter(DataQualityIssue.dataset_id == dataset.id).count()
        assert issue_count > 0

    finally:
        if tmp_csv.exists():
            tmp_csv.unlink(missing_ok=True)
