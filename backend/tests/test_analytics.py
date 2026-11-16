"""
Unit & Integration Tests for Operational Analytics Engine.
Uses a small, manually verifiable dataset with exactly known metrics:
- 3 cases (2 completed, 1 incomplete)
- Exact known durations: 24.0h, 48.0h, 3.0h
- Exact known waiting times, rework counts, and SLA breaches.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.service import (
    get_bottleneck_analytics,
    get_cycle_time_analytics,
    get_department_performance_analytics,
    get_overview_analytics,
    get_rework_analytics,
    get_trends_analytics,
    get_vendor_performance_analytics,
    get_waiting_time_analytics,
)
from app.models.dataset import CleanedEvent, Dataset


@pytest.fixture()
def verified_dataset(db: Session) -> Dataset:
    """
    Creates a manually verifiable dataset with 3 distinct cases:
    - Case PO-101: Completed, cycle time = 24.0h, spend = $1,000, Vendor = V-A, Dept = IT
    - Case PO-102: Completed, cycle time = 48.0h, spend = $2,000, Vendor = V-A, Dept = Finance, Rework on Manager Approval
    - Case PO-103: Incomplete (abandoned), cycle time = 3.0h, spend = $3,000, Vendor = V-B, Dept = IT
    """
    ds = Dataset(
        id=uuid.uuid4(),
        name="Manually Verifiable Test Log",
        filename="verified.csv",
        file_path="verified.csv",
        status="processed",
    )
    db.add(ds)
    db.commit()

    events = [
        # Case 1: PO-101 (24.0h duration, completed)
        CleanedEvent(
            dataset_id=ds.id,
            case_id="PO-101",
            activity="Purchase Requisition",
            timestamp=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            resource="Alice",
            extra_attributes={"amount": 1000.0, "vendor_id": "V-A", "department": "IT"},
        ),
        CleanedEvent(
            dataset_id=ds.id,
            case_id="PO-101",
            activity="Manager Approval",
            timestamp=datetime(2025, 1, 1, 14, 0, 0, tzinfo=timezone.utc),  # wait 4h
            resource="Bob",
            extra_attributes={"amount": 1000.0, "vendor_id": "V-A", "department": "IT"},
        ),
        CleanedEvent(
            dataset_id=ds.id,
            case_id="PO-101",
            activity="Payment Completed",
            timestamp=datetime(2025, 1, 2, 10, 0, 0, tzinfo=timezone.utc),  # wait 20h
            resource="System",
            extra_attributes={"amount": 1000.0, "vendor_id": "V-A", "department": "IT"},
        ),

        # Case 2: PO-102 (48.0h duration, completed, rework on Manager Approval)
        CleanedEvent(
            dataset_id=ds.id,
            case_id="PO-102",
            activity="Purchase Requisition",
            timestamp=datetime(2025, 1, 2, 8, 0, 0, tzinfo=timezone.utc),
            resource="Charlie",
            extra_attributes={"amount": 2000.0, "vendor_id": "V-A", "department": "Finance"},
        ),
        CleanedEvent(
            dataset_id=ds.id,
            case_id="PO-102",
            activity="Manager Approval",
            timestamp=datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc),  # wait 4h
            resource="Diana",
            extra_attributes={"amount": 2000.0, "vendor_id": "V-A", "department": "Finance"},
        ),
        CleanedEvent(
            dataset_id=ds.id,
            case_id="PO-102",
            activity="Manager Approval",  # REWORK: 2nd execution
            timestamp=datetime(2025, 1, 3, 8, 0, 0, tzinfo=timezone.utc),  # wait 20h
            resource="Diana",
            extra_attributes={"amount": 2000.0, "vendor_id": "V-A", "department": "Finance"},
        ),
        CleanedEvent(
            dataset_id=ds.id,
            case_id="PO-102",
            activity="Payment Completed",
            timestamp=datetime(2025, 1, 4, 8, 0, 0, tzinfo=timezone.utc),  # wait 24h
            resource="System",
            extra_attributes={"amount": 2000.0, "vendor_id": "V-A", "department": "Finance"},
        ),

        # Case 3: PO-103 (3.0h duration, incomplete / abandoned)
        CleanedEvent(
            dataset_id=ds.id,
            case_id="PO-103",
            activity="Purchase Requisition",
            timestamp=datetime(2025, 1, 5, 9, 0, 0, tzinfo=timezone.utc),
            resource="Evan",
            extra_attributes={"amount": 3000.0, "vendor_id": "V-B", "department": "IT"},
        ),
        CleanedEvent(
            dataset_id=ds.id,
            case_id="PO-103",
            activity="Purchase Order Created",
            timestamp=datetime(2025, 1, 5, 12, 0, 0, tzinfo=timezone.utc),  # wait 3h
            resource="Evan",
            extra_attributes={"amount": 3000.0, "vendor_id": "V-B", "department": "IT"},
        ),
    ]

    for ev in events:
        db.add(ev)
    db.commit()

    return ds


# ── 1. Unit Tests for Metrics Against Ground Truth ────────────────────────────

def test_overview_metrics_ground_truth(db: Session, verified_dataset: Dataset):
    overview = get_overview_analytics(db, verified_dataset.id, sla_hours=30.0)

    assert overview.total_purchase_cases == 3
    assert overview.total_events == 9
    assert overview.completed_cases == 2
    assert overview.incomplete_cases == 1
    assert overview.completion_rate == round(2 / 3, 4)

    # Completed cycle times are 24.0h and 48.0h -> Avg = 36.0h, Median = 36.0h
    assert overview.avg_cycle_time_hours == 36.0
    assert overview.median_cycle_time_hours == 36.0

    # Rework: exactly PO-102 had rework
    assert overview.rework_cases == 1
    assert overview.rework_percentage == round(1 / 3, 4)

    # SLA breaches: with SLA = 30.0h, PO-102 (48h) breached SLA -> 1 breach
    assert overview.sla_breach_cases == 1
    assert overview.sla_breach_percentage == 0.5  # 1 out of 2 completed cases

    # Total spend: $1000 + $2000 + $3000 = $6000
    assert overview.total_spend_usd == 6000.0


def test_cycle_time_percentiles(db: Session, verified_dataset: Dataset):
    ct = get_cycle_time_analytics(db, verified_dataset.id, sla_hours=30.0)

    assert ct.total_cases == 3
    assert ct.completed_cases == 2
    assert ct.min_cycle_time_hours == 24.0
    assert ct.max_cycle_time_hours == 48.0
    assert ct.avg_cycle_time_hours == 36.0
    assert ct.median_cycle_time_hours == 36.0
    assert ct.sla_breach_count == 1
    assert len(ct.distribution) == 10


def test_waiting_time_consecutive_activities(db: Session, verified_dataset: Dataset):
    wt = get_waiting_time_analytics(db, verified_dataset.id)

    # Manager Approval had 3 occurrences:
    # PO-101: 4.0h
    # PO-102: 4.0h and 20.0h
    # Average = (4 + 4 + 20) / 3 = 9.33h
    ma = next((a for a in wt.activities if a.activity == "Manager Approval"), None)
    assert ma is not None
    assert ma.transition_count == 3
    assert ma.avg_waiting_time_hours == round(28.0 / 3.0, 2)
    assert ma.min_waiting_time_hours == 4.0
    assert ma.max_waiting_time_hours == 20.0

    # Payment Completed had 2 occurrences: 20h and 24h -> Avg = 22.0h
    pc = next((a for a in wt.activities if a.activity == "Payment Completed"), None)
    assert pc is not None
    assert pc.transition_count == 2
    assert pc.avg_waiting_time_hours == 22.0


def test_rework_detection(db: Session, verified_dataset: Dataset):
    rw = get_rework_analytics(db, verified_dataset.id)

    assert rw.total_cases == 3
    assert rw.cases_with_rework == 1
    assert rw.rework_case_percentage == round(1 / 3, 4)
    assert rw.total_rework_events == 1

    assert len(rw.activities) == 1
    act = rw.activities[0]
    assert act.activity == "Manager Approval"
    assert act.rework_case_count == 1
    assert act.max_repetitions_in_case == 2


def test_bottleneck_ranking(db: Session, verified_dataset: Dataset):
    bn = get_bottleneck_analytics(db, verified_dataset.id, activity_sla_hours=12.0)

    assert len(bn.bottlenecks) > 0
    # Top bottleneck should have highest score and rank = 1
    top = bn.bottlenecks[0]
    assert top.rank == 1
    assert top.bottleneck_score > 0
    assert len(top.reasons) > 0


def test_vendor_and_department_performance(db: Session, verified_dataset: Dataset):
    vp = get_vendor_performance_analytics(db, verified_dataset.id)
    assert vp.total_vendors == 2

    # Vendor V-A: 2 cases ($3000 spend, 100% completed)
    va = next((v for v in vp.vendors if v.vendor_id == "V-A"), None)
    assert va is not None
    assert va.total_cases == 2
    assert va.total_spend_usd == 3000.0
    assert va.completed_cases == 2
    assert va.completion_rate == 1.0

    dp = get_department_performance_analytics(db, verified_dataset.id)
    assert dp.total_departments == 2
    # Finance: 1 case with rework
    fin = next((d for d in dp.departments if d.department == "Finance"), None)
    assert fin is not None
    assert fin.total_cases == 1
    assert fin.rework_cases == 1
    assert fin.rework_rate == 1.0


# ── 2. Integration Tests for HTTP Endpoints ───────────────────────────────────

def test_analytics_api_endpoints(client: TestClient, verified_dataset: Dataset):
    ds_id = str(verified_dataset.id)

    # 1. Overview
    r1 = client.get(f"/api/analytics/overview?dataset_id={ds_id}&sla_hours=30.0")
    assert r1.status_code == 200
    assert r1.json()["total_purchase_cases"] == 3

    # 2. Cycle Time
    r2 = client.get(f"/api/analytics/cycle-time?dataset_id={ds_id}")
    assert r2.status_code == 200
    assert "distribution" in r2.json()

    # 3. Waiting Time
    r3 = client.get(f"/api/analytics/waiting-time?dataset_id={ds_id}")
    assert r3.status_code == 200
    assert len(r3.json()["activities"]) > 0

    # 4. Rework
    r4 = client.get(f"/api/analytics/rework?dataset_id={ds_id}")
    assert r4.status_code == 200
    assert r4.json()["cases_with_rework"] == 1

    # 5. Bottlenecks
    r5 = client.get(f"/api/analytics/bottlenecks?dataset_id={ds_id}")
    assert r5.status_code == 200
    assert r5.json()["top_bottleneck"] is not None

    # 6. Vendor Performance
    r6 = client.get(f"/api/analytics/vendor-performance?dataset_id={ds_id}")
    assert r6.status_code == 200
    assert r6.json()["total_vendors"] == 2

    # 7. Department Performance
    r7 = client.get(f"/api/analytics/department-performance?dataset_id={ds_id}")
    assert r7.status_code == 200
    assert r7.json()["total_departments"] == 2

    # 8. Trends
    r8 = client.get(f"/api/analytics/trends?dataset_id={ds_id}")
    assert r8.status_code == 200
    assert len(r8.json()["trends"]) > 0
