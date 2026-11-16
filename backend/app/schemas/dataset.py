"""
Pydantic schemas for datasets, ETL processing, and data quality metrics.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Dataset Schemas ───────────────────────────────────────────────────────────

class ColumnMapping(BaseModel):
    case_id: str = "case_id"
    activity: str = "activity"
    timestamp: str = "timestamp"
    resource: Optional[str] = "resource"


class DatasetUploadResponse(BaseModel):
    id: uuid.UUID
    name: str
    filename: str
    file_size_bytes: int
    delimiter: str
    status: str
    detected_columns: List[str]
    suggested_mapping: Dict[str, str]
    preview_rows: List[Dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetResponse(BaseModel):
    id: uuid.UUID
    name: str
    filename: str
    file_size_bytes: int
    delimiter: str
    status: str
    total_rows_raw: int
    column_mapping: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatasetListResponse(BaseModel):
    items: List[DatasetResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ── ETL & Quality Schemas ─────────────────────────────────────────────────────

class ProcessDatasetRequest(BaseModel):
    column_mapping: Optional[Dict[str, str]] = Field(
        default=None,
        description="Custom mapping of CSV headers to case_id, activity, timestamp, resource",
    )
    delimiter: Optional[str] = Field(default=None, description="Optional delimiter override")
    normalize_activities: bool = Field(default=True, description="Normalize whitespace and casing of activities")
    drop_duplicates: bool = Field(default=True, description="Filter out duplicate events from cleaned dataset")


class ETLExecutionSummary(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    total_records_received: int
    valid_records: int
    duplicate_records: int
    invalid_records: int
    missing_value_records: int
    records_rejected: int
    records_loaded: int
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class DataQualityIssueItem(BaseModel):
    id: int
    row_index: int
    issue_type: str
    severity: str
    details: Dict[str, Any]
    is_fatal: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DataQualityReport(BaseModel):
    dataset_id: uuid.UUID
    dataset_name: str
    dataset_status: str
    latest_execution: Optional[ETLExecutionSummary] = None
    metrics: Dict[str, int]
    issue_breakdown: Dict[str, int]
    recent_issues: List[DataQualityIssueItem]


class ProcessDatasetResponse(BaseModel):
    dataset_id: uuid.UUID
    execution_id: uuid.UUID
    status: str
    message: str
    metrics: Dict[str, int]
    duration_seconds: float
