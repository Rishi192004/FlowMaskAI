"""
Normalization utilities for event log columns, activity names, and timestamps.
Uses built-in Python 3.11+ datetime features with optional dateutil fallback.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional


# Common activity acronyms to preserve in upper case
KNOWN_ACRONYMS = {"PO", "PR", "P2P", "SLA", "ID", "ERP", "IT", "HR", "USD", "EUR"}

COMMON_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%d/%m/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
]


def normalize_activity_name(raw_activity: Optional[str]) -> str:
    """
    Standardize activity name:
    - Strips leading/trailing whitespace
    - Replaces multiple consecutive spaces/underscores with a single space
    - Converts to title case while preserving standard acronyms (e.g., 'PO Created')
    """
    if not raw_activity:
        return ""

    # Replace underscores and dashes with spaces
    text = re.sub(r"[_\-]+", " ", str(raw_activity).strip())
    # Collapse multiple whitespaces
    text = re.sub(r"\s+", " ", text)

    words = text.split(" ")
    normalized_words = []
    for w in words:
        upper = w.upper()
        if upper in KNOWN_ACRONYMS:
            normalized_words.append(upper)
        else:
            normalized_words.append(w.capitalize())

    return " ".join(normalized_words)


def parse_timestamp_to_utc(raw_val: Any) -> Optional[datetime]:
    """
    Parses various timestamp string formats and numerical timestamps to a timezone-aware UTC datetime.
    Supports:
    - ISO 8601 (built-in Python 3.11+ fromisoformat)
    - Standard datetime formats
    - Unix epoch timestamps (seconds or milliseconds)
    Returns None if parsing fails.
    """
    if raw_val is None:
        return None

    # Already datetime
    if isinstance(raw_val, datetime):
        if raw_val.tzinfo is None:
            return raw_val.replace(tzinfo=timezone.utc)
        return raw_val.astimezone(timezone.utc)

    val_str = str(raw_val).strip()
    if not val_str:
        return None

    # Check for Unix epoch (numeric)
    if re.match(r"^\d{10}(\.\d+)?$", val_str):
        try:
            return datetime.fromtimestamp(float(val_str), tz=timezone.utc)
        except Exception:
            pass
    elif re.match(r"^\d{13}$", val_str):  # milliseconds epoch
        try:
            return datetime.fromtimestamp(float(val_str) / 1000.0, tz=timezone.utc)
        except Exception:
            pass

    # 1. Try ISO 8601 parsing (handles Z, offsets, milliseconds in Python 3.11+)
    iso_str = val_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        pass

    # 2. Try common strptime formats
    for fmt in COMMON_FORMATS:
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue

    # 3. Fallback to dateutil if installed
    try:
        from dateutil import parser as date_parser
        dt = date_parser.parse(val_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        pass

    return None
