"""
SQL Query layer for Operational Analytics.
Provides documented SQL queries for case durations, activity transitions,
rework occurrences, and department/vendor groupings.
Works seamlessly across PostgreSQL and SQLite.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.dataset import CleanedEvent


# Terminal activity defining a completed P2P case
COMPLETION_ACTIVITIES = ("Payment Completed", "Payment Executed", "Invoice Paid")


def fetch_case_durations_sql(
    db: Session,
    dataset_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    SQL Query: Aggregates case-level statistics.
    Computes:
      - case_id
      - min_ts: first event timestamp (start of case)
      - max_ts: last event timestamp (end of case)
      - event_count: total events in case
      - is_completed: 1 if case reached completion activity, else 0
      - vendor_id, department, amount (from extra_attributes)

    Traceable SQL:
      SELECT
        case_id,
        MIN(timestamp) as min_ts,
        MAX(timestamp) as max_ts,
        COUNT(id) as event_count,
        MAX(CASE WHEN activity IN (:c1, :c2, :c3) THEN 1 ELSE 0 END) as is_completed
      FROM cleaned_events
      WHERE dataset_id = :dataset_id
      GROUP BY case_id
    """
    conditions = ["dataset_id = :dataset_id"]
    params: Dict[str, Any] = {
        "dataset_id": str(dataset_id),
        "c1": COMPLETION_ACTIVITIES[0],
        "c2": COMPLETION_ACTIVITIES[1],
        "c3": COMPLETION_ACTIVITIES[2],
    }

    if start_date:
        conditions.append("timestamp >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("timestamp <= :end_date")
        params["end_date"] = end_date

    where_clause = " AND ".join(conditions)

    # Use ORM / SQL query
    sql = text(f"""
        SELECT
            case_id,
            MIN(timestamp) AS min_ts,
            MAX(timestamp) AS max_ts,
            COUNT(id) AS event_count,
            MAX(CASE WHEN activity IN (:c1, :c2, :c3) THEN 1 ELSE 0 END) AS is_completed
        FROM cleaned_events
        WHERE {where_clause}
        GROUP BY case_id
    """)

    rows = db.execute(sql, params).fetchall()

    results: List[Dict[str, Any]] = []
    for r in rows:
        min_ts = r[1]
        max_ts = r[2]

        # Convert strings to datetime if SQLite returned string
        if isinstance(min_ts, str):
            min_ts = datetime.fromisoformat(min_ts)
        if isinstance(max_ts, str):
            max_ts = datetime.fromisoformat(max_ts)

        duration_seconds = (max_ts - min_ts).total_seconds() if min_ts and max_ts else 0.0

        results.append({
            "case_id": r[0],
            "min_ts": min_ts,
            "max_ts": max_ts,
            "event_count": r[3],
            "is_completed": bool(r[4]),
            "duration_hours": round(duration_seconds / 3600.0, 4),
        })

    return results


def fetch_activity_transitions_sql(
    db: Session,
    dataset_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    SQL Query: Computes waiting times between consecutive activities within each case.
    Uses SQL Window Function LAG() partitioned by case_id ordered by timestamp.

    Traceable SQL:
      SELECT
        case_id,
        activity,
        timestamp,
        LAG(timestamp) OVER (PARTITION BY case_id ORDER BY timestamp) as prev_ts,
        LAG(activity) OVER (PARTITION BY case_id ORDER BY timestamp) as prev_act
      FROM cleaned_events
      WHERE dataset_id = :dataset_id
    """
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
            case_id,
            activity,
            timestamp,
            LAG(timestamp) OVER (PARTITION BY case_id ORDER BY timestamp, id) AS prev_ts,
            LAG(activity) OVER (PARTITION BY case_id ORDER BY timestamp, id) AS prev_act
        FROM cleaned_events
        WHERE {where_clause}
        ORDER BY case_id, timestamp, id
    """)

    rows = db.execute(sql, params).fetchall()

    transitions: List[Dict[str, Any]] = []
    for r in rows:
        curr_ts = r[2]
        prev_ts = r[3]

        if prev_ts is None:
            continue  # First event in the case has no preceding waiting time

        if isinstance(curr_ts, str):
            curr_ts = datetime.fromisoformat(curr_ts)
        if isinstance(prev_ts, str):
            prev_ts = datetime.fromisoformat(prev_ts)

        wait_seconds = (curr_ts - prev_ts).total_seconds()
        # Enforce non-negative waiting time for consecutive events
        wait_hours = max(0.0, wait_seconds / 3600.0)

        transitions.append({
            "case_id": r[0],
            "activity": r[1],
            "prev_activity": r[4],
            "waiting_time_hours": round(wait_hours, 4),
        })

    return transitions


def fetch_rework_sql(
    db: Session,
    dataset_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    SQL Query: Identifies activity repetitions within each case (Rework).
    Groups by case_id, activity and counts occurrences.
    Rework occurs when occurrences > 1.

    Traceable SQL:
      SELECT
        case_id,
        activity,
        COUNT(id) as execution_count
      FROM cleaned_events
      WHERE dataset_id = :dataset_id
      GROUP BY case_id, activity
      HAVING COUNT(id) > 1
    """
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
            case_id,
            activity,
            COUNT(id) AS execution_count
        FROM cleaned_events
        WHERE {where_clause}
        GROUP BY case_id, activity
        HAVING COUNT(id) > 1
    """)

    rows = db.execute(sql, params).fetchall()
    return [
        {
            "case_id": r[0],
            "activity": r[1],
            "execution_count": r[2],
            "rework_count": r[2] - 1,
        }
        for r in rows
    ]


def fetch_case_attributes_and_events(
    db: Session,
    dataset_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Fetches events with extra_attributes (vendor_id, department, amount)
    for grouping and multidimensional performance analysis.
    """
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
            extra_attributes
        FROM cleaned_events
        WHERE {where_clause}
        ORDER BY case_id, timestamp, id
    """)

    rows = db.execute(sql, params).fetchall()
    events: List[Dict[str, Any]] = []

    for r in rows:
        ts = r[3]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)

        attrs = r[4]
        if isinstance(attrs, str):
            try:
                attrs = json.loads(attrs)
            except Exception:
                attrs = {}
        elif attrs is None:
            attrs = {}

        events.append({
            "id": r[0],
            "case_id": r[1],
            "activity": r[2],
            "timestamp": ts,
            "extra_attributes": attrs,
        })

    return events
