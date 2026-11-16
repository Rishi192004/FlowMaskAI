"""
Validation rules and anomaly detection for event records.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple


INVALID_CASE_STRINGS = {"none", "null", "nan", "undefined", "", "n/a"}


class EventValidationResult:
    def __init__(self, row_index: int):
        self.row_index = row_index
        self.is_valid: bool = True
        self.is_rejected: bool = False
        self.is_duplicate: bool = False
        self.is_out_of_order: bool = False
        self.has_missing_values: bool = False
        self.issues: List[Dict[str, Any]] = []

    def add_issue(
        self, issue_type: str, message: str, severity: str = "ERROR", is_fatal: bool = True, details: Optional[Dict[str, Any]] = None
    ) -> None:
        self.is_valid = False
        if is_fatal:
            self.is_rejected = True
        issue = {
            "issue_type": issue_type,
            "severity": severity,
            "message": message,
            "is_fatal": is_fatal,
            "details": details or {},
        }
        self.issues.append(issue)


class EventLogValidator:
    """
    Maintains state across streamed events for a dataset to detect:
    - Duplicates
    - Out-of-order events per case
    - Missing or malformed values
    """
    def __init__(self):
        # Set of seen (case_id, activity, timestamp_iso, resource) tuples
        self.seen_event_signatures: Set[Tuple[str, str, str, str]] = set()
        # Dictionary of latest timestamp per case_id for out-of-order detection
        self.latest_timestamp_per_case: Dict[str, datetime] = {}

    def validate_row(
        self,
        row_index: int,
        case_id: Optional[str],
        activity: Optional[str],
        dt: Optional[datetime],
        resource: Optional[str],
        raw_row: Dict[str, Any],
    ) -> EventValidationResult:
        result = EventValidationResult(row_index)

        # 1. Validate Case ID
        clean_case = str(case_id).strip() if case_id is not None else ""
        if not clean_case or clean_case.lower() in INVALID_CASE_STRINGS:
            result.has_missing_values = True
            result.add_issue(
                issue_type="MISSING_REQUIRED_FIELD",
                message=f"Missing or invalid case_id: '{case_id}'",
                severity="ERROR",
                is_fatal=True,
                details={"field": "case_id", "value": case_id},
            )

        # 2. Validate Activity
        clean_activity = str(activity).strip() if activity is not None else ""
        if not clean_activity or clean_activity.lower() in INVALID_CASE_STRINGS:
            result.has_missing_values = True
            result.add_issue(
                issue_type="MISSING_REQUIRED_FIELD",
                message=f"Missing or invalid activity: '{activity}'",
                severity="ERROR",
                is_fatal=True,
                details={"field": "activity", "value": activity},
            )

        # 3. Validate Timestamp
        if dt is None:
            result.has_missing_values = True
            result.add_issue(
                issue_type="INVALID_TIMESTAMP",
                message="Timestamp could not be parsed into a valid UTC datetime",
                severity="ERROR",
                is_fatal=True,
                details={"raw_timestamp": raw_row.get("timestamp") or raw_row.get("date") or "missing"},
            )

        # If fatal issues encountered so far, record is rejected before temporal checks
        if result.is_rejected:
            return result

        # 4. Check for duplicate event
        clean_resource = str(resource).strip() if resource is not None else ""
        sig = (clean_case, clean_activity, dt.isoformat(), clean_resource)
        if sig in self.seen_event_signatures:
            result.is_duplicate = True
            result.add_issue(
                issue_type="DUPLICATE_EVENT",
                message=f"Duplicate event detected for case '{clean_case}' and activity '{clean_activity}'",
                severity="WARNING",
                is_fatal=False,
                details={"case_id": clean_case, "activity": clean_activity, "timestamp": dt.isoformat()},
            )
        else:
            self.seen_event_signatures.add(sig)

        # 5. Check for out-of-order event within case
        last_dt = self.latest_timestamp_per_case.get(clean_case)
        if last_dt is not None:
            if dt < last_dt:
                result.is_out_of_order = True
                result.add_issue(
                    issue_type="OUT_OF_ORDER_EVENT",
                    message=(
                        f"Out-of-order event in case '{clean_case}': "
                        f"timestamp {dt.isoformat()} is earlier than previous event timestamp {last_dt.isoformat()}"
                    ),
                    severity="WARNING",
                    is_fatal=False,
                    details={
                        "case_id": clean_case,
                        "current_timestamp": dt.isoformat(),
                        "previous_timestamp": last_dt.isoformat(),
                    },
                )
            else:
                self.latest_timestamp_per_case[clean_case] = dt
        else:
            self.latest_timestamp_per_case[clean_case] = dt

        return result
