"""
Datasets & ETL API Endpoints.
Provides extraction, upload, inspection, processing, and data quality metrics.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dataset import (
    DataQualityReport,
    DatasetListResponse,
    DatasetResponse,
    DatasetUploadResponse,
    ProcessDatasetRequest,
    ProcessDatasetResponse,
)
from app.services.dataset_service import (
    get_dataset,
    get_dataset_quality,
    list_datasets,
    process_dataset,
    upload_dataset,
)

router = APIRouter(prefix="/datasets", tags=["Datasets & ETL"])


@router.post(
    "/upload",
    response_model=DatasetUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a raw CSV event log",
    description="Uploads a CSV file, validates format, detects delimiters & columns, and returns a 10-row preview.",
)
def upload(
    file: UploadFile = File(..., description="The raw CSV event log file"),
    name: Optional[str] = Form(None, description="Optional custom name for the dataset"),
    db: Session = Depends(get_db),
) -> DatasetUploadResponse:
    return upload_dataset(db=db, file=file, name=name)


@router.get(
    "",
    response_model=DatasetListResponse,
    summary="List all uploaded datasets",
    description="Returns a paginated list of datasets with their upload and processing status.",
)
def list_all(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> DatasetListResponse:
    return list_datasets(db=db, page=page, page_size=page_size)


@router.get(
    "/{dataset_id}",
    response_model=DatasetResponse,
    summary="Get dataset details",
    description="Returns dataset metadata, file info, row counts, and current processing status.",
)
def get_one(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> DatasetResponse:
    return get_dataset(db=db, dataset_id=dataset_id)


@router.get(
    "/{dataset_id}/quality",
    response_model=DataQualityReport,
    summary="Get data quality report",
    description="Returns detailed ETL execution audit metrics, data quality issue breakdown, and sample issues.",
)
def get_quality(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> DataQualityReport:
    return get_dataset_quality(db=db, dataset_id=dataset_id)


@router.post(
    "/{dataset_id}/process",
    response_model=ProcessDatasetResponse,
    summary="Trigger ETL processing",
    description="Runs transformation, normalization, validation, and loading into PostgreSQL tables.",
)
def process(
    dataset_id: uuid.UUID,
    request: ProcessDatasetRequest = ProcessDatasetRequest(),
    db: Session = Depends(get_db),
) -> ProcessDatasetResponse:
    return process_dataset(db=db, dataset_id=dataset_id, request=request)
