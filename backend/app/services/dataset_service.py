"""
Dataset management service: file uploads, dataset metadata, and quality reporting.
"""
from __future__ import annotations

import math
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.etl.detector import (
    detect_columns_and_preview,
    detect_delimiter,
    suggest_column_mapping,
)
from app.etl.pipeline import run_etl_pipeline
from app.models.dataset import (
    DataQualityIssue,
    Dataset,
    ETLExecution,
)
from app.schemas.dataset import (
    DataQualityIssueItem,
    DataQualityReport,
    DatasetListResponse,
    DatasetResponse,
    DatasetUploadResponse,
    ETLExecutionSummary,
    ProcessDatasetRequest,
    ProcessDatasetResponse,
)

logger = get_logger(__name__)


def get_upload_dir() -> Path:
    p = Path(settings.UPLOAD_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def upload_dataset(
    db: Session,
    file: UploadFile,
    name: Optional[str] = None,
) -> DatasetUploadResponse:
    """
    Validates CSV upload, writes file to disk, auto-detects delimiter and columns,
    and creates a new Dataset entity in 'uploaded' status.
    """
    if not file.filename:
        raise ValidationError("Uploaded file must have a filename.")

    # Validate extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext != ".csv":
        raise ValidationError(f"Invalid file type '{file_ext}'. Only .csv files are supported.")

    dataset_id = uuid.uuid4()
    upload_dir = get_upload_dir()
    safe_filename = f"{dataset_id}_{Path(file.filename).name}"
    dest_path = upload_dir / safe_filename

    # Save to disk
    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        logger.error("Failed to write uploaded file to disk", exc_info=exc)
        raise ValidationError("Could not save the uploaded file.")

    file_size = dest_path.stat().st_size
    if file_size == 0:
        dest_path.unlink(missing_ok=True)
        raise ValidationError("Uploaded CSV file is empty.")

    # Step 1: Detect delimiter and sample preview
    try:
        delimiter = detect_delimiter(dest_path)
        columns, preview_rows = detect_columns_and_preview(dest_path, delimiter=delimiter, max_preview_rows=10)
    except Exception as exc:
        dest_path.unlink(missing_ok=True)
        raise ValidationError(f"Failed to parse CSV format: {str(exc)}")

    if not columns:
        dest_path.unlink(missing_ok=True)
        raise ValidationError("CSV file contains no valid headers or columns.")

    suggested_mapping = suggest_column_mapping(columns)
    dataset_name = name.strip() if name and name.strip() else Path(file.filename).stem

    dataset = Dataset(
        id=dataset_id,
        name=dataset_name,
        filename=file.filename,
        file_path=str(dest_path.resolve()),
        file_size_bytes=file_size,
        delimiter=delimiter,
        status="uploaded",
        total_rows_raw=0,
        column_mapping=suggested_mapping,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    logger.info("Dataset uploaded successfully", extra={"dataset_id": str(dataset_id), "size_bytes": file_size})

    return DatasetUploadResponse(
        id=dataset.id,
        name=dataset.name,
        filename=dataset.filename,
        file_size_bytes=dataset.file_size_bytes,
        delimiter=dataset.delimiter,
        status=dataset.status,
        detected_columns=columns,
        suggested_mapping=suggested_mapping,
        preview_rows=preview_rows,
        created_at=dataset.created_at,
    )


def get_dataset(db: Session, dataset_id: uuid.UUID) -> DatasetResponse:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise NotFoundError(f"Dataset '{dataset_id}' not found.")
    return DatasetResponse.model_validate(dataset)


def list_datasets(
    db: Session, page: int = 1, page_size: int = 20
) -> DatasetListResponse:
    query = db.query(Dataset).order_by(Dataset.created_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    pages = math.ceil(total / page_size) if total > 0 else 0

    return DatasetListResponse(
        items=[DatasetResponse.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


def get_dataset_quality(db: Session, dataset_id: uuid.UUID) -> DataQualityReport:
    """
    Compiles complete data quality report for a dataset:
    - Latest ETL execution audit metrics
    - Breakdown of issues by type and severity
    - Recent sample issues with full details
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise NotFoundError(f"Dataset '{dataset_id}' not found.")

    latest_exec = (
        db.query(ETLExecution)
        .filter(ETLExecution.dataset_id == dataset.id)
        .order_by(ETLExecution.started_at.desc())
        .first()
    )

    metrics = {
        "total_records_received": latest_exec.total_records_received if latest_exec else 0,
        "valid_records": latest_exec.valid_records if latest_exec else 0,
        "duplicate_records": latest_exec.duplicate_records if latest_exec else 0,
        "invalid_records": latest_exec.invalid_records if latest_exec else 0,
        "missing_value_records": latest_exec.missing_value_records if latest_exec else 0,
        "records_rejected": latest_exec.records_rejected if latest_exec else 0,
        "records_loaded": latest_exec.records_loaded if latest_exec else 0,
    }

    # Aggregate issues by type
    issues_counts = (
        db.query(DataQualityIssue.issue_type, func.count(DataQualityIssue.id))
        .filter(DataQualityIssue.dataset_id == dataset.id)
        .group_by(DataQualityIssue.issue_type)
        .all()
    )
    breakdown = {issue_type: count for issue_type, count in issues_counts}

    # Fetch top 50 recent issues
    recent_issues = (
        db.query(DataQualityIssue)
        .filter(DataQualityIssue.dataset_id == dataset.id)
        .order_by(DataQualityIssue.id.asc())
        .limit(50)
        .all()
    )

    return DataQualityReport(
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        dataset_status=dataset.status,
        latest_execution=ETLExecutionSummary.model_validate(latest_exec) if latest_exec else None,
        metrics=metrics,
        issue_breakdown=breakdown,
        recent_issues=[DataQualityIssueItem.model_validate(iss) for iss in recent_issues],
    )


def process_dataset(
    db: Session,
    dataset_id: uuid.UUID,
    request: ProcessDatasetRequest,
) -> ProcessDatasetResponse:
    """Trigger the ETL pipeline on an uploaded dataset."""
    execution = run_etl_pipeline(
        db=db,
        dataset_id=dataset_id,
        column_mapping_override=request.column_mapping,
        delimiter_override=request.delimiter,
        normalize_activities=request.normalize_activities,
        drop_duplicates=request.drop_duplicates,
    )

    metrics = {
        "total_records_received": execution.total_records_received,
        "valid_records": execution.valid_records,
        "duplicate_records": execution.duplicate_records,
        "invalid_records": execution.invalid_records,
        "missing_value_records": execution.missing_value_records,
        "records_rejected": execution.records_rejected,
        "records_loaded": execution.records_loaded,
    }

    return ProcessDatasetResponse(
        dataset_id=dataset_id,
        execution_id=execution.id,
        status=execution.status,
        message=f"ETL completed: {execution.records_loaded} records loaded, {execution.records_rejected} records rejected.",
        metrics=metrics,
        duration_seconds=execution.duration_seconds or 0.0,
    )
