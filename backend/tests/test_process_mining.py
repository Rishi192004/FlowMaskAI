"""
Unit and Integration Tests for Process Mining Engine.
Validates:
- DFG extraction, edge frequencies, start/end activity analysis
- Variant discovery, variant percentages, and rare path detection
- Inductive Miner process discovery
- Dynamic process map generation for React Flow
- Process map filter responsiveness (verifying map changes when dataset/filters change)
- Process comparison between two departments
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.dataset import CleanedEvent, Dataset
from app.process_mining.discovery import (
    discover_inductive_miner,
    extract_dfg_and_boundaries,
    generate_interactive_process_map,
    get_dfg_response,
)
from app.process_mining.variants import (
    get_activity_frequency_response,
    get_variants_response,
)
from app.process_mining.comparison import compare_process_slices


@pytest.fixture()
def mining_dataset(db: Session) -> Dataset:
    """
    Manually constructed event log with 4 cases and 3 known variants:
      - Case C-1: [Purchase Requisition, Manager Approval, Payment Completed] (Dept: Procurement)
      - Case C-2: [Purchase Requisition, Manager Approval, Payment Completed] (Dept: Procurement)
      - Case C-3: [Purchase Requisition, Payment Completed] (Dept: IT, skipped approval!)
      - Case C-4: [Purchase Requisition, Manager Approval, Manager Approval, Payment Completed] (Dept: Finance, rework loop!)
    """
    ds = Dataset(
        id=uuid.uuid4(),
        name="Process Mining Test Log",
        filename="mining_test.csv",
        file_path="mining_test.csv",
        status="processed",
    )
    db.add(ds)
    db.commit()

    events = [
        # Case C-1 (Procurement)
        CleanedEvent(
            dataset_id=ds.id, case_id="C-1", activity="Purchase Requisition",
            timestamp=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc),
            extra_attributes={"department": "Procurement", "vendor_id": "V-1"}
        ),
        CleanedEvent(
            dataset_id=ds.id, case_id="C-1", activity="Manager Approval",
            timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc),
            extra_attributes={"department": "Procurement", "vendor_id": "V-1"}
        ),
        CleanedEvent(
            dataset_id=ds.id, case_id="C-1", activity="Payment Completed",
            timestamp=datetime(2025, 1, 2, 10, 0, tzinfo=timezone.utc),
            extra_attributes={"department": "Procurement", "vendor_id": "V-1"}
        ),

        # Case C-2 (Procurement - duplicate variant)
        CleanedEvent(
            dataset_id=ds.id, case_id="C-2", activity="Purchase Requisition",
            timestamp=datetime(2025, 1, 2, 8, 0, tzinfo=timezone.utc),
            extra_attributes={"department": "Procurement", "vendor_id": "V-1"}
        ),
        CleanedEvent(
            dataset_id=ds.id, case_id="C-2", activity="Manager Approval",
            timestamp=datetime(2025, 1, 2, 12, 0, tzinfo=timezone.utc),
            extra_attributes={"department": "Procurement", "vendor_id": "V-1"}
        ),
        CleanedEvent(
            dataset_id=ds.id, case_id="C-2", activity="Payment Completed",
            timestamp=datetime(2025, 1, 3, 8, 0, tzinfo=timezone.utc),
            extra_attributes={"department": "Procurement", "vendor_id": "V-1"}
        ),

        # Case C-3 (IT - skipped approval)
        CleanedEvent(
            dataset_id=ds.id, case_id="C-3", activity="Purchase Requisition",
            timestamp=datetime(2025, 1, 4, 9, 0, tzinfo=timezone.utc),
            extra_attributes={"department": "IT", "vendor_id": "V-2"}
        ),
        CleanedEvent(
            dataset_id=ds.id, case_id="C-3", activity="Payment Completed",
            timestamp=datetime(2025, 1, 4, 15, 0, tzinfo=timezone.utc),
            extra_attributes={"department": "IT", "vendor_id": "V-2"}
        ),

        # Case C-4 (Finance - rework loop on Approval)
        CleanedEvent(
            dataset_id=ds.id, case_id="C-4", activity="Purchase Requisition",
            timestamp=datetime(2025, 1, 5, 8, 0, tzinfo=timezone.utc),
            extra_attributes={"department": "Finance", "vendor_id": "V-1"}
        ),
        CleanedEvent(
            dataset_id=ds.id, case_id="C-4", activity="Manager Approval",
            timestamp=datetime(2025, 1, 5, 12, 0, tzinfo=timezone.utc),
            extra_attributes={"department": "Finance", "vendor_id": "V-1"}
        ),
        CleanedEvent(
            dataset_id=ds.id, case_id="C-4", activity="Manager Approval",
            timestamp=datetime(2025, 1, 6, 8, 0, tzinfo=timezone.utc),
            extra_attributes={"department": "Finance", "vendor_id": "V-1"}
        ),
        CleanedEvent(
            dataset_id=ds.id, case_id="C-4", activity="Payment Completed",
            timestamp=datetime(2025, 1, 7, 8, 0, tzinfo=timezone.utc),
            extra_attributes={"department": "Finance", "vendor_id": "V-1"}
        ),
    ]

    for ev in events:
        db.add(ev)
    db.commit()

    return ds


# ── 1. Unit Tests for Process Discovery Algorithms ────────────────────────────

def test_dfg_and_boundaries(mining_dataset: Dataset, db: Session):
    from app.process_mining.converter import fetch_cleaned_event_records

    records = fetch_cleaned_event_records(db, mining_dataset.id)
    assert len(records) == 12

    dfg_freq, dfg_perf, start_acts, end_acts = extract_dfg_and_boundaries(records)

    # 100% of cases start with Purchase Requisition
    assert start_acts == {"Purchase Requisition": 4}
    # 100% of cases end with Payment Completed
    assert end_acts == {"Payment Completed": 4}

    # Verify transition counts
    assert dfg_freq[("Purchase Requisition", "Manager Approval")] == 3
    assert dfg_freq[("Manager Approval", "Payment Completed")] == 3
    assert dfg_freq[("Purchase Requisition", "Payment Completed")] == 1  # Case C-3
    assert dfg_freq[("Manager Approval", "Manager Approval")] == 1    # Case C-4 rework loop


def test_variant_discovery_ground_truth(mining_dataset: Dataset, db: Session):
    from app.process_mining.converter import fetch_cleaned_event_records

    records = fetch_cleaned_event_records(db, mining_dataset.id)
    resp = get_variants_response(mining_dataset.id, records)

    assert resp.total_cases == 4
    assert resp.unique_variants_count == 3
    assert resp.top_variant_percentage == 50.0  # 2 of 4 cases

    # Top variant is standard P2P
    top_var = resp.variants[0]
    assert top_var.case_count == 2
    assert top_var.percentage == 50.0
    assert top_var.activities == ["Purchase Requisition", "Manager Approval", "Payment Completed"]


def test_process_map_generation(mining_dataset: Dataset, db: Session):
    from app.process_mining.converter import fetch_cleaned_event_records

    records = fetch_cleaned_event_records(db, mining_dataset.id)
    pm = generate_interactive_process_map(mining_dataset.id, records)

    assert pm.total_cases == 4
    assert pm.total_events == 12

    # Verify nodes
    node_ids = {n.id for n in pm.nodes}
    assert node_ids == {"Purchase Requisition", "Manager Approval", "Payment Completed"}

    # Verify edges
    edge_pairs = {(e.source, e.target) for e in pm.edges}
    assert ("Purchase Requisition", "Manager Approval") in edge_pairs
    assert ("Manager Approval", "Payment Completed") in edge_pairs
    assert ("Purchase Requisition", "Payment Completed") in edge_pairs
    assert ("Manager Approval", "Manager Approval") in edge_pairs


def test_process_comparison(mining_dataset: Dataset, db: Session):
    from app.process_mining.converter import fetch_cleaned_event_records

    recs_proc = fetch_cleaned_event_records(db, mining_dataset.id, department="Procurement")
    recs_it = fetch_cleaned_event_records(db, mining_dataset.id, department="IT")

    comp = compare_process_slices(
        dataset_id=mining_dataset.id,
        records_a=recs_proc,
        label_a="Procurement",
        records_b=recs_it,
        label_b="IT",
    )

    assert comp.slice_a.case_count == 2
    assert comp.slice_b.case_count == 1
    assert "Manager Approval" in comp.unique_to_a  # IT skipped Manager Approval!
    assert "Purchase Requisition" in comp.shared_activities
    assert comp.divergence_summary is not None


# ── 2. Integration Tests for Process Mining HTTP Endpoints ───────────────────

def test_process_map_changes_with_filters(client: TestClient, mining_dataset: Dataset):
    """
    Acceptance Criteria Test:
    Verifies that the process map dynamically changes when filters are applied.
    """
    ds_id = str(mining_dataset.id)

    # 1. Unfiltered map: 4 cases, 3 nodes, 4 edges
    resp_all = client.get(f"/api/process/map?dataset_id={ds_id}")
    assert resp_all.status_code == 200
    data_all = resp_all.json()
    assert data_all["total_cases"] == 4
    assert len(data_all["edges"]) == 4

    # 2. Filter by department=IT (Case C-3: PR -> Payment Completed, skips Manager Approval)
    resp_it = client.get(f"/api/process/map?dataset_id={ds_id}&department=IT")
    assert resp_it.status_code == 200
    data_it = resp_it.json()
    assert data_it["total_cases"] == 1
    # Only 2 nodes (PR and Payment Completed)
    it_node_ids = {n["id"] for n in data_it["nodes"]}
    assert "Manager Approval" not in it_node_ids
    assert len(data_it["edges"]) == 1
    assert data_it["edges"][0]["source"] == "Purchase Requisition"
    assert data_it["edges"][0]["target"] == "Payment Completed"

    # Confirms process map changed based on filter!
    assert len(data_it["edges"]) != len(data_all["edges"])


def test_process_api_endpoints(client: TestClient, mining_dataset: Dataset):
    ds_id = str(mining_dataset.id)

    # 1. DFG
    r_dfg = client.get(f"/api/process/dfg?dataset_id={ds_id}")
    assert r_dfg.status_code == 200
    assert len(r_dfg.json()["transitions"]) > 0

    # 2. Variants
    r_var = client.get(f"/api/process/variants?dataset_id={ds_id}")
    assert r_var.status_code == 200
    assert r_var.json()["unique_variants_count"] == 3

    # 3. Activities
    r_act = client.get(f"/api/process/activities?dataset_id={ds_id}")
    assert r_act.status_code == 200
    assert len(r_act.json()["activities"]) == 3

    # 4. Discovery
    r_disc = client.get(f"/api/process/discovery?dataset_id={ds_id}")
    assert r_disc.status_code == 200
    assert len(r_disc.json()["transitions"]) > 0

    # 5. Compare
    r_comp = client.get(f"/api/process/compare?dataset_id={ds_id}&dimension=department&value_a=Procurement&value_b=IT")
    assert r_comp.status_code == 200
    assert r_comp.json()["slice_a"]["case_count"] == 2
    assert r_comp.json()["slice_b"]["case_count"] == 1
