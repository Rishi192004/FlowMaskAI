"""
Process Mining API Endpoints powered by PM4Py and graph discovery algorithms.
Provides DFG, Inductive Miner Petri Net, Variants, Interactive Map, and Process Comparison.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.db.session import get_db
from app.models.dataset import Dataset
from app.process_mining.comparison import compare_process_slices
from app.process_mining.converter import fetch_cleaned_event_records
from app.process_mining.discovery import (
    discover_inductive_miner,
    generate_interactive_process_map,
    get_dfg_response,
)
from app.process_mining.variants import (
    get_activity_frequency_response,
    get_variants_response,
)
from app.schemas.process_mining import (
    ActivityFrequencyResponse,
    ComparisonResponse,
    DFGResponse,
    ProcessDiscoveryResponse,
    ProcessMapResponse,
    ProcessVariantsResponse,
)

router = APIRouter(prefix="/process", tags=["Process Mining"])


def _get_records_or_raise(
    db: Session,
    dataset_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    department: Optional[str] = None,
    vendor_id: Optional[str] = None,
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise NotFoundError(f"Dataset '{dataset_id}' not found.")

    records = fetch_cleaned_event_records(
        db=db,
        dataset_id=dataset_id,
        start_date=start_date,
        end_date=end_date,
        department=department,
        vendor_id=vendor_id,
    )
    return records


@router.get(
    "/discovery",
    response_model=ProcessDiscoveryResponse,
    summary="Discover process model using Inductive Miner",
    description="Applies PM4Py Inductive Miner to discover Petri net places, transitions, and arcs.",
)
def get_discovery(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    department: Optional[str] = Query(None),
    vendor_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> ProcessDiscoveryResponse:
    records = _get_records_or_raise(db, dataset_id, start_date, end_date, department, vendor_id)
    return discover_inductive_miner(dataset_id=dataset_id, records=records)


@router.get(
    "/dfg",
    response_model=DFGResponse,
    summary="Get Directly-Follows Graph (DFG)",
    description="Computes DFG transitions, edge frequencies, average transition times, and start/end boundaries.",
)
def get_dfg(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    department: Optional[str] = Query(None),
    vendor_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> DFGResponse:
    records = _get_records_or_raise(db, dataset_id, start_date, end_date, department, vendor_id)
    return get_dfg_response(dataset_id=dataset_id, records=records)


@router.get(
    "/variants",
    response_model=ProcessVariantsResponse,
    summary="Get process variants and execution paths",
    description="Identifies unique execution paths, frequency percentages, rare variants, and excessive-activity cases.",
)
def get_variants(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    department: Optional[str] = Query(None),
    vendor_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> ProcessVariantsResponse:
    records = _get_records_or_raise(db, dataset_id, start_date, end_date, department, vendor_id)
    return get_variants_response(dataset_id=dataset_id, records=records)


@router.get(
    "/activities",
    response_model=ActivityFrequencyResponse,
    summary="Get activity frequency and coverage",
    description="Returns total occurrence counts and case coverage percentages for each activity.",
)
def get_activities(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    department: Optional[str] = Query(None),
    vendor_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> ActivityFrequencyResponse:
    records = _get_records_or_raise(db, dataset_id, start_date, end_date, department, vendor_id)
    return get_activity_frequency_response(dataset_id=dataset_id, records=records)


@router.get(
    "/map",
    response_model=ProcessMapResponse,
    summary="Get interactive React Flow process map",
    description="Generates React Flow nodes and edges with frequencies, durations, and bottleneck highlights.",
)
def get_map(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    department: Optional[str] = Query(None),
    vendor_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> ProcessMapResponse:
    records = _get_records_or_raise(db, dataset_id, start_date, end_date, department, vendor_id)
    return generate_interactive_process_map(dataset_id=dataset_id, records=records)


@router.get(
    "/compare",
    response_model=ComparisonResponse,
    summary="Compare workflows across departments, vendors, or time periods",
    description="Performs comparative process mining between two slices, highlighting workflow divergence.",
)
def compare_slices(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    dimension: str = Query("department", description="'department' or 'vendor'"),
    value_a: str = Query(..., description="First slice value, e.g. 'Procurement'"),
    value_b: str = Query(..., description="Second slice value, e.g. 'Finance'"),
    db: Session = Depends(get_db),
) -> ComparisonResponse:
    if dimension == "department":
        recs_a = _get_records_or_raise(db, dataset_id, department=value_a)
        recs_b = _get_records_or_raise(db, dataset_id, department=value_b)
    elif dimension == "vendor":
        recs_a = _get_records_or_raise(db, dataset_id, vendor_id=value_a)
        recs_b = _get_records_or_raise(db, dataset_id, vendor_id=value_b)
    else:
        raise ValidationError(f"Unsupported comparison dimension '{dimension}'. Use 'department' or 'vendor'.")

    return compare_process_slices(
        dataset_id=dataset_id,
        records_a=recs_a,
        label_a=value_a,
        records_b=recs_b,
        label_b=value_b,
    )
