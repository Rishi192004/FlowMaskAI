"""
Unit and Integration Tests for Conformance Checking & Deviation Detection.
Validates:
- Detection of Skipped Approval
- Detection of Early Invoice Verification (before Goods Received)
- Detection of Repeated Approval
- Detection of Incomplete Processes (missing Payment Completed)
- Detection of Unexpected Activities
- Exact culprit event, violation description, and fitness score accuracy
- Administrative rule customization (re-evaluating conformance when rules change)
- Conformance HTTP endpoints
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.conformance.engine import (
    evaluate_case_conformance,
    get_case_deviations_response,
    get_conformance_overview_response,
    run_conformance_check,
)
from app.conformance.rules import ConformanceRulesConfig
from app.models.dataset import CleanedEvent, Dataset


@pytest.fixture()
def conformance_dataset(db: Session) -> Dataset:
    """
    Creates a dataset with 6 specific cases testing every deviation type:
      1. PO-CONF: 100% conformant standard sequence
      2. PO-SKIP-APP: Skipped Manager Approval before PO creation
      3. PO-EARLY-INV: Invoice Verified before Goods Received
      4. PO-REP-APP: Repeated Manager Approval (2 times)
      5. PO-INCOMP: Abandoned at PO Created (missing Payment Completed)
      6. PO-UNEXP: Contains 'Vendor Meeting' (unexpected activity)
    """
    ds = Dataset(
        id=uuid.uuid4(),
        name="Conformance Test Event Log",
        filename="conformance_test.csv",
        file_path="conformance_test.csv",
        status="processed",
    )
    db.add(ds)
    db.commit()

    base_t = datetime(2025, 1, 1, 8, 0, tzinfo=timezone.utc)

    events = [
        # 1. PO-CONF (100% Conformant)
        CleanedEvent(dataset_id=ds.id, case_id="PO-CONF", activity="Purchase Requisition", timestamp=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-CONF", activity="Manager Approval", timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-CONF", activity="Purchase Order Created", timestamp=datetime(2025, 1, 1, 15, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-CONF", activity="Goods Received", timestamp=datetime(2025, 1, 2, 9, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-CONF", activity="Invoice Received", timestamp=datetime(2025, 1, 2, 14, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-CONF", activity="Invoice Verified", timestamp=datetime(2025, 1, 3, 10, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-CONF", activity="Payment Completed", timestamp=datetime(2025, 1, 4, 11, 0, tzinfo=timezone.utc)),

        # 2. PO-SKIP-APP (Skipped Approval)
        CleanedEvent(dataset_id=ds.id, case_id="PO-SKIP-APP", activity="Purchase Requisition", timestamp=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-SKIP-APP", activity="Purchase Order Created", timestamp=datetime(2025, 1, 1, 15, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-SKIP-APP", activity="Goods Received", timestamp=datetime(2025, 1, 2, 9, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-SKIP-APP", activity="Payment Completed", timestamp=datetime(2025, 1, 4, 11, 0, tzinfo=timezone.utc)),

        # 3. PO-EARLY-INV (Early Invoice Verification)
        CleanedEvent(dataset_id=ds.id, case_id="PO-EARLY-INV", activity="Purchase Requisition", timestamp=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-EARLY-INV", activity="Manager Approval", timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-EARLY-INV", activity="Purchase Order Created", timestamp=datetime(2025, 1, 1, 15, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-EARLY-INV", activity="Invoice Received", timestamp=datetime(2025, 1, 2, 9, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-EARLY-INV", activity="Invoice Verified", timestamp=datetime(2025, 1, 2, 14, 0, tzinfo=timezone.utc)), # Verified BEFORE Goods Received!
        CleanedEvent(dataset_id=ds.id, case_id="PO-EARLY-INV", activity="Goods Received", timestamp=datetime(2025, 1, 3, 10, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-EARLY-INV", activity="Payment Completed", timestamp=datetime(2025, 1, 4, 11, 0, tzinfo=timezone.utc)),

        # 4. PO-REP-APP (Repeated Approval)
        CleanedEvent(dataset_id=ds.id, case_id="PO-REP-APP", activity="Purchase Requisition", timestamp=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-REP-APP", activity="Manager Approval", timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-REP-APP", activity="Manager Approval", timestamp=datetime(2025, 1, 2, 10, 0, tzinfo=timezone.utc)), # 2nd approval
        CleanedEvent(dataset_id=ds.id, case_id="PO-REP-APP", activity="Purchase Order Created", timestamp=datetime(2025, 1, 2, 15, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-REP-APP", activity="Payment Completed", timestamp=datetime(2025, 1, 4, 11, 0, tzinfo=timezone.utc)),

        # 5. PO-INCOMP (Incomplete Process)
        CleanedEvent(dataset_id=ds.id, case_id="PO-INCOMP", activity="Purchase Requisition", timestamp=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-INCOMP", activity="Manager Approval", timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-INCOMP", activity="Purchase Order Created", timestamp=datetime(2025, 1, 1, 15, 0, tzinfo=timezone.utc)),

        # 6. PO-UNEXP (Unexpected Activity)
        CleanedEvent(dataset_id=ds.id, case_id="PO-UNEXP", activity="Purchase Requisition", timestamp=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-UNEXP", activity="Manager Approval", timestamp=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-UNEXP", activity="Vendor Meeting", timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc)), # Unexpected!
        CleanedEvent(dataset_id=ds.id, case_id="PO-UNEXP", activity="Purchase Order Created", timestamp=datetime(2025, 1, 1, 16, 0, tzinfo=timezone.utc)),
        CleanedEvent(dataset_id=ds.id, case_id="PO-UNEXP", activity="Payment Completed", timestamp=datetime(2025, 1, 4, 11, 0, tzinfo=timezone.utc)),
    ]

    for ev in events:
        db.add(ev)
    db.commit()

    return ds


# ── 1. Unit Tests for Conformance Checking & Deviations ───────────────────────

def test_conformant_case(conformance_dataset: Dataset, db: Session):
    results, _ = run_conformance_check(db, conformance_dataset.id)
    c_conf = next(c for c in results if c.case_id == "PO-CONF")

    assert c_conf.is_conformant is True
    assert c_conf.fitness_score == 1.0
    assert len(c_conf.deviations) == 0


def test_skipped_approval_detection(conformance_dataset: Dataset, db: Session):
    results, _ = run_conformance_check(db, conformance_dataset.id)
    c_skip = next(c for c in results if c.case_id == "PO-SKIP-APP")

    assert c_skip.is_conformant is False
    dev_types = [d.deviation_type for d in c_skip.deviations]
    assert "SKIPPED_APPROVAL" in dev_types

    dev = next(d for d in c_skip.deviations if d.deviation_type == "SKIPPED_APPROVAL")
    assert dev.severity == "HIGH"
    assert dev.culprit_activity == "Purchase Order Created"
    assert "without authorized Manager Approval" in dev.description


def test_early_invoice_verification_detection(conformance_dataset: Dataset, db: Session):
    results, _ = run_conformance_check(db, conformance_dataset.id)
    c_early = next(c for c in results if c.case_id == "PO-EARLY-INV")

    assert c_early.is_conformant is False
    dev_types = [d.deviation_type for d in c_early.deviations]
    assert "EARLY_INVOICE_VERIFICATION" in dev_types

    dev = next(d for d in c_early.deviations if d.deviation_type == "EARLY_INVOICE_VERIFICATION")
    assert dev.severity == "HIGH"
    assert dev.culprit_activity == "Invoice Verified"
    assert "3-way match" in dev.description


def test_repeated_approval_detection(conformance_dataset: Dataset, db: Session):
    results, _ = run_conformance_check(db, conformance_dataset.id)
    c_rep = next(c for c in results if c.case_id == "PO-REP-APP")

    assert c_rep.is_conformant is False
    dev_types = [d.deviation_type for d in c_rep.deviations]
    assert "REPEATED_APPROVAL" in dev_types


def test_incomplete_process_detection(conformance_dataset: Dataset, db: Session):
    results, _ = run_conformance_check(db, conformance_dataset.id)
    c_incomp = next(c for c in results if c.case_id == "PO-INCOMP")

    assert c_incomp.is_conformant is False
    dev_types = [d.deviation_type for d in c_incomp.deviations]
    assert "INCOMPLETE_PROCESS" in dev_types


def test_unexpected_activity_detection(conformance_dataset: Dataset, db: Session):
    results, _ = run_conformance_check(db, conformance_dataset.id)
    c_unexp = next(c for c in results if c.case_id == "PO-UNEXP")

    assert c_unexp.is_conformant is False
    dev_types = [d.deviation_type for d in c_unexp.deviations]
    assert "UNEXPECTED_ACTIVITY" in dev_types
    dev = next(d for d in c_unexp.deviations if d.deviation_type == "UNEXPECTED_ACTIVITY")
    assert dev.culprit_activity == "Vendor Meeting"


def test_configurable_rules_override(conformance_dataset: Dataset, db: Session):
    """
    Verifies that changing business rules alters conformance detection
    (e.g., if require_manager_approval=False, PO-SKIP-APP no longer flags SKIPPED_APPROVAL).
    """
    custom_rules = ConformanceRulesConfig(
        require_manager_approval=False,
        require_payment_completion=True,
    )
    results, _ = run_conformance_check(db, conformance_dataset.id, rules=custom_rules)
    c_skip = next(c for c in results if c.case_id == "PO-SKIP-APP")

    # Should NOT have SKIPPED_APPROVAL deviation because rule was disabled
    dev_types = [d.deviation_type for d in c_skip.deviations]
    assert "SKIPPED_APPROVAL" not in dev_types


# ── 2. Integration Tests for HTTP Endpoints ───────────────────────────────────

def test_conformance_api_endpoints(client: TestClient, conformance_dataset: Dataset):
    ds_id = str(conformance_dataset.id)

    # 1. Overview
    r_ov = client.get(f"/api/conformance/overview?dataset_id={ds_id}")
    assert r_ov.status_code == 200
    ov_data = r_ov.json()
    assert ov_data["total_cases"] == 6
    assert ov_data["conformant_cases"] == 1
    assert ov_data["deviant_cases"] == 5
    assert ov_data["conformance_percentage"] == round(1/6 * 100, 2)
    assert len(ov_data["deviation_breakdown"]) >= 5

    # 2. Deviations
    r_dev = client.get(f"/api/conformance/deviations?dataset_id={ds_id}")
    assert r_dev.status_code == 200
    assert len(r_dev.json()) >= 5

    # 3. Cases (all and deviant-only)
    r_cases = client.get(f"/api/conformance/cases?dataset_id={ds_id}")
    assert r_cases.status_code == 200
    assert r_cases.json()["total_cases"] == 6

    r_dev_only = client.get(f"/api/conformance/cases?dataset_id={ds_id}&filter_deviant_only=true")
    assert r_dev_only.status_code == 200
    assert len(r_dev_only.json()["cases"]) == 5

    # 4. Rules GET & PUT
    r_rules = client.get(f"/api/conformance/rules?dataset_id={ds_id}")
    assert r_rules.status_code == 200
    assert r_rules.json()["require_manager_approval"] is True

    # Update rule
    r_put = client.put(
        f"/api/conformance/rules?dataset_id={ds_id}",
        json={"require_manager_approval": False, "prohibit_early_invoice_verification": False},
    )
    assert r_put.status_code == 200
    assert r_put.json()["require_manager_approval"] is False
