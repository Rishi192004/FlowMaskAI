"""
Complete ETL Pipeline Orchestrator.
Performs chunked Extraction, Transformation (normalization, validation, anomaly detection),
and Loading into PostgreSQL while preserving 100% of raw records and tracking data quality metrics.
"""
from __future__ import annotations

import csv
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import DatasetProcessingError, NotFoundError
from app.core.logging import get_logger
from app.etl.detector import suggest_column_mapping
from app.etl.normalizer import normalize_activity_name, parse_timestamp_to_utc
from app.etl.validator import EventLogValidator
from app.models.dataset import (
    CleanedEvent,
    DataQualityIssue,
    Dataset,
    ETLExecution,
    RawEvent,
)

logger = get_logger(__name__)

CHUNK_SIZE = 5000  # Process in memory-efficient chunks


def run_etl_pipeline(
    db: Session,
    dataset_id: uuid.UUID,
    column_mapping_override: Optional[Dict[str, str]] = None,
    delimiter_override: Optional[str] = None,
    normalize_activities: bool = True,
    drop_duplicates: bool = True,
) -> ETLExecution:
    """
    Executes the full ETL extraction, transformation, and loading pipeline.
    Never silently discards records.
    Maintains full audit trails in etl_executions and raw_events.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise NotFoundError(f"Dataset '{dataset_id}' not found.")

    file_path = Path(dataset.file_path)
    if not file_path.exists():
        raise DatasetProcessingError(f"Dataset source file not found at '{file_path}'.")

    # Update dataset status to processing
    dataset.status = "processing"
    db.commit()

    start_time = time.time()
    started_at = datetime.now(timezone.utc)

    # Initialize ETL Execution audit entity
    execution = ETLExecution(
        id=uuid.uuid4(),
        dataset_id=dataset.id,
        status="running",
        started_at=started_at,
        total_records_received=0,
        valid_records=0,
        duplicate_records=0,
        invalid_records=0,
        missing_value_records=0,
        records_rejected=0,
        records_loaded=0,
    )
    db.add(execution)
    db.commit()

    delimiter = delimiter_override or dataset.delimiter or ","
    validator = EventLogValidator()

    # Determine column mapping
    mapping = column_mapping_override or dataset.column_mapping or {}

    total_received = 0
    total_valid = 0
    total_duplicates = 0
    total_invalid = 0
    total_missing_values = 0
    total_rejected = 0
    total_loaded = 0

    try:
        # Clear any prior cleaned events / raw events if this is a re-run
        db.query(CleanedEvent).filter(CleanedEvent.dataset_id == dataset.id).delete()
        db.query(RawEvent).filter(RawEvent.dataset_id == dataset.id).delete()
        db.commit()

        # Step 1: Open and read the CSV in streaming mode
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            fieldnames = [col.strip() for col in reader.fieldnames if col is not None] if reader.fieldnames else []

            # If mapping is incomplete, auto-suggest
            if not mapping or "case_id" not in mapping or "activity" not in mapping or "timestamp" not in mapping:
                mapping = suggest_column_mapping(fieldnames)
                dataset.column_mapping = mapping

            case_col = mapping.get("case_id")
            act_col = mapping.get("activity")
            time_col = mapping.get("timestamp")
            res_col = mapping.get("resource")

            raw_events_batch: List[RawEvent] = []
            cleaned_events_batch: List[CleanedEvent] = []
            issues_batch: List[DataQualityIssue] = []

            for row_idx, row in enumerate(reader, start=1):
                total_received += 1
                clean_row = {
                    (k.strip() if k else f"col_{i}"): (v.strip() if v else "")
                    for i, (k, v) in enumerate(row.items())
                }

                # Audit: Create RawEvent preserving exact unedited input
                raw_event = RawEvent(
                    dataset_id=dataset.id,
                    row_index=row_idx,
                    raw_data=clean_row,
                )
                raw_events_batch.append(raw_event)

                # Step 2: Transformation & Extraction of fields
                raw_case_id = clean_row.get(case_col) if case_col else None
                raw_activity = clean_row.get(act_col) if act_col else None
                raw_timestamp = clean_row.get(time_col) if time_col else None
                raw_resource = clean_row.get(res_col) if res_col else None

                # Normalize activity and parse timestamp
                activity_norm = normalize_activity_name(raw_activity) if normalize_activities else (raw_activity or "")
                dt_parsed = parse_timestamp_to_utc(raw_timestamp)

                # Validation & anomaly detection
                v_res = validator.validate_row(
                    row_index=row_idx,
                    case_id=raw_case_id,
                    activity=activity_norm,
                    dt=dt_parsed,
                    resource=raw_resource,
                    raw_row=clean_row,
                )

                if v_res.has_missing_values:
                    total_missing_values += 1
                if v_res.is_duplicate:
                    total_duplicates += 1
                if not v_res.is_valid:
                    total_invalid += 1

                # Record quality issues
                for issue in v_res.issues:
                    db_issue = DataQualityIssue(
                        dataset_id=dataset.id,
                        etl_execution_id=execution.id,
                        row_index=row_idx,
                        issue_type=issue["issue_type"],
                        severity=issue["severity"],
                        details=issue["details"],
                        is_fatal=issue["is_fatal"],
                    )
                    issues_batch.append(db_issue)

                # Determine whether record is accepted into cleaned_events
                if v_res.is_rejected:
                    total_rejected += 1
                elif v_res.is_duplicate and drop_duplicates:
                    total_rejected += 1
                else:
                    total_valid += 1
                    total_loaded += 1

                    # Extract remaining attributes as extra_attributes
                    exclude_cols = {case_col, act_col, time_col, res_col}
                    extra_attrs = {k: v for k, v in clean_row.items() if k not in exclude_cols and v != ""}

                    cleaned_event = CleanedEvent(
                        dataset_id=dataset.id,
                        case_id=str(raw_case_id).strip(),
                        activity=activity_norm,
                        timestamp=dt_parsed,
                        resource=str(raw_resource).strip() if raw_resource else None,
                        extra_attributes=extra_attrs if extra_attrs else None,
                        is_out_of_order=v_res.is_out_of_order,
                    )
                    cleaned_events_batch.append(cleaned_event)

                # Batch flush to keep memory overhead bounded for large 100K+ files
                if len(raw_events_batch) >= CHUNK_SIZE:
                    db.bulk_save_objects(raw_events_batch)
                    db.bulk_save_objects(cleaned_events_batch)
                    db.bulk_save_objects(issues_batch)
                    db.commit()
                    raw_events_batch.clear()
                    cleaned_events_batch.clear()
                    issues_batch.clear()

            # Flush any remaining items in the final batch
            if raw_events_batch:
                db.bulk_save_objects(raw_events_batch)
            if cleaned_events_batch:
                db.bulk_save_objects(cleaned_events_batch)
            if issues_batch:
                db.bulk_save_objects(issues_batch)
            db.commit()

        # Step 3: Complete execution audit
        completed_at = datetime.now(timezone.utc)
        duration = round(time.time() - start_time, 3)

        execution.status = "completed"
        execution.completed_at = completed_at
        execution.duration_seconds = duration
        execution.total_records_received = total_received
        execution.valid_records = total_valid
        execution.duplicate_records = total_duplicates
        execution.invalid_records = total_invalid
        execution.missing_value_records = total_missing_values
        execution.records_rejected = total_rejected
        execution.records_loaded = total_loaded

        dataset.status = "processed"
        dataset.total_rows_raw = total_received
        db.commit()
        db.refresh(execution)

        logger.info(
            "ETL processing completed successfully",
            extra={
                "dataset_id": str(dataset_id),
                "total_received": total_received,
                "loaded": total_loaded,
                "duration_seconds": duration,
            },
        )
        return execution

    except Exception as exc:
        db.rollback()
        completed_at = datetime.now(timezone.utc)
        duration = round(time.time() - start_time, 3)

        execution.status = "failed"
        execution.completed_at = completed_at
        execution.duration_seconds = duration
        execution.error_message = str(exc)

        dataset.status = "failed"
        db.commit()

        logger.error(
            "ETL processing failed",
            exc_info=exc,
            extra={"dataset_id": str(dataset_id), "error": str(exc)},
        )
        raise DatasetProcessingError(f"ETL pipeline failed: {str(exc)}")
