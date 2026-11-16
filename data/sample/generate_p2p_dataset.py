"""
Synthetic P2P (Purchase-to-Pay) Event Log Generator.
Generates 100,000+ realistic business event records with:
- Standard P2P workflow
- Natural timestamp progressions
- Intentionally seeded data quality issues (duplicates, out-of-order, missing values)
- Domain attributes (amount, vendor_id, department, resource)
"""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


ACTIVITIES = [
    "Purchase Requisition",
    "Manager Approval",
    "Purchase Order Created",
    "Goods Received",
    "Invoice Received",
    "Invoice Verified",
    "Payment Completed",
]

RESOURCES = [
    "Alice Smith", "Bob Jones", "Charlie Brown", "Diana Prince",
    "Evan Wright", "Fiona Gallagher", "George Clark", "System Automated"
]

DEPARTMENTS = ["Procurement", "Finance", "Supply Chain", "IT Ops", "Marketing", "Legal"]
VENDORS = [f"VEND-{i:04d}" for i in range(1, 51)]


def generate_p2p_event_log(
    output_path: Path | str,
    target_event_count: int = 105000,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    base_time = datetime(2025, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
    case_counter = 1
    total_events = 0

    headers = [
        "Case ID",
        "Activity",
        "Timestamp",
        "Resource",
        "Amount USD",
        "Vendor ID",
        "Department",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        while total_events < target_event_count:
            case_id = f"PO-2025-{case_counter:06d}"
            case_counter += 1

            # Case duration starts at an offset
            case_start = base_time + timedelta(
                days=random.randint(0, 180),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            curr_time = case_start
            amount = round(random.uniform(250.0, 75000.0), 2)
            vendor = random.choice(VENDORS)
            dept = random.choice(DEPARTMENTS)

            # Determine case path: 85% standard, 15% variations
            path_type = random.choices(["standard", "skip_approval", "rework", "early_invoice"], weights=[85, 5, 5, 5])[0]

            case_activities = list(ACTIVITIES)
            if path_type == "skip_approval":
                case_activities.remove("Manager Approval")
            elif path_type == "early_invoice":
                # Swap Goods Received and Invoice Received
                gr_idx = case_activities.index("Goods Received")
                ir_idx = case_activities.index("Invoice Received")
                case_activities[gr_idx], case_activities[ir_idx] = case_activities[ir_idx], case_activities[gr_idx]
            elif path_type == "rework":
                # Insert a duplicate or repeated verification activity
                case_activities.insert(case_activities.index("Invoice Verified"), "Invoice Verified")

            for act_idx, act in enumerate(case_activities):
                # Realistic gap between activities (1 hour to 3 days)
                step_gap_hours = random.uniform(1.0, 72.0)
                curr_time = curr_time + timedelta(hours=step_gap_hours)

                resource = "System Automated" if "Created" in act or "Completed" in act else random.choice(RESOURCES)

                # Seed realistic data quality anomalies (total ~2-3% of events)
                dice = random.random()

                # Anomaly 1: Missing value (0.3% probability)
                if dice < 0.003:
                    if random.random() < 0.5:
                        row = [case_id, "", curr_time.isoformat(), resource, amount, vendor, dept]
                    else:
                        row = [case_id, act, "INVALID_DATE_XYZ", resource, amount, vendor, dept]
                    writer.writerow(row)
                    total_events += 1
                    continue

                # Anomaly 2: Out of order timestamp (0.5% probability)
                event_time = curr_time
                if 0.003 <= dice < 0.008 and act_idx > 0:
                    event_time = curr_time - timedelta(hours=step_gap_hours * 2)

                # Regular event
                writer.writerow([
                    case_id,
                    act,
                    event_time.isoformat(),
                    resource,
                    amount,
                    vendor,
                    dept,
                ])
                total_events += 1

                # Anomaly 3: Duplicate event (0.5% probability)
                if 0.008 <= dice < 0.013:
                    writer.writerow([
                        case_id,
                        act,
                        event_time.isoformat(),
                        resource,
                        amount,
                        vendor,
                        dept,
                    ])
                    total_events += 1

                if total_events >= target_event_count:
                    break

    return output_path


if __name__ == "__main__":
    out = Path("data/sample/p2p_100k_events.csv")
    print(f"Generating 100K+ event dataset to {out}...")
    generate_p2p_event_log(out, target_event_count=102000)
    print("Done!")
