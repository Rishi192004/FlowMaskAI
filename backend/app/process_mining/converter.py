"""
Event Log Converter for PM4Py and process mining algorithms.
Transforms cleaned database records into a canonical event log structure:
  case_id   -> case:concept:name
  activity  -> concept:name
  timestamp -> time:timestamp
  resource  -> org:resource
Preserves domain attributes (amount, vendor_id, department).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

# Removed top-level sqlalchemy import to allow lightweight import
# from sqlalchemy import text
# from sqlalchemy.orm import Session

# Lazy import inside function if needed


def fetch_cleaned_event_records(
    db: Any,
    dataset_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    department: Optional[str] = None,
    vendor_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Queries cleaned_events with optional multi-dimensional filters.
    Returns deterministic, timestamp-ordered event dictionaries.
    """
    from sqlalchemy import text
    conditions = ["dataset_id = :dataset_id"]
    params: Dict[str, Any] = {"dataset_id": str(dataset_id)}

    if start_date:
        conditions.append("timestamp >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("timestamp <= :end_date")
        params["end_date"] = end_date

    where_clause = " AND ".join(conditions)

    sql = text(f"""
        SELECT
            id,
            case_id,
            activity,
            timestamp,
            resource,
            extra_attributes,
            is_out_of_order
        FROM cleaned_events
        WHERE {where_clause}
        ORDER BY case_id, timestamp, id
    """)

    rows = db.execute(sql, params).fetchall()
    records: List[Dict[str, Any]] = []

    for r in rows:
        ts = r[3]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)

        attrs = r[5]
        if isinstance(attrs, str):
            try:
                attrs = json.loads(attrs)
            except Exception:
                attrs = {}
        elif attrs is None:
            attrs = {}

        # Apply in-memory attribute filters if department or vendor_id specified
        row_dept = attrs.get("department") or attrs.get("Department")
        if department and row_dept != department:
            continue

        row_vendor = attrs.get("vendor_id") or attrs.get("Vendor ID")
        if vendor_id and row_vendor != vendor_id:
            continue

        rec: Dict[str, Any] = {
            "id": r[0],
            "case:concept:name": str(r[1]).strip(),
            "concept:name": str(r[2]).strip(),
            "time:timestamp": ts,
            "org:resource": str(r[4]).strip() if r[4] else "System",
            "is_out_of_order": bool(r[6]),
        }

        # Preserve additional attributes
        for k, v in attrs.items():
            if k not in rec:
                rec[k] = v

        records.append(rec)

    return records


def to_pm4py_dataframe(records: List[Dict[str, Any]]):
    """
    Converts list of event dictionaries into a PM4Py-compatible pandas DataFrame.
    Applies standard PM4Py formatting when pm4py is installed.
    """
    import pandas as pd

    if not records:
        df = pd.DataFrame(columns=[
            "case:concept:name",
            "concept:name",
            "time:timestamp",
            "org:resource",
        ])
        return df

    df = pd.DataFrame(records)
    df["time:timestamp"] = pd.to_datetime(df["time:timestamp"], utc=True)
    df = df.sort_values(by=["case:concept:name", "time:timestamp"])

    try:
        import pm4py
        df = pm4py.format_dataframe(
            df,
            case_id="case:concept:name",
            activity_key="concept:name",
            timestamp_key="time:timestamp",
        )
    except Exception:
        pass

    return df
