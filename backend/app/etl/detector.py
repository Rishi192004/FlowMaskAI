"""
CSV delimiter and column mapping detector.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Dict, List, Tuple


COMMON_DELIMITERS = [",", ";", "\t", "|"]

# Common synonym mappings for standard event log fields
SYNONYMS_CASE = [
    "case_id", "caseid", "case id", "case", "order_id", "order id", "orderid",
    "requisition_id", "po_number", "ponumber", "po_id", "trace_id", "traceid"
]

SYNONYMS_ACTIVITY = [
    "activity", "activity_name", "activityname", "event", "event_name",
    "eventname", "task", "task_name", "action", "step", "status"
]

SYNONYMS_TIMESTAMP = [
    "timestamp", "event_timestamp", "time", "date", "datetime", "created_at",
    "start_time", "complete_time", "end_time", "timestamp_utc"
]

SYNONYMS_RESOURCE = [
    "resource", "user", "user_id", "username", "org:resource", "operator",
    "agent", "assignee", "role", "performer"
]


def detect_delimiter(file_path: Path | str, sample_size_bytes: int = 65536) -> str:
    """Detect delimiter by analyzing a sample of the file."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        sample = f.read(sample_size_bytes)
    
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample, delimiters=COMMON_DELIMITERS)
        return dialect.delimiter
    except Exception:
        # Fallback: count occurrences in sample lines
        lines = sample.splitlines()[:10]
        if not lines:
            return ","
        counts = {d: sum(line.count(d) for line in lines) for d in COMMON_DELIMITERS}
        best = max(counts, key=counts.get)
        return best if counts[best] > 0 else ","


def detect_columns_and_preview(
    file_path: Path | str, delimiter: str = ",", max_preview_rows: int = 10
) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Reads the header and first N rows of a CSV file.
    Returns (columns, preview_rows).
    """
    columns: List[str] = []
    preview: List[Dict[str, str]] = []

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        if reader.fieldnames:
            columns = [col.strip() for col in reader.fieldnames if col is not None]
        
        for idx, row in enumerate(reader):
            if idx >= max_preview_rows:
                break
            cleaned_row = {
                (k.strip() if k else f"col_{i}"): (v.strip() if v else "")
                for i, (k, v) in enumerate(row.items())
            }
            preview.append(cleaned_row)

    return columns, preview


def suggest_column_mapping(columns: List[str]) -> Dict[str, str]:
    """
    Heuristically matches detected columns to canonical fields:
    case_id, activity, timestamp, resource.
    """
    mapping: Dict[str, str] = {}
    normalized = {col.lower().replace("-", "_").replace(" ", "_"): col for col in columns}

    # Match case_id
    for syn in SYNONYMS_CASE:
        syn_norm = syn.lower().replace("-", "_").replace(" ", "_")
        if syn_norm in normalized:
            mapping["case_id"] = normalized[syn_norm]
            break

    # Match activity
    for syn in SYNONYMS_ACTIVITY:
        syn_norm = syn.lower().replace("-", "_").replace(" ", "_")
        if syn_norm in normalized:
            mapping["activity"] = normalized[syn_norm]
            break

    # Match timestamp
    for syn in SYNONYMS_TIMESTAMP:
        syn_norm = syn.lower().replace("-", "_").replace(" ", "_")
        if syn_norm in normalized:
            mapping["timestamp"] = normalized[syn_norm]
            break

    # Match resource
    for syn in SYNONYMS_RESOURCE:
        syn_norm = syn.lower().replace("-", "_").replace(" ", "_")
        if syn_norm in normalized:
            mapping["resource"] = normalized[syn_norm]
            break

    # Fallback to positional defaults if not detected
    if "case_id" not in mapping and len(columns) > 0:
        mapping["case_id"] = columns[0]
    if "activity" not in mapping and len(columns) > 1:
        mapping["activity"] = columns[1]
    if "timestamp" not in mapping and len(columns) > 2:
        mapping["timestamp"] = columns[2]
    if "resource" not in mapping and len(columns) > 3:
        mapping["resource"] = columns[3]

    return mapping
